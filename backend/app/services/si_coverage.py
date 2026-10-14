"""Traceable SI coverage confirmations, separate from observed transaction dates."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import ImportBatch, ImportRowIssue, InvoiceGroupRecord, SICoverageConfirmation
from app.db.repository import audit
from app.services.locked_packages import FINAL_PACKAGE_SHA256, read_package_csv, verified_package
from app.services.study_predictions import COMPLETENESS_MEMBER, FORECAST_ORIGIN, validate_study_prediction_package


def latest_verified_si_coverage(db: Session) -> date | None:
    first_conflict = db.scalar(select(func.min(InvoiceGroupRecord.si_date)).where(
        InvoiceGroupRecord.review_reason.like(
            "Controlled correction required: the same account/SI/date%"
        )
    ))
    statement = select(SICoverageConfirmation.complete_through).outerjoin(
        ImportBatch, SICoverageConfirmation.source_batch_id == ImportBatch.import_batch_id
    ).where(
        SICoverageConfirmation.superseded_at.is_(None),
        or_(SICoverageConfirmation.source_package_hash.is_not(None),
            ImportBatch.status == "committed"),
    )
    if first_conflict:
        statement = statement.where(SICoverageConfirmation.complete_through < first_conflict)
    return db.scalar(statement.order_by(
        SICoverageConfirmation.complete_through.desc()).limit(1))


def confirm_si_coverage(
    db: Session, *, complete_through: date, evidence_type: str,
    evidence_reference: str, evidence_basis: str, confirmed_on: date | None,
    recorded_by: str, source_batch_id: str | None = None,
    source_package_hash: str | None = None,
    supersedes_confirmation_id: str | None = None,
) -> SICoverageConfirmation:
    if complete_through > date.today() or (confirmed_on and confirmed_on > date.today()):
        raise ValueError("SI coverage or confirmation cannot be dated in the future.")
    if evidence_type not in {"Client confirmation", "Audited source reconciliation"}:
        raise ValueError("A client confirmation or audited source reconciliation is required.")
    if not evidence_reference.strip() or not evidence_basis.strip():
        raise ValueError("An evidence reference and basis are required.")
    if confirmed_on is None and source_package_hash is None:
        raise ValueError("A dated confirmation is required for new coverage evidence.")
    if confirmed_on and confirmed_on < complete_through:
        raise ValueError("Confirmation cannot predate its complete-through date.")
    if source_package_hash is None and source_batch_id is None:
        raise ValueError("New coverage evidence must identify the source import batch.")
    if source_batch_id and db.get(ImportBatch, source_batch_id) is None:
        raise ValueError("Referenced import batch does not exist.")
    previous = None
    if supersedes_confirmation_id:
        previous = db.get(SICoverageConfirmation, supersedes_confirmation_id)
        if previous is None or previous.superseded_at is not None:
            raise ValueError("Coverage record to supersede is not active.")
    record = SICoverageConfirmation(
        complete_through=complete_through, evidence_type=evidence_type,
        evidence_reference=evidence_reference.strip(), evidence_basis=evidence_basis.strip(),
        confirmed_on=confirmed_on, recorded_by=recorded_by,
        source_batch_id=source_batch_id, source_package_hash=source_package_hash,
        supersedes_confirmation_id=supersedes_confirmation_id,
    )
    db.add(record)
    db.flush()
    if previous:
        previous.superseded_at = datetime.now(timezone.utc)
    audit(db, recorded_by, "si_coverage_confirmed", "si_coverage_confirmation", record.confirmation_id, {
        "complete_through": complete_through.isoformat(),
        "evidence_type": evidence_type,
        "evidence_reference": evidence_reference.strip(),
        "supersedes": supersedes_confirmation_id,
    })
    return record


def require_si_coverage(
    db: Session, reference: date, current_batch_id: str | None = None,
) -> SICoverageConfirmation:
    statement = select(SICoverageConfirmation).outerjoin(
        ImportBatch, SICoverageConfirmation.source_batch_id == ImportBatch.import_batch_id
    ).where(
        SICoverageConfirmation.superseded_at.is_(None),
        SICoverageConfirmation.complete_through >= reference,
    )
    if current_batch_id:
        statement = statement.where(or_(
            (SICoverageConfirmation.source_batch_id == current_batch_id)
            & (ImportBatch.status == "previewed"),
            SICoverageConfirmation.source_package_hash.is_not(None),
        ))
    else:
        statement = statement.where(or_(
            SICoverageConfirmation.source_package_hash.is_not(None),
            ImportBatch.status == "committed",
        ))
    record = db.scalar(statement.order_by(
        SICoverageConfirmation.complete_through.asc()).limit(1))
    if record is None:
        raise ValueError(
            "No independently recorded SI complete-through evidence covers this analysis reference. "
            "An administrator must record supported client confirmation or audited reconciliation first."
        )
    critical = db.scalar(select(ImportRowIssue).join(
        ImportBatch, ImportBatch.import_batch_id == ImportRowIssue.import_batch_id
    ).where(
        ImportBatch.status == "committed",
        ImportRowIssue.severity == "error",
    ).limit(1))
    if critical:
        raise ValueError("Unresolved critical SI source issues prevent complete-coverage publication.")
    invoice_conflict = db.scalar(select(InvoiceGroupRecord).where(
        InvoiceGroupRecord.si_date <= reference,
        InvoiceGroupRecord.review_reason.like("Controlled correction required: the same account/SI/date%"),
    ).limit(1))
    if invoice_conflict:
        raise ValueError("An unresolved conflicting SI amount prevents complete-coverage publication.")
    return record


def seed_locked_study_coverage(db: Session, package_path: str, actor: str) -> SICoverageConfirmation:
    _, content = verified_package(package_path, FINAL_PACKAGE_SHA256)
    validate_study_prediction_package(content)
    existing = db.scalar(select(SICoverageConfirmation).where(
        SICoverageConfirmation.source_package_hash == FINAL_PACKAGE_SHA256,
        SICoverageConfirmation.complete_through == FORECAST_ORIGIN,
    ))
    if existing:
        return existing
    frame = read_package_csv(content, COMPLETENESS_MEMBER)
    row = frame.loc[frame["scope"] == "2025 Sales Invoice coverage"].iloc[0]
    return confirm_si_coverage(
        db, complete_through=FORECAST_ORIGIN, evidence_type="Client confirmation",
        evidence_reference=f"{COMPLETENESS_MEMBER} in SHA-256 {FINAL_PACKAGE_SHA256}",
        evidence_basis=str(row["basis"]), confirmed_on=None, recorded_by=actor,
        source_package_hash=FINAL_PACKAGE_SHA256,
    )
