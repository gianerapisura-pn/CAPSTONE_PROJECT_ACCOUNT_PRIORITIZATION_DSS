from dataclasses import asdict
from decimal import Decimal
import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.models import (
    AccountContextSnapshot, AnalyticsRun, Base, DimAccount, FutureTransactionPrediction, InvoiceGroupRecord,
    RFMResult, SettlementResult,
)
from app.db.repository import (
    current_account_rows, filter_current_account_rows, latest_successful_run,
    load_invoice_groups, persist_run_output, run_payload, serialize_run,
)
from app.etl.invoices import InvoiceGroup
from app.services.analytics_runner import run_account_prioritization
from app.analytics.predictive.future_transaction import FutureTransactionResult


def group(i):
    return InvoiceGroup(
        invoice_group_id=str(i), standardized_account_name=f"A{i}", si_no=str(i),
        si_date=pd.Timestamp("2025-01-01") + pd.Timedelta(days=i * 10),
        si_amount=Decimal(100 + i * 25), payment_status="Fully Paid",
        final_cr_date=pd.Timestamp("2025-01-10") + pd.Timedelta(days=i * 12),
        total_cr_amount=Decimal(100 + i * 25),
        reconciliation_amount=Decimal(100 + i * 25),
        reconciliation_difference=Decimal("0"), reconciled=True)


def test_final_run_persistence_and_public_contract():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        groups = [group(i) for i in range(1, 9)]
        for item in groups:
            db.add(DimAccount(
                standardized_account_name=item.standardized_account_name,
                display_name=item.standardized_account_name,
                entity_type="Business", business_category="Corporate",
                b2b_priority_eligible=True, account_status="Client-Confirmed Active"))
        db.flush()
        predictions = {item.standardized_account_name: "No Future Transaction"
                       for item in groups}
        predictive = FutureTransactionResult(
            status="Validated", target_horizon_months=12, feature_columns=[],
            predictions=predictions, model_version="extra_trees_stage8",
            artifact_hash="hash", analysis_reference_date="2026-09-21",
            monitoring_status="Pending outcome maturity")
        result = asdict(run_account_prioritization(
            groups, pd.Timestamp("2026-09-21"), set(predictions),
            predictive_result=predictive))
        run = AnalyticsRun(status="running")
        db.add(run); db.flush()
        persist_run_output(db, run, result)
        db.commit()
        latest = latest_successful_run(db)
        assert latest.analysis_reference_date.isoformat() == "2026-09-21"
        payload = run_payload(db, latest)
        assert "predictive" in payload and "cart" not in payload
        assert payload["predictive"]["model_version"] == "extra_trees_stage8"
        snapshotted = db.scalars(select(DimAccount)).first()
        snapshotted.entity_type = "Property/Building"
        snapshotted.account_status = "Client-Confirmed Closed"
        db.commit()
        rows = current_account_rows(db, latest)
        assert rows[0]["entity_type"] == "Business"
        assert rows[0]["account_status"] == "Client-Confirmed Active"
        assert rows[0]["current_actionable"] is True
        assert all(x["b2b_priority_eligible"] for x in rows)
        assert {x["predicted_future_transaction_class"] for x in rows} == {
            "No Future Transaction"}
        assert all("predicted_inactivity_risk" not in x for x in rows)
        assert db.scalar(select(FutureTransactionPrediction)) is not None
        assert serialize_run(latest)["analysis_reference_date"] == "2026-09-21"


def test_filters_do_not_rerank_or_mutate_scores():
    rows = [
        {"account": "A", "priority_group": "High", "priority_rank": 1,
         "final_priority_score": .9, "mcs_eligible": True, "is_ranked": True,
         "predicted_future_transaction_class": "Future Transaction"},
        {"account": "B", "priority_group": "Low", "priority_rank": 2,
         "final_priority_score": .4, "mcs_eligible": True, "is_ranked": True,
         "predicted_future_transaction_class": "No Future Transaction"},
    ]
    filtered = filter_current_account_rows(
        rows, predicted_future_transaction_class="No Future Transaction")
    assert filtered == [rows[1]]
    assert rows[1]["priority_rank"] == 2

def test_load_invoice_groups_recomputes_derived_properties():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(InvoiceGroupRecord(
            invoice_group_id="persisted-1", import_batch_id="00000000-0000-4000-8000-000000000099",
            standardized_account_name="Verified Account", si_no="SI-1",
            si_date=pd.Timestamp("2026-01-01").date(), si_amount=Decimal("1000"),
            payment_status="Fully Paid", final_cr_date=pd.Timestamp("2026-01-11").date(),
            total_cr_amount=Decimal("980"), total_ewt=Decimal("20"),
            reconciliation_amount=Decimal("1000"), reconciliation_difference=Decimal("0"),
            reconciled=True, is_cancelled=False, conflicting_invoice=False,
            rfm_eligible=True, settlement_eligible=True, settlement_days=10,
        ))
        db.commit()
        loaded = load_invoice_groups(db)
        assert len(loaded) == 1
        assert loaded[0].rfm_eligible is True
        assert loaded[0].settlement_eligible is True
        assert loaded[0].settlement_days == 10

def test_mcs_eligibility_is_distinct_from_non_discriminating_rank_status():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        account = DimAccount(
            standardized_account_name="A", display_name="A",
            b2b_priority_eligible=True,
        )
        run = AnalyticsRun(status="successful", mcs_status="non_discriminating",
                           analysis_reference_date=pd.Timestamp("2026-09-21").date())
        db.add_all([account, run])
        db.flush()
        db.add(AccountContextSnapshot(
            analysis_run_id=run.analysis_run_id,
            account_key=account.account_key,
            standardized_account_name="A",
            b2b_priority_eligible=True,
            account_status="Client-Confirmed Active",
            current_actionable=True,
        ))
        db.add(RFMResult(
            analysis_run_id=run.analysis_run_id,
            account_key=account.account_key,
            payload={
                "account": "A", "recency_days": 1, "frequency": 1, "monetary": 100,
                "r_score": 3, "f_score": 3, "m_score": 3,
                "rfm_code": "333", "rfm_mean_score": 3,
            },
        ))
        db.add(SettlementResult(
            analysis_run_id=run.analysis_run_id,
            account_key=account.account_key,
            payload={
                "account": "A", "settlement_invoice_count": 1,
                "average_settlement_days": 10,
            },
        ))
        db.commit()
        row = current_account_rows(db, run)[0]
        assert row["mcs_eligible"] is True
        assert row["mcs_eligibility_reason"] is None
        assert row["is_ranked"] is False
        assert row["ranking_status"] == "not_ranked"
        assert "non-discriminating" in row["ranking_unavailable_reason"]
        assert filter_current_account_rows([row], eligibility="not_ranked") == [row]
