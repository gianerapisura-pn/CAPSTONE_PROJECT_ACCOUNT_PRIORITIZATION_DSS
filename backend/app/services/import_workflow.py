from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser
from app.core.config import get_settings
from app.db.models import (
    AnalyticsRun, ImportBatch, ImportRowIssue, InvoiceGroupLineage,
    InvoiceGroupRecord, RawSourceRow,
)
from app.db.repository import audit, ensure_accounts, load_invoice_groups, persist_run_output
from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.etl.status import standardize_payment_status
from app.imports.validators import REQUIRED_COLUMNS, parse_source_file, validate_rows
from app.services.analytics_runner import run_account_prioritization
from app.services.model_lifecycle import cart_for_current_run
from app.services.storage import SourceStorage, sanitize_filename


def _persist_source_and_invoices(
    db: Session, batch_id: str, frames: list[pd.DataFrame],
) -> None:
    source_rows = []
    for frame in frames:
        converted = dataframe_to_source_rows(frame, import_batch_id=batch_id)
        for source, (_, row) in zip(converted, frame.iterrows(), strict=True):
            payload = {column: str(row[column]) for column in REQUIRED_COLUMNS}
            payload.update({
                "source_sheet": str(row["source_sheet"]),
                "source_row_number": int(row["source_row_number"]),
            })
            raw = RawSourceRow(
                import_batch_id=batch_id,
                source_sheet=str(row["source_sheet"]),
                source_row_number=int(row["source_row_number"]),
                customer_name_raw=str(row["CUSTOMER NAME"]),
                si_no=str(row["SI NO."]),
                si_date_raw=str(row["SI DATE"]),
                si_amount_raw=str(row["SI AMOUNT"]),
                cr_no=str(row["CR NO."]),
                cr_date_raw=str(row["CR DATE"]),
                cr_amount_raw=str(row["CR AMOUNT"]),
                ewt_raw=str(row["EWT"]),
                payment_mode_raw=str(row["PAYMENT MODE"]),
                payment_status_raw=str(row["PAYMENT STATUS"]),
                canonical_payload=payload,
            )
            db.add(raw)
            db.flush()
            source.raw_source_row_id = raw.raw_source_row_id
            source_rows.append(source)
    groupable = [
        row for row in source_rows
        if row.standardized_account_name and row.si_no and not pd.isna(row.si_date) and row.si_amount > 0
    ]
    groups = group_invoices(groupable)
    accounts = ensure_accounts(db, [group.standardized_account_name for group in groups])
    for group in groups:
        conflicting = db.scalars(select(InvoiceGroupRecord).where(
            InvoiceGroupRecord.standardized_account_name == group.standardized_account_name,
            InvoiceGroupRecord.si_no == group.si_no,
            InvoiceGroupRecord.si_date == group.si_date.date(),
            InvoiceGroupRecord.si_amount != group.si_amount,
        )).all()
        if conflicting:
            group.conflicting_invoice = True
            group.review_reason = "Conflicting SI amount for the same account/SI/date; excluded pending review."
            for candidate in conflicting:
                candidate.conflicting_invoice = True
                candidate.rfm_eligible = False
                candidate.settlement_eligible = False
                candidate.review_reason = group.review_reason
        record = db.get(InvoiceGroupRecord, group.invoice_group_id)
        if record is None:
            record = InvoiceGroupRecord(
                invoice_group_id=group.invoice_group_id, import_batch_id=batch_id,
                account_key=accounts[group.standardized_account_name].account_key,
                standardized_account_name=group.standardized_account_name, si_no=group.si_no,
                si_date=group.si_date.date(), si_amount=group.si_amount,
                payment_status=group.payment_status,
                final_cr_date=group.final_cr_date.date() if group.final_cr_date is not None else None,
                total_cr_amount=group.total_cr_amount, total_ewt=group.total_ewt,
                reconciliation_amount=group.reconciliation_amount,
                reconciliation_difference=group.reconciliation_difference,
                reconciled=group.reconciled, review_reason=group.review_reason,
                is_cancelled=group.is_cancelled, conflicting_invoice=group.conflicting_invoice,
                rfm_eligible=group.rfm_eligible,
                settlement_eligible=group.settlement_eligible,
                settlement_days=group.settlement_days,
            )
            db.add(record)
            db.flush()
        elif (
            record.total_cr_amount != group.total_cr_amount
            or record.total_ewt != group.total_ewt
            or record.payment_status != group.payment_status
        ):
            record.conflicting_invoice = True
            record.rfm_eligible = False
            record.settlement_eligible = False
            record.review_reason = "Repeated invoice has inconsistent collection/status evidence; excluded pending review."
        for row in group.rows:
            if row.raw_source_row_id:
                db.add(InvoiceGroupLineage(
                    invoice_group_id=record.invoice_group_id,
                    raw_source_row_id=row.raw_source_row_id,
                ))


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
        cancelled += sum(standardize_payment_status(value) == "Cancelled" for value in frame["PAYMENT STATUS"])
        issues.extend(validate_rows(frame))
    preview_rows = [
        row
        for frame in parsed.frames.values()
        for row in dataframe_to_source_rows(frame, import_batch_id="preview")
        if row.standardized_account_name and row.si_no and not pd.isna(row.si_date) and row.si_amount > 0
    ]
    preview_groups = group_invoices(preview_rows)
    error_rows = {(issue.source_sheet, issue.row_number) for issue in issues if issue.severity == "error" and issue.row_number is not None}
    warning_rows = {(issue.source_sheet, issue.row_number) for issue in issues if issue.severity == "warning" and issue.row_number is not None}
    duplicate = db.scalar(select(ImportBatch).where(ImportBatch.file_hash == parsed.file_hash, ImportBatch.status == "committed"))
    batch = ImportBatch(
        file_name=safe_name, file_hash=parsed.file_hash, uploaded_by=user.user_id, status="previewed",
        rows_discovered=rows_discovered, rows_accepted=max(0, rows_discovered - len(error_rows)),
        rows_flagged=len(warning_rows), rows_excluded=len(error_rows),
        cancelled_count=cancelled,
    )
    db.add(batch)
    db.flush()
    batch.storage_path = SourceStorage().put(batch.import_batch_id, safe_name, content)
    for issue in issues:
        db.add(ImportRowIssue(
            import_batch_id=batch.import_batch_id, source_sheet=issue.source_sheet,
            row_number=issue.row_number, column_name=issue.column, severity=issue.severity,
            message=issue.message, issue_type=issue.issue_type,
        ))
    audit(db, user.user_id, "import_preview", "import_batch", batch.import_batch_id,
          {"file_hash": parsed.file_hash, "rows": rows_discovered, "duplicate": bool(duplicate)})
    db.commit()
    return {
        "import_batch_id": batch.import_batch_id, "file_name": safe_name, "file_hash": parsed.file_hash,
        "sheets": list(parsed.frames), "rows_discovered": rows_discovered, "cancelled_count": cancelled,
        "issues": [asdict(issue) for issue in issues], "duplicate_committed_file": bool(duplicate),
        "quality_rates": {
            "cancelled_row_rate": cancelled / rows_discovered if rows_discovered else 0.0,
            "invalid_date_issue_rate": sum(i.issue_type in {"invalid_si_date", "invalid_cr_date"} for i in issues) / rows_discovered if rows_discovered else 0.0,
            "chronology_issue_rate": sum(i.issue_type == "negative_chronology" for i in issues) / rows_discovered if rows_discovered else 0.0,
            "reconciliation_issue_rate": (
                sum(group.payment_status == "Fully Paid" and not group.reconciled for group in preview_groups)
                / len(preview_groups) if preview_groups else 0.0
            ),
        },
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
        if not duplicate:
            _persist_source_and_invoices(db, batch_id, frames)
        batch.status = "committed"
        batch.committed_at = datetime.now(timezone.utc)
        db.flush()
        run = AnalyticsRun(status="running", latest_import_batch_id=batch_id, code_version="final-four-criterion")
        db.add(run)
        db.flush()
        cumulative_groups = load_invoice_groups(db)
        cart = cart_for_current_run(db, cumulative_groups)
        result = asdict(run_account_prioritization(cumulative_groups, cart_result=cart))
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
