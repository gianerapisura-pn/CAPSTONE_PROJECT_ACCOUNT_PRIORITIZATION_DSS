from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    AccountPriorityResult, AnalyticsRun, AuditLog, BusinessBaselineRecord, DimAccount,
    ImportBatch, ImportRowIssue, InvoiceGroupRecord, ModelRun, RFMResult, RankingBacktestRecord,
    RawSourceRow, SensitivityScenarioRecord, SensitivitySummaryRecord, SettlementResult,
)
from app.etl.invoices import InvoiceGroup


def audit(db: Session, actor: str | None, action: str, entity_type: str, entity_id: str | None, details: dict | None = None) -> None:
    db.add(AuditLog(actor_user_id=actor, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}))


def account_map(db: Session) -> dict[str, DimAccount]:
    return {item.standardized_account_name: item for item in db.scalars(select(DimAccount)).all()}


def ensure_accounts(db: Session, names: list[str]) -> dict[str, DimAccount]:
    existing = account_map(db)
    for name in sorted(set(names)):
        if name not in existing:
            item = DimAccount(standardized_account_name=name, display_name=name)
            db.add(item)
            db.flush()
            existing[name] = item
    return existing


def load_invoice_groups(db: Session) -> list[InvoiceGroup]:
    rows = db.scalars(select(InvoiceGroupRecord).join(ImportBatch, ImportBatch.import_batch_id == InvoiceGroupRecord.import_batch_id)
                      .where(ImportBatch.status == "committed")).all()
    return [InvoiceGroup(
        invoice_group_id=row.invoice_group_id,
        standardized_account_name=row.standardized_account_name,
        si_no=row.si_no,
        si_date=pd.Timestamp(row.si_date),
        si_amount=Decimal(str(row.si_amount)),
        payment_status=row.payment_status,
        final_cr_date=pd.Timestamp(row.final_cr_date) if row.final_cr_date else None,
        total_cr_amount=Decimal(str(row.total_cr_amount)),
        total_ewt=Decimal(str(row.total_ewt)),
        reconciliation_amount=Decimal(str(row.reconciliation_amount)),
        reconciliation_difference=Decimal(str(row.reconciliation_difference)),
        reconciled=row.reconciled,
        review_reason=row.review_reason,
        conflicting_invoice=row.conflicting_invoice,
    ) for row in rows]


def latest_successful_run(db: Session) -> AnalyticsRun | None:
    return db.scalar(select(AnalyticsRun).where(AnalyticsRun.status == "successful").order_by(desc(AnalyticsRun.completed_at)).limit(1))


def persist_run_output(db: Session, run: AnalyticsRun, result: dict) -> None:
    accounts = ensure_accounts(db, [row["account"] for row in result["rfm"]])
    for row in result["rfm"]:
        db.add(RFMResult(analysis_run_id=run.analysis_run_id, account_key=accounts[row["account"]].account_key, payload=row))
    for row in result["settlement"]:
        db.add(SettlementResult(analysis_run_id=run.analysis_run_id, account_key=accounts[row["account"]].account_key, payload=row))
    for row in result["priorities"]:
        db.add(AccountPriorityResult(
            analysis_run_id=run.analysis_run_id, account_key=accounts[row["account"]].account_key,
            standardized_account_name=row["account"], payload=row,
        ))
    cart = result.get("cart") or {}
    db.add(ModelRun(analysis_run_id=run.analysis_run_id, model_version=cart.get("model_version") or "unavailable",
                    status=cart.get("status", "unavailable"), payload=cart))
    for summary in result.get("sensitivity", []):
        scenarios = summary.get("scenarios", [])
        aggregate = {key: value for key, value in summary.items() if key != "scenarios"}
        db.add(SensitivitySummaryRecord(analysis_run_id=run.analysis_run_id, weight_range=summary["weight_range"], payload=aggregate))
        for scenario in scenarios:
            db.add(SensitivityScenarioRecord(
                analysis_run_id=run.analysis_run_id, weight_range=scenario["perturbation_level"],
                iteration=scenario["iteration"], account_key=accounts[scenario["account"]].account_key, payload=scenario,
            ))
    db.add(RankingBacktestRecord(analysis_run_id=run.analysis_run_id, payload=result.get("backtest", {})))
    for row in result.get("business_baselines", []):
        db.add(BusinessBaselineRecord(analysis_run_id=run.analysis_run_id, year=row["year"], payload=row))
    run.cutoff_date = pd.Timestamp(result["cutoff_date"]).date() if result.get("cutoff_date") else None
    run.status = result["status"]
    run.completed_at = datetime.now(timezone.utc)
    run.mcs_status = result.get("mcs_status", "unavailable")
    run.critic_weights = result.get("critic_weights", {})
    run.effective_config = result.get("effective_config", {})
    run.context_metrics = result.get("context_metrics", {})
    run.warnings = result.get("warnings", [])
    run.row_counts = {
        "logical_invoices": len(load_invoice_groups(db)),
        "rfm_results": len(result.get("rfm", [])),
        "settlement_results": len(result.get("settlement", [])),
    }
    run.eligible_account_counts = {
        "rfm": len(result.get("rfm", [])),
        "settlement": len(result.get("settlement", [])),
        "mcs": int(result.get("mcs_eligible_account_count", len(result.get("priorities", [])))),
    }
    run.model_version = result.get("cart", {}).get("model_version") or None
    run.predictive_status = result.get("cart", {}).get("status") or "model_unavailable"
    run.duration_seconds = (run.completed_at - run.started_at).total_seconds()


def serialize_run(run: AnalyticsRun) -> dict:
    return {
        "analysis_run_id": run.analysis_run_id, "cutoff_date": run.cutoff_date.isoformat() if run.cutoff_date else None,
        "started_at": run.started_at.isoformat(), "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "status": run.status, "mcs_status": run.mcs_status or "unavailable",
        "critic_weights": run.critic_weights or {}, "warnings": run.warnings or [],
        "duration_seconds": run.duration_seconds, "latest_import_batch_id": run.latest_import_batch_id,
        "row_counts": run.row_counts or {}, "eligible_account_counts": run.eligible_account_counts or {},
        "model_version": run.model_version, "predictive_status": run.predictive_status,
    }


def _logical_priority_payload(
    payload: dict,
    critic_weights: dict,
    settlement_record_count: int | None,
) -> dict:
    """Expose final logical aliases while keeping older stored payloads readable."""
    row = dict(payload)
    row.setdefault("frequency_count", row.get("frequency"))
    row.setdefault("monetary_value", row.get("monetary"))
    row.setdefault("average_settlement_days", row.get("settlement_days_avg"))
    row.setdefault("latest_valid_transaction_date", row.get("latest_valid_transaction"))
    row.setdefault("latest_valid_si_date", row.get("latest_valid_transaction_date"))
    row.setdefault("valid_settlement_record_count", settlement_record_count)
    row.setdefault("predicted_inactivity_risk", row.get("inactivity_risk"))
    row.setdefault("inactivity_risk", row.get("predicted_inactivity_risk"))
    for criterion in ("recency", "frequency", "monetary", "settlement"):
        row.setdefault(f"baseline_{criterion}_weight", critic_weights.get(criterion))
    return row


MCS_INELIGIBLE_REASON = (
    "No valid Historical Settlement Duration evidence known by the analysis cutoff."
)


def current_account_rows(db: Session, run: AnalyticsRun) -> list[dict]:
    """Build the current account universe from RFM, with optional MCS and CART evidence."""
    account_by_key = {
        item.account_key: item for item in db.scalars(select(DimAccount)).all()
    }
    rfm_records = db.scalars(
        select(RFMResult).where(RFMResult.analysis_run_id == run.analysis_run_id)
    ).all()
    settlement_by_key = {
        item.account_key: item.payload for item in db.scalars(
            select(SettlementResult).where(
                SettlementResult.analysis_run_id == run.analysis_run_id
            )
        ).all()
    }
    priority_by_key = {
        item.account_key: item.payload for item in db.scalars(
            select(AccountPriorityResult).where(
                AccountPriorityResult.analysis_run_id == run.analysis_run_id
            )
        ).all()
    }
    model = db.scalar(
        select(ModelRun).where(ModelRun.analysis_run_id == run.analysis_run_id)
    )
    cart = model.payload if model else {}
    predictions = cart.get("predictions") or {}
    model_version = cart.get("model_version") or (model.model_version if model else None)
    if model_version == "unavailable":
        model_version = None
    cutoff = run.cutoff_date
    rows: list[dict] = []
    for record in rfm_records:
        rfm = dict(record.payload)
        account_record = account_by_key.get(record.account_key)
        account = rfm.get("account") or (
            account_record.standardized_account_name if account_record else record.account_key
        )
        settlement = settlement_by_key.get(record.account_key) or {}
        settlement_count = int(settlement.get("settlement_invoice_count") or 0)
        settlement_average = settlement.get("average_settlement_days")
        stored_priority = priority_by_key.get(record.account_key)
        eligible = stored_priority is not None
        priority = (
            _logical_priority_payload(
                stored_priority, run.critic_weights or {}, settlement_count
            )
            if stored_priority
            else {}
        )
        latest_si = priority.get("latest_valid_si_date")
        if latest_si is None and cutoff is not None and rfm.get("recency_days") is not None:
            latest_si = (cutoff - timedelta(days=int(rfm["recency_days"]))).isoformat()
        row = {
            "account_key": record.account_key,
            "account": account,
            "analysis_run_id": run.analysis_run_id,
            "analysis_cutoff": cutoff.isoformat() if cutoff else None,
            "latest_valid_si_date": latest_si,
            "latest_valid_transaction_date": latest_si,
            "recency_days": rfm.get("recency_days"),
            "frequency": rfm.get("frequency"),
            "frequency_count": rfm.get("frequency"),
            "monetary": rfm.get("monetary"),
            "monetary_value": rfm.get("monetary"),
            "recency_score": rfm.get("recency_score"),
            "frequency_score": rfm.get("frequency_score"),
            "monetary_score": rfm.get("monetary_score"),
            "rfm_score": rfm.get("rfm_score"),
            "settlement_invoice_count": settlement_count,
            "valid_settlement_record_count": settlement_count,
            "average_settlement_days": settlement_average,
            "settlement_days_avg": settlement_average,
            "mcs_eligible": eligible,
            "mcs_eligibility_reason": (
                None if eligible else MCS_INELIGIBLE_REASON
                if settlement_average is None
                else "MCS ranking was unavailable because the current four-criterion run was non-discriminating."
            ),
            "predicted_inactivity_risk": predictions.get(account),
            "inactivity_risk": predictions.get(account),
            "model_version": model_version,
        }
        for field in (
            "normalized_recency", "normalized_frequency", "normalized_monetary",
            "normalized_settlement", "recency_contribution", "frequency_contribution",
            "monetary_contribution", "settlement_contribution", "final_priority_score",
            "priority_rank", "priority_group", "baseline_recency_weight",
            "baseline_frequency_weight", "baseline_monetary_weight",
            "baseline_settlement_weight",
        ):
            row[field] = priority.get(field)
        rows.append(row)
    rows.sort(key=lambda row: (
        row["priority_rank"] is None,
        row["priority_rank"] if row["priority_rank"] is not None else 0,
        row["account"].casefold(),
    ))
    return rows


def filter_current_account_rows(
    rows: list[dict],
    search: str = "",
    priority_group: str | None = None,
    predicted_inactivity_risk: str | None = None,
    eligibility: str | None = None,
) -> list[dict]:
    query = search.strip().casefold()
    filtered = [row for row in rows if not query or query in row["account"].casefold()]
    if priority_group:
        filtered = [row for row in filtered if row.get("priority_group") == priority_group]
    if predicted_inactivity_risk:
        filtered = [
            row for row in filtered
            if row.get("predicted_inactivity_risk") == predicted_inactivity_risk
        ]
    if eligibility == "ranked":
        filtered = [row for row in filtered if row.get("mcs_eligible")]
    elif eligibility == "not_ranked":
        filtered = [row for row in filtered if not row.get("mcs_eligible")]
    return filtered

def run_payload(db: Session, run: AnalyticsRun) -> dict:
    stored_priorities = [item.payload for item in db.scalars(select(AccountPriorityResult).where(AccountPriorityResult.analysis_run_id == run.analysis_run_id)).all()]
    rfm = [item.payload for item in db.scalars(select(RFMResult).where(RFMResult.analysis_run_id == run.analysis_run_id)).all()]
    settlement = [item.payload for item in db.scalars(select(SettlementResult).where(SettlementResult.analysis_run_id == run.analysis_run_id)).all()]
    settlement_counts = {
        row["account"]: int(row.get("settlement_invoice_count", 0)) for row in settlement
    }
    priorities = [
        _logical_priority_payload(
            row,
            run.critic_weights or {},
            settlement_counts.get(row["account"]),
        )
        for row in stored_priorities
    ]
    priorities.sort(key=lambda row: (row["priority_rank"], row["account"]))
    model = db.scalar(select(ModelRun).where(ModelRun.analysis_run_id == run.analysis_run_id))
    sensitivity = [item.payload for item in db.scalars(select(SensitivitySummaryRecord).where(SensitivitySummaryRecord.analysis_run_id == run.analysis_run_id)).all()]
    backtest = db.scalar(select(RankingBacktestRecord).where(RankingBacktestRecord.analysis_run_id == run.analysis_run_id))
    baselines = [item.payload for item in db.scalars(select(BusinessBaselineRecord).where(BusinessBaselineRecord.analysis_run_id == run.analysis_run_id).order_by(BusinessBaselineRecord.year)).all()]
    accounts = current_account_rows(db, run)
    return {**serialize_run(run), "accounts": accounts, "priorities": priorities, "rfm": rfm, "settlement": settlement,
            "cart": model.payload if model else {}, "sensitivity": sensitivity,
            "backtest": backtest.payload if backtest else {}, "business_baselines": baselines,
            "context_metrics": run.context_metrics or {}}
