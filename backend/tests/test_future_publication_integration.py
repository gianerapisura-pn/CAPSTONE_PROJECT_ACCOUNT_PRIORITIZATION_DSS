from __future__ import annotations

from datetime import date

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser
from app.db.models import AnalyticsRun, Base, DimAccount, ImportBatch, InvoiceGroupRecord, RawSourceRow
from app.db.repository import latest_successful_run, run_payload
from app.services.import_workflow import commit_source, preview_source
from app.services.si_coverage import confirm_si_coverage
from app.services.storage import SourceStorage
from app.main import RunRequest, native_insights, run_analytics


ADMIN = AuthenticatedUser("00000000-0000-4000-8000-000000000001", "administrator")
HEADER = "ACCOUNT NAMES,SI NO.,SI DATE,SI AMOUNT,CR NO.,CR DATE,CR AMOUNT,EWT,PAYMENT MODE,PAYMENT STATUS\n"
REFERENCE = date(2026, 9, 30)


def test_future_source_publications_are_isolated_and_idempotent(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    stored = {}
    monkeypatch.setattr(SourceStorage, "put", lambda self, batch_id, name, content: stored.setdefault(batch_id, content) and batch_id)
    monkeypatch.setattr(SourceStorage, "get", lambda self, path: stored[path])

    def publish(db: Session, content: bytes):
        preview = preview_source(db, ADMIN, "source.csv", content)
        assert preview["can_commit"]
        confirm_si_coverage(
            db, complete_through=REFERENCE, evidence_type="Client confirmation",
            evidence_reference=f"Synthetic test confirmation for {preview['file_hash']}",
            evidence_basis="Isolated synthetic SI file checked through the reference date",
            confirmed_on=date(2026, 10, 1), recorded_by=ADMIN.user_id,
            source_batch_id=preview["import_batch_id"],
        )
        db.commit()
        return preview, commit_source(db, ADMIN, preview["import_batch_id"], REFERENCE)

    try:
        with Session(engine) as db:
            first = (HEADER + "ACME,SI-1,2025-07-01,100,,,,,Bank,Fully Paid\n").encode()
            first_preview, first_result = publish(db, first)
            first_run = db.get(AnalyticsRun, first_result["analysis_run_id"])
            first_payload = run_payload(db, first_run)
            assert first_payload["business_baselines"]
            assert not first_payload["rfm"]  # Unknown B2B context stays outside analysis.

            acme = db.scalar(select(DimAccount).where(DimAccount.standardized_account_name == "ACME"))
            acme.b2b_priority_eligible = True
            acme.account_status = "Client-Confirmed Active"
            db.commit()
            second = (HEADER + "ACME,SI-1,2025-07-01,100,CR-1,2026-01-15,100,0,Bank,Fully Paid\n"
                      "NEW FUTURE ACCOUNT,SI-2,2026-04-02,80,CR-2,2026-04-20,80,0,Bank,Fully Paid\n").encode()
            _, second_result = publish(db, second)
            second_run = db.get(AnalyticsRun, second_result["analysis_run_id"])
            second_payload = run_payload(db, second_run)
            assert second_run.analysis_run_id != first_run.analysis_run_id
            assert run_payload(db, first_run) == first_payload
            assert any(row["account"] == "ACME" for row in second_payload["rfm"])
            assert all(row["account"] != "NEW FUTURE ACCOUNT" for row in second_payload["rfm"])
            invoice = db.scalar(select(InvoiceGroupRecord).where(InvoiceGroupRecord.si_no == "SI-1"))
            assert invoice.settlement_eligible
            assert db.scalar(select(func.count()).select_from(InvoiceGroupRecord).where(
                InvoiceGroupRecord.si_no == "SI-1")) == 1

            duplicate = preview_source(db, ADMIN, "source.csv", second)
            assert duplicate["duplicate_committed_file"]
            with pytest.raises(HTTPException) as error:
                commit_source(db, ADMIN, duplicate["import_batch_id"], REFERENCE)
            assert error.value.status_code == 409

            # A different byte stream with the same SI/CR must not duplicate an invoice.
            _, third_result = publish(db, second + b"\n")
            assert third_result["status"] == "COMMITTED"
            assert db.scalar(select(func.count()).select_from(InvoiceGroupRecord).where(
                InvoiceGroupRecord.si_no == "SI-1")) == 1

            newcomer = db.scalar(select(DimAccount).where(
                DimAccount.standardized_account_name == "NEW FUTURE ACCOUNT"))
            newcomer.b2b_priority_eligible = True
            newcomer.account_status = "Client-Confirmed Active"
            db.commit()
            new_run = run_analytics(
                RunRequest(analysis_reference_date=REFERENCE), BackgroundTasks(), ADMIN, db
            )
            new_payload = run_payload(db, db.get(AnalyticsRun, new_run["analysis_run_id"]))
            assert any(row["account"] == "NEW FUTURE ACCOUNT" for row in new_payload["rfm"])
            report = native_insights(user=ADMIN, db=db)
            assert report["run"]["analysis_run_id"] == new_run["analysis_run_id"]
            assert run_payload(db, second_run) == second_payload
    finally:
        engine.dispose()


def test_failed_future_publication_preserves_previous_run(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    stored = {}
    monkeypatch.setattr(SourceStorage, "put", lambda self, batch_id, name, content: stored.setdefault(batch_id, content) and batch_id)
    monkeypatch.setattr(SourceStorage, "get", lambda self, path: stored[path])
    try:
        with Session(engine) as db:
            first = preview_source(db, ADMIN, "first.csv", (
                HEADER + "ACME,SI-1,2025-07-01,100,CR-1,2025-07-10,100,0,Bank,Fully Paid\n"
            ).encode())
            confirm_si_coverage(
                db, complete_through=REFERENCE, evidence_type="Client confirmation",
                evidence_reference="Synthetic source coverage", evidence_basis="Test SI records reconciled",
                confirmed_on=date(2026, 10, 1), recorded_by=ADMIN.user_id,
                source_batch_id=first["import_batch_id"],
            )
            db.commit()
            published = commit_source(db, ADMIN, first["import_batch_id"], REFERENCE)
            previous_id = published["analysis_run_id"]
            previous_payload = run_payload(db, db.get(AnalyticsRun, previous_id))

            second = preview_source(db, ADMIN, "second.csv", (
                HEADER + "NEW ACCOUNT,SI-2,2026-05-01,50,CR-2,2026-05-10,50,0,Bank,Fully Paid\n"
            ).encode())
            confirm_si_coverage(
                db, complete_through=REFERENCE, evidence_type="Client confirmation",
                evidence_reference="Second synthetic source coverage", evidence_basis="Test SI records reconciled",
                confirmed_on=date(2026, 10, 1), recorded_by=ADMIN.user_id,
                source_batch_id=second["import_batch_id"],
            )
            db.commit()

            def fail_persistence(*args):
                raise RuntimeError("Simulated persistence failure")

            monkeypatch.setattr("app.services.import_workflow.persist_run_output", fail_persistence)
            with pytest.raises(HTTPException) as error:
                commit_source(db, ADMIN, second["import_batch_id"], REFERENCE)
            assert error.value.status_code == 500
            assert latest_successful_run(db).analysis_run_id == previous_id
            assert run_payload(db, db.get(AnalyticsRun, previous_id)) == previous_payload
            assert db.get(ImportBatch, second["import_batch_id"]).status == "failed"
            assert db.scalar(select(func.count()).select_from(RawSourceRow).where(
                RawSourceRow.import_batch_id == second["import_batch_id"]
            )) == 0
    finally:
        engine.dispose()
