from __future__ import annotations

import pandas as pd
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser

from app.db.models import (
    Base, CollectionCorrectionReview, ImportBatch, InvoiceGroupRecord,
)
from app.services.import_workflow import _persist_raw_rows, resolve_collection_correction

COLUMNS = [
    "ACCOUNT NAMES", "SI NO.", "SI DATE", "SI AMOUNT", "CR NO.", "CR DATE",
    "CR AMOUNT", "EWT", "PAYMENT MODE", "PAYMENT STATUS",
]


def frame(**changes) -> pd.DataFrame:
    row = {
        "ACCOUNT NAMES": "ACME", "SI NO.": "SI-1", "SI DATE": "2026-01-01",
        "SI AMOUNT": "100", "CR NO.": "CR-1", "CR DATE": "2026-01-10",
        "CR AMOUNT": "100", "EWT": "0", "PAYMENT MODE": "Bank",
        "PAYMENT STATUS": "Fully Paid",
    }
    row.update(changes)
    result = pd.DataFrame([row], columns=COLUMNS)
    result["source_sheet"] = "CSV"
    result["source_row_number"] = 2
    return result


def add_batch(db: Session, batch_id: str, source: pd.DataFrame) -> None:
    batch = ImportBatch(
        import_batch_id=batch_id,
        file_name=f"{batch_id}.csv",
        file_hash=batch_id.replace("-", "").ljust(64, "0")[:64],
        status="previewed",
    )
    db.add(batch)
    db.flush()
    _persist_raw_rows(db, batch_id, [source])
    batch.status = "committed"
    db.commit()


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def invoice(db: Session) -> InvoiceGroupRecord:
    return db.scalars(select(InvoiceGroupRecord).order_by(InvoiceGroupRecord.si_amount)).first()


def test_exact_duplicate_row_is_a_no_op(db):
    add_batch(db, "00000000-0000-4000-8000-000000000001", frame())
    add_batch(db, "00000000-0000-4000-8000-000000000002", frame())
    assert invoice(db).total_cr_amount == 100
    assert db.scalar(select(CollectionCorrectionReview)) is None


def test_late_genuinely_new_cr_is_additive_without_invoice_inflation(db):
    add_batch(db, "00000000-0000-4000-8000-000000000003", frame(**{"CR AMOUNT": "60"}))
    add_batch(db, "00000000-0000-4000-8000-000000000004", frame(**{
        "CR NO.": "CR-2", "CR DATE": "2026-01-11", "CR AMOUNT": "40",
    }))
    rows = db.scalars(select(InvoiceGroupRecord)).all()
    assert len(rows) == 1
    assert rows[0].total_cr_amount == 100
    assert rows[0].conflicting_invoice is False


@pytest.mark.parametrize("change", [
    {"CR AMOUNT": "90"},
    {"CR AMOUNT": "98", "EWT": "2"},
    {"PAYMENT STATUS": "Partially Paid"},
])
def test_changed_existing_collection_evidence_is_quarantined_not_added(db, change):
    add_batch(db, "00000000-0000-4000-8000-000000000005", frame())
    add_batch(db, "00000000-0000-4000-8000-000000000006", frame(**change))
    row = invoice(db)
    review = db.scalar(select(CollectionCorrectionReview))
    assert review is not None and review.status == "pending"
    assert row.conflicting_invoice is True
    assert row.rfm_eligible is False
    assert row.settlement_eligible is False
    assert float(row.total_cr_amount) != 190.0


def test_conflicting_si_amount_is_quarantined(db):
    add_batch(db, "00000000-0000-4000-8000-000000000007", frame())
    add_batch(db, "00000000-0000-4000-8000-000000000008", frame(**{"SI AMOUNT": "110"}))
    rows = db.scalars(select(InvoiceGroupRecord)).all()
    assert len(rows) == 2
    assert all(row.conflicting_invoice and not row.rfm_eligible for row in rows)


def test_audited_resolution_selects_one_collection_version_and_reconstructs(db):
    add_batch(db, "00000000-0000-4000-8000-000000000009", frame())
    add_batch(db, "00000000-0000-4000-8000-000000000010", frame(**{"CR AMOUNT": "90"}))
    review = db.scalar(select(CollectionCorrectionReview))
    selected = review.raw_source_row_ids[-1]
    resolve_collection_correction(
        db,
        AuthenticatedUser(
            user_id="00000000-0000-4000-8000-000000000001",
            role="administrator",
        ),
        review.collection_correction_review_id,
        selected,
        "Confirmed corrected collection amount against source record.",
    )
    db.commit()
    row = invoice(db)
    assert review.status == "resolved"
    assert review.selected_raw_source_row_id == selected
    assert row.conflicting_invoice is False
    assert float(row.total_cr_amount) == 90.0
    assert row.rfm_eligible is True
    with pytest.raises(HTTPException) as error:
        resolve_collection_correction(
            db,
            AuthenticatedUser(
                user_id="00000000-0000-4000-8000-000000000001",
                role="administrator",
            ),
            review.collection_correction_review_id,
            selected,
            "Attempted second resolution.",
        )
    assert error.value.status_code == 409
