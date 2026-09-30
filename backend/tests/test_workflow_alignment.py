from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser, require_admin
from app.db.models import Base, CollectionCorrectionReview, RawSourceRow
from app.main import collection_correction_queue
from app.services.import_workflow import preview_source
from app.services.storage import SourceStorage


ADMIN = AuthenticatedUser(
    user_id="00000000-0000-4000-8000-000000000001", role="administrator",
)


def test_preview_separates_valid_si_and_final_cr_dates(monkeypatch):
    monkeypatch.setattr(SourceStorage, "put", lambda self, batch_id, name, content: "private/test.csv")
    data = (
        "ACCOUNT NAMES,SI NO.,SI DATE,SI AMOUNT,CR NO.,CR DATE,CR AMOUNT,EWT,PAYMENT MODE,PAYMENT STATUS\n"
        "ACME,SI-1,2025-07-01,100,CR-1,2026-02-01,100,0,Bank,Fully Paid\n"
        "ACME,SI-2,2030-01-01,100,,,,,Bank,Cancelled\n"
        "ACME,SI-3,2040-01-01,100,CR-3,2040-01-10,bad,0,Bank,Fully Paid\n"
    ).encode()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        preview = preview_source(db, ADMIN, "source.csv", data)

    assert preview["latest_valid_si_date"] == "2025-07-01"
    assert preview["latest_final_cr_date"] == "2026-02-01"
    assert preview["latest_evidence_date"] == "2026-02-01"
    assert preview["analysis_reference_required"] is True


def test_collection_correction_queue_returns_admin_candidate_evidence():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        raw = RawSourceRow(
            import_batch_id="00000000-0000-4000-8000-000000000010",
            source_sheet="CSV", source_row_number=2,
            customer_name_raw="ACME", si_no="SI-1", si_date_raw="2026-01-01",
            si_amount_raw="100", cr_no="CR-1", cr_date_raw="2026-01-10",
            cr_amount_raw="100", ewt_raw="0", payment_mode_raw="Bank",
            payment_status_raw="Fully Paid", canonical_payload={},
        )
        db.add(raw)
        db.flush()
        review = CollectionCorrectionReview(
            collection_identity="c" * 64, invoice_identity="i" * 64,
            raw_source_row_ids=[raw.raw_source_row_id], status="pending",
        )
        db.add(review)
        db.flush()
        result = collection_correction_queue(status="pending", user=ADMIN, db=db)

    assert len(result) == 1
    assert result[0]["candidates"][0]["raw_source_row_id"] == raw.raw_source_row_id
    assert result[0]["candidates"][0]["cr_amount"] == "100"
    assert require_admin in {
        dependency.call
        for route in __import__("app.main", fromlist=["app"]).app.routes
        if getattr(route, "path", None) == "/collection-corrections"
        for dependency in route.dependant.dependencies
    }
