from datetime import date

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.analytics.predictive.future_transaction import FutureTransactionResult
from app.db.models import AnalyticsRun, AuditLog, Base, DimAccount, ImportBatch, InvoiceGroupRecord
from app.db.repository import latest_successful_run, run_payload
from app.services.si_coverage import confirm_si_coverage
from scripts.publish_current_analytics import publish


ACTOR = "00000000-0000-4000-8000-000000000001"
REFERENCE = date(2025, 12, 31)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            batch = ImportBatch(file_name="synthetic.csv", file_hash="a" * 64, status="committed")
            session.add(batch)
            session.flush()
            for index, name in enumerate(("ALPHA", "BETA", "GAMMA"), start=1):
                account = DimAccount(
                    standardized_account_name=name, display_name=name,
                    entity_type="Business", business_category="Corporate",
                    b2b_priority_eligible=True, account_status="Client-Confirmed Active",
                    status_confirming_role="PESLC client representative",
                    identity_source_type="Official company/organization",
                    identity_source_reference="Synthetic registry",
                )
                session.add(account)
                session.flush()
                amount = index * 100
                session.add(InvoiceGroupRecord(
                    invoice_group_id=f"invoice-{index}", import_batch_id=batch.import_batch_id,
                    account_key=account.account_key, standardized_account_name=name,
                    si_no=f"SI-{index}", si_date=date(2025, index, 1), si_amount=amount,
                    payment_status="Fully Paid", final_cr_date=date(2025, index, 15),
                    total_cr_amount=amount, total_ewt=0, reconciliation_amount=amount,
                    reconciliation_difference=0, reconciled=True, is_cancelled=False,
                    rfm_eligible=True, settlement_eligible=True, settlement_days=14,
                ))
            session.commit()
            yield session, batch.import_batch_id
    finally:
        engine.dispose()


def allow_frozen_scoring(monkeypatch):
    monkeypatch.setattr(
        "app.services.publication_workflow.future_transaction_for_current_run",
        lambda db, groups, reference, accounts: FutureTransactionResult(
            status="Validated", target_horizon_months=12, feature_columns=[],
            predictions={name: "With No Future Sales" for name in accounts},
            model_version="catboost_stage8", artifact_hash="synthetic-test-hash",
        ),
    )


def record_coverage(db, batch_id):
    confirm_si_coverage(
        db, complete_through=REFERENCE, evidence_type="Client confirmation",
        evidence_reference="Synthetic SI check", evidence_basis="All synthetic rows reviewed",
        confirmed_on=date(2026, 1, 1), recorded_by=ACTOR, source_batch_id=batch_id,
    )
    db.commit()


def test_cli_publication_requires_independent_si_coverage(db, monkeypatch):
    session, _ = db
    allow_frozen_scoring(monkeypatch)
    with pytest.raises(ValueError, match="independently recorded SI complete-through"):
        publish(session, REFERENCE, ACTOR)
    session.rollback()
    assert session.scalar(select(func.count()).select_from(AnalyticsRun)) == 0


def test_cli_publication_monitors_and_audits_with_one_commit(db, monkeypatch):
    session, batch_id = db
    record_coverage(session, batch_id)
    allow_frozen_scoring(monkeypatch)
    seen = []
    def monitor(db, groups, as_of, complete_through, source_run_id):
        seen.append((complete_through, source_run_id))
        return {"matured": 0, "pending": 3, "study_outcome_status": "Pending",
                "review_recommended": False}
    monkeypatch.setattr("app.services.publication_workflow.monitor_registered_predictions", monitor)
    run = publish(session, REFERENCE, ACTOR)
    session.commit()
    assert run.status == "successful"
    assert run.model_version == "catboost_stage8"
    assert seen == [(REFERENCE, run.analysis_run_id)]
    assert latest_successful_run(session).analysis_run_id == run.analysis_run_id
    assert len(run_payload(session, run)["priorities"]) == 3
    audit = session.scalar(select(AuditLog).where(AuditLog.action == "analytics_run"))
    assert audit.details["source"] == "controlled_cli_publication"
    assert audit.details["monitoring_pending"] == 3


def test_cli_monitoring_failure_rolls_back_and_preserves_previous_run(db, monkeypatch):
    session, batch_id = db
    record_coverage(session, batch_id)
    allow_frozen_scoring(monkeypatch)
    monkeypatch.setattr(
        "app.services.publication_workflow.monitor_registered_predictions",
        lambda *args: {"matured": 0, "pending": 0, "study_outcome_status": "Pending",
                       "review_recommended": False},
    )
    previous = publish(session, REFERENCE, ACTOR)
    session.commit()
    previous_payload = run_payload(session, previous)
    def fail_monitoring(*args):
        raise RuntimeError("Synthetic monitoring failure")
    monkeypatch.setattr("app.services.publication_workflow.monitor_registered_predictions", fail_monitoring)
    with pytest.raises(RuntimeError, match="Synthetic monitoring failure"):
        publish(session, REFERENCE, ACTOR)
    session.rollback()
    assert session.scalar(select(func.count()).select_from(AnalyticsRun)) == 1
    assert latest_successful_run(session).analysis_run_id == previous.analysis_run_id
    assert run_payload(session, previous) == previous_payload
