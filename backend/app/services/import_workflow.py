from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
import logging

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.core.config import get_settings
from app.db.models import (
    AnalyticsRun,
    DimAccount,
    ImportBatch,
    ImportRowIssue,
    InvoiceGroupLineage,
    InvoiceGroupRecord,
    RawSourceRow,
)
from app.db.repository import audit, ensure_accounts, load_invoice_groups, persist_run_output
from app.etl.invoices import SourceRow, dataframe_to_source_rows, group_invoices
from app.etl.status import standardize_payment_status
from app.imports.validators import REQUIRED_COLUMNS, parse_source_file, validate_rows
from app.services.analytics_runner import run_account_prioritization, validate_analysis_reference
from app.services.model_lifecycle import future_transaction_for_current_run
from app.services.storage import SourceStorage, sanitize_filename

logger = logging.getLogger(__name__)


def _source_business_key(row: SourceRow) -> tuple:
    return (
        row.standardized_account_name,
        row.si_no,
        str(row.si_date),
        str(row.si_amount),
        row.cr_no,
        str(row.cr_date),
        str(row.cr_amount),
        str(row.ewt),
        row.payment_mode,
        row.payment_status,
    )


def _raw_to_source(raw: RawSourceRow) -> SourceRow:
    frame = pd.DataFrame([{**raw.canonical_payload, "source_sheet": raw.source_sheet,
                           "source_row_number": raw.source_row_number}])
    source = dataframe_to_source_rows(frame, import_batch_id=raw.import_batch_id)[0]
    source.raw_source_row_id = raw.raw_source_row_id
    return source


def _reconstruct_invoice_groups(db: Session, current_batch_id: str) -> None:
    raw_rows = db.scalars(
        select(RawSourceRow)
        .join(ImportBatch, ImportBatch.import_batch_id == RawSourceRow.import_batch_id)
        .where(or_(ImportBatch.status == "committed", ImportBatch.import_batch_id == current_batch_id))
        .order_by(RawSourceRow.created_at, RawSourceRow.raw_source_row_id)
    ).all()
    unique: dict[tuple, SourceRow] = {}
    duplicate_ids: dict[tuple, list[str]] = {}
    for raw in raw_rows:
        source = _raw_to_source(raw)
        key = _source_business_key(source)
        duplicate_ids.setdefault(key, []).append(raw.raw_source_row_id)
        unique.setdefault(key, source)
    groupable = [
        row for row in unique.values()
        if row.standardized_account_name and row.si_no
        and not pd.isna(row.si_date) and row.si_amount > 0
    ]
    groups = group_invoices(groupable)
    accounts = ensure_accounts(db, [group.standardized_account_name for group in groups])
    for group in groups:
        record = db.get(InvoiceGroupRecord, group.invoice_group_id)
        if record is None:
            record = InvoiceGroupRecord(
                invoice_group_id=group.invoice_group_id,
                import_batch_id=current_batch_id,
                account_key=accounts[group.standardized_account_name].account_key,
                standardized_account_name=group.standardized_account_name,
                si_no=group.si_no,
                si_date=group.si_date.date(),
                si_amount=group.si_amount,
                payment_status=group.payment_status,
                final_cr_date=None,
                total_cr_amount=0,
                total_ewt=0,
                reconciliation_amount=0,
                reconciliation_difference=0,
                reconciled=False,
                is_cancelled=False,
                conflicting_invoice=False,
                rfm_eligible=False,
                settlement_eligible=False,
            )
            db.add(record)
            db.flush()
        record.payment_status = group.payment_status
        record.final_cr_date = group.final_cr_date.date() if group.final_cr_date is not None else None
        record.total_cr_amount = group.total_cr_amount
        record.total_ewt = group.total_ewt
        record.reconciliation_amount = group.reconciliation_amount
        record.reconciliation_difference = group.reconciliation_difference
        record.reconciled = group.reconciled
        record.review_reason = group.review_reason
        record.is_cancelled = group.is_cancelled
        record.conflicting_invoice = group.conflicting_invoice
        record.rfm_eligible = group.rfm_eligible
        record.settlement_eligible = group.settlement_eligible
        record.settlement_days = group.settlement_days
        for row in group.rows:
            for raw_id in duplicate_ids.get(_source_business_key(row), []):
                existing = db.get(InvoiceGroupLineage, {
                    "invoice_group_id": record.invoice_group_id,
                    "raw_source_row_id": raw_id,
                })
                if existing is None:
                    db.add(InvoiceGroupLineage(
                        invoice_group_id=record.invoice_group_id,
                        raw_source_row_id=raw_id,
                    ))
    identities: dict[tuple[str, str, date], list[InvoiceGroupRecord]] = {}
    for record in db.scalars(select(InvoiceGroupRecord)).all():
        identities.setdefault(
            (record.standardized_account_name, record.si_no, record.si_date), []
        ).append(record)
    for records in identities.values():
        if len({str(record.si_amount) for record in records}) <= 1:
            continue
        for record in records:
            record.conflicting_invoice = True
            record.rfm_eligible = False
            record.settlement_eligible = False
            record.review_reason = (
                "Controlled correction required: the same account/SI/date has differing SI amounts."
            )


def _persist_raw_rows(
    db: Session,
    batch_id: str,
    frames: list[pd.DataFrame],
) -> None:
    for frame in frames:
        for _, row in frame.iterrows():
            payload = {column: str(row[column]) for column in REQUIRED_COLUMNS}
            payload.update({
                "source_sheet": str(row["source_sheet"]),
                "source_row_number": int(row["source_row_number"]),
            })
            db.add(RawSourceRow(
                import_batch_id=batch_id,
                source_sheet=str(row["source_sheet"]),
                source_row_number=int(row["source_row_number"]),
                customer_name_raw=str(row["ACCOUNT NAMES"]),
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
            ))
    db.flush()
    _reconstruct_invoice_groups(db, batch_id)


def preview_source(db: Session, user: AuthenticatedUser, file_name: str, content: bytes) -> dict:
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_bytes // 1_000_000} MB limit.")
    safe_name = sanitize_filename(file_name)
    parsed = parse_source_file(safe_name, content)
    issues = list(parsed.issues)
    rows_discovered = 0
    cancelled = 0
    evidence_dates: list[pd.Timestamp] = []
    for frame in parsed.frames.values():
        rows_discovered += len(frame)
        cancelled += sum(
            standardize_payment_status(value) == "Cancelled"
            for value in frame["PAYMENT STATUS"]
        )
        issues.extend(validate_rows(frame))
        for column in ("SI DATE", "CR DATE"):
            evidence_dates.extend(
                value for value in pd.to_datetime(frame[column], errors="coerce")
                if not pd.isna(value)
            )
    preview_rows = [
        row for frame in parsed.frames.values()
        for row in dataframe_to_source_rows(frame, import_batch_id="preview")
        if row.standardized_account_name and row.si_no
        and not pd.isna(row.si_date) and row.si_amount > 0
    ]
    preview_groups = group_invoices(preview_rows)
    error_rows = {
        (issue.source_sheet, issue.row_number) for issue in issues
        if issue.severity == "error" and issue.row_number is not None
    }
    warning_rows = {
        (issue.source_sheet, issue.row_number) for issue in issues
        if issue.severity == "warning" and issue.row_number is not None
    }
    duplicate = db.scalar(select(ImportBatch).where(
        ImportBatch.file_hash == parsed.file_hash,
        ImportBatch.status == "committed",
    ))
    batch = ImportBatch(
        file_name=safe_name,
        file_hash=parsed.file_hash,
        uploaded_by=user.user_id,
        status="previewed",
        rows_discovered=rows_discovered,
        rows_accepted=max(0, rows_discovered - len(error_rows)),
        rows_flagged=len(warning_rows),
        rows_excluded=len(error_rows),
        cancelled_count=cancelled,
    )
    db.add(batch)
    db.flush()
    batch.storage_path = SourceStorage().put(batch.import_batch_id, safe_name, content)
    for issue in issues:
        db.add(ImportRowIssue(
            import_batch_id=batch.import_batch_id,
            source_sheet=issue.source_sheet,
            row_number=issue.row_number,
            column_name=issue.column,
            severity=issue.severity,
            message=issue.message,
            issue_type=issue.issue_type,
        ))
    audit(db, user.user_id, "import_preview", "import_batch", batch.import_batch_id, {
        "file_hash": parsed.file_hash,
        "rows": rows_discovered,
        "duplicate": bool(duplicate),
    })
    db.commit()
    latest_evidence = max(evidence_dates).date().isoformat() if evidence_dates else None
    return {
        "import_batch_id": batch.import_batch_id,
        "file_name": safe_name,
        "file_hash": parsed.file_hash,
        "sheets": list(parsed.frames),
        "rows_discovered": rows_discovered,
        "cancelled_count": cancelled,
        "latest_evidence_date": latest_evidence,
        "analysis_reference_required": True,
        "issues": [asdict(issue) for issue in issues],
        "duplicate_committed_file": bool(duplicate),
        "quality_rates": {
            "cancelled_row_rate": cancelled / rows_discovered if rows_discovered else 0.0,
            "invalid_date_issue_rate": sum(
                i.issue_type in {"invalid_si_date", "invalid_cr_date"} for i in issues
            ) / rows_discovered if rows_discovered else 0.0,
            "chronology_issue_rate": sum(
                i.issue_type == "negative_chronology" for i in issues
            ) / rows_discovered if rows_discovered else 0.0,
            "reconciliation_issue_rate": (
                sum(group.payment_status == "Fully Paid" and not group.reconciled
                    for group in preview_groups) / len(preview_groups)
                if preview_groups else 0.0
            ),
        },
        "can_commit": not any(issue.severity == "error" for issue in issues) and not duplicate,
        "status": "PREVIEW",
    }


def commit_source(
    db: Session,
    user: AuthenticatedUser,
    batch_id: str,
    analysis_reference_date: date,
) -> dict:
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Import preview not found.")
    if batch.status == "committed":
        raise HTTPException(409, "This import batch is already committed.")
    errors = db.scalar(select(ImportRowIssue).where(
        ImportRowIssue.import_batch_id == batch_id,
        ImportRowIssue.severity == "error",
    ))
    if errors:
        raise HTTPException(422, "Import has validation errors and cannot be committed.")
    duplicate = db.scalar(select(ImportBatch).where(
        ImportBatch.file_hash == batch.file_hash,
        ImportBatch.status == "committed",
        ImportBatch.import_batch_id != batch_id,
    ))
    if duplicate:
        batch.status = "blocked_duplicate"
        audit(db, user.user_id, "duplicate_import_blocked", "import_batch", batch_id, {
            "duplicate_of": duplicate.import_batch_id,
            "semantics": "audited_no_op",
        })
        db.commit()
        raise HTTPException(409, "Exact duplicate re-upload blocked as an audited no-op.")
    try:
        content = SourceStorage().get(batch.storage_path or "")
        parsed = parse_source_file(batch.file_name, content)
        _persist_raw_rows(db, batch_id, list(parsed.frames.values()))
        cumulative_groups = load_invoice_groups(db)
        validate_analysis_reference(cumulative_groups, pd.Timestamp(analysis_reference_date))
        batch.analysis_reference_date = analysis_reference_date
        batch.status = "committed"
        batch.committed_at = datetime.now(timezone.utc)
        db.flush()
        eligible_accounts = set(db.scalars(
            select(DimAccount.standardized_account_name).where(
                DimAccount.b2b_priority_eligible.is_(True)
            )
        ).all())
        predictive = future_transaction_for_current_run(
            db, cumulative_groups, pd.Timestamp(analysis_reference_date), eligible_accounts,
        )
        result = asdict(run_account_prioritization(
            cumulative_groups,
            pd.Timestamp(analysis_reference_date),
            eligible_accounts,
            predictive_result=predictive,
        ))
        run = AnalyticsRun(
            status="running",
            latest_import_batch_id=batch_id,
            analysis_reference_date=analysis_reference_date,
            methodology_version=DEFAULT_ANALYTICS_CONFIG.version,
            code_version=DEFAULT_ANALYTICS_CONFIG.version,
        )
        db.add(run)
        db.flush()
        persist_run_output(db, run, result)
        batch.analysis_run_id = run.analysis_run_id
        audit(db, user.user_id, "import_committed", "import_batch", batch_id, {
            "analysis_run_id": run.analysis_run_id,
            "analysis_reference_date": analysis_reference_date.isoformat(),
        })
        db.commit()
        return {
            "status": "COMMITTED",
            "import_batch_id": batch_id,
            "analysis_run_id": run.analysis_run_id,
            "prioritized_accounts": len(result["priorities"]),
            "analysis_reference_date": result["analysis_reference_date"],
            "warnings": result["warnings"],
        }
    except HTTPException:
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.exception("Atomic import publication failed for batch %s", batch_id)
        db.rollback()
        failed_batch = db.get(ImportBatch, batch_id)
        if failed_batch:
            failed_batch.status = "failed"
        failed_run = AnalyticsRun(
            status="failed",
            latest_import_batch_id=batch_id,
            completed_at=datetime.now(timezone.utc),
            methodology_version=DEFAULT_ANALYTICS_CONFIG.version,
            errors=[{"message": "Analytics publication failed safely."}],
        )
        db.add(failed_run)
        audit(db, user.user_id, "import_failed", "import_batch", batch_id, {
            "error_type": type(exc).__name__,
        })
        db.commit()
        raise HTTPException(
            500,
            "Import failed safely; the previous successful analysis remains current.",
        ) from exc