from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser
from app.core.config import get_settings
from app.db.models import AnalyticsRun, ImportBatch, ImportRowIssue, InvoiceGroupRecord, RawSourceRow
from app.db.repository import audit, ensure_accounts, load_invoice_groups, persist_run_output
from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.imports.validators import REQUIRED_COLUMNS, parse_source_file, validate_rows
from app.services.analytics_runner import run_account_prioritization
from app.services.storage import SourceStorage, sanitize_filename


def preview_source(db: Session, user: AuthenticatedUser, file_name: str, content: bytes) -> dict:
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_bytes // 1_000_000} MB limit.")
    safe_name = sanitize_filename(file_name)
    parsed = parse_source_file(safe_name, content)
    issues = list(parsed.issues)
    rows_discovered = 0
    cancelled = 0
    for frame in parsed.frames.values():
        rows_discovered += len(frame)
        cancelled += int(frame["PAYMENT STATUS"].astype(str).str.strip().str.lower().eq("cancelled").sum())
        issues.extend(validate_rows(frame))
    duplicate = db.scalar(select(ImportBatch).where(ImportBatch.file_hash == parsed.file_hash, ImportBatch.status == "committed"))
    batch = ImportBatch(
        file_name=safe_name, file_hash=parsed.file_hash, uploaded_by=user.user_id, status="previewed",
        rows_discovered=rows_discovered, rows_accepted=rows_discovered - sum(i.severity == "error" for i in issues),
        rows_flagged=sum(i.severity == "warning" for i in issues), rows_excluded=sum(i.severity == "error" for i in issues),
        cancelled_count=cancelled,
    )
    db.add(batch)
    db.flush()
    batch.storage_path = SourceStorage().put(batch.import_batch_id, safe_name, content)
    for issue in issues:
        db.add(ImportRowIssue(import_batch_id=batch.import_batch_id, row_number=issue.row_number,
                              column_name=issue.column, severity=issue.severity, message=issue.message))
    audit(db, user.user_id, "import_preview", "import_batch", batch.import_batch_id,
          {"file_hash": parsed.file_hash, "rows": rows_discovered, "duplicate": bool(duplicate)})
    db.commit()
    return {
        "import_batch_id": batch.import_batch_id, "file_name": safe_name, "file_hash": parsed.file_hash,
        "sheets": list(parsed.frames), "rows_discovered": rows_discovered, "cancelled_count": cancelled,
        "issues": [asdict(issue) for issue in issues], "duplicate_committed_file": bool(duplicate),
        "can_commit": not any(issue.severity == "error" for issue in issues) and not duplicate,
        "status": "PREVIEW",
    }


def commit_source(db: Session, user: AuthenticatedUser, batch_id: str, override_reason: str | None = None) -> dict:
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Import preview not found.")
    if batch.status == "committed":
        raise HTTPException(409, "This import batch is already committed.")
    errors = db.scalar(select(ImportRowIssue).where(ImportRowIssue.import_batch_id == batch_id, ImportRowIssue.severity == "error"))
    if errors:
        raise HTTPException(422, "Import has validation errors and cannot be committed.")
    duplicate = db.scalar(select(ImportBatch).where(ImportBatch.file_hash == batch.file_hash,
                                                     ImportBatch.status == "committed",
                                                     ImportBatch.import_batch_id != batch_id))
    if duplicate and not (override_reason and override_reason.strip()):
        batch.status = "blocked_duplicate"
        audit(db, user.user_id, "duplicate_import_blocked", "import_batch", batch_id, {"duplicate_of": duplicate.import_batch_id})
        db.commit()
        raise HTTPException(409, "A committed file with the same SHA-256 hash already exists. An override reason is required.")
    if duplicate:
        batch.override_reason = override_reason.strip()
    run: AnalyticsRun | None = None
    try:
        content = SourceStorage().get(batch.storage_path or "")
        parsed = parse_source_file(batch.file_name, content)
        frames = list(parsed.frames.values())
        source_rows = []
        for frame in frames:
            source_rows.extend(dataframe_to_source_rows(frame, import_batch_id=batch_id))
            for _, row in frame.iterrows():
                payload = {column: str(row[column]) for column in REQUIRED_COLUMNS}
                payload.update({"source_sheet": str(row["source_sheet"]), "source_row_number": int(row["source_row_number"])})
                db.add(RawSourceRow(import_batch_id=batch_id, source_sheet=str(row["source_sheet"]),
                                    source_row_number=int(row["source_row_number"]), canonical_payload=payload))
        groupable_rows = [row for row in source_rows if row.standardized_account_name and not pd.isna(row.si_date) and row.si_amount > 0]
        groups = group_invoices(groupable_rows)
        accounts = ensure_accounts(db, [group.standardized_account_name for group in groups])
        for group in groups:
            db.add(InvoiceGroupRecord(
                invoice_group_id=group.invoice_group_id, import_batch_id=batch_id,
                account_key=accounts[group.standardized_account_name].account_key,
                standardized_account_name=group.standardized_account_name, si_no=group.si_no,
                si_date=group.si_date.date(), si_amount=group.si_amount, payment_status=group.payment_status,
                final_cr_date=group.final_cr_date.date() if group.final_cr_date is not None else None,
                total_cr_amount=group.total_cr_amount, total_ewt=group.total_ewt,
                reconciliation_amount=group.reconciliation_amount, reconciliation_difference=group.reconciliation_difference,
                reconciled=group.reconciled, review_reason=group.review_reason, is_cancelled=group.is_cancelled,
            ))
        batch.status = "committed"
        batch.committed_at = datetime.now(timezone.utc)
        db.flush()
        run = AnalyticsRun(status="running", latest_import_batch_id=batch_id, code_version="corrective-pass")
        db.add(run)
        db.flush()
        result = asdict(run_account_prioritization(load_invoice_groups(db)))
        persist_run_output(db, run, result)
        batch.analysis_run_id = run.analysis_run_id
        audit(db, user.user_id, "import_committed", "import_batch", batch_id,
              {"analysis_run_id": run.analysis_run_id, "override": bool(duplicate)})
        audit(db, user.user_id, "analytics_run", "analytics_run", run.analysis_run_id, {"status": run.status})
        db.commit()
        return {"status": "COMMITTED", "import_batch_id": batch_id, "analysis_run_id": run.analysis_run_id,
                "prioritized_accounts": len(result["priorities"]), "cutoff_date": result["cutoff_date"]}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        failed_batch = db.get(ImportBatch, batch_id)
        if failed_batch:
            failed_batch.status = "failed"
        failed_run = AnalyticsRun(status="failed", latest_import_batch_id=batch_id, completed_at=datetime.now(timezone.utc),
                                  errors=[{"message": "Analytics publication failed safely."}])
        db.add(failed_run)
        audit(db, user.user_id, "import_failed", "import_batch", batch_id, {"error_type": type(exc).__name__})
        db.commit()
        raise HTTPException(500, "Import failed safely; the previous successful analysis remains current.") from exc
