from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.db.models import (
    AccountPriorityResult, AnalyticsRun, AuditLog, BusinessBaselineRecord,
    CriticInfluenceRecord, DimAccount, FutureTransactionPrediction,
    InvoiceGroupRecord, ModelRun, RFMResult, RankingBacktestRecord,
    SensitivityScenarioRecord, SensitivitySummaryRecord, SettlementResult,
)
from app.etl.invoices import InvoiceGroup


def audit(db, actor, action, entity_type, entity_id, details=None):
    db.add(AuditLog(actor_user_id=actor, action=action, entity_type=entity_type,
                    entity_id=entity_id, details=details or {}))


def account_map(db):
    return {x.standardized_account_name: x for x in db.scalars(select(DimAccount)).all()}


def ensure_accounts(db, names):
    result = account_map(db)
    for name in sorted(set(names)):
        if name not in result:
            result[name] = DimAccount(standardized_account_name=name, display_name=name,
                                      b2b_priority_eligible=False)
            db.add(result[name])
            db.flush()
    return result


def eligible_b2b_accounts(db):
    return set(db.scalars(select(DimAccount.standardized_account_name).where(
        DimAccount.b2b_priority_eligible.is_(True))).all())


def load_invoice_groups(db):
    # This table is the cumulative current materialization. Import lineage lives separately.
    return [InvoiceGroup(
        invoice_group_id=x.invoice_group_id,
        standardized_account_name=x.standardized_account_name,
        si_no=x.si_no, si_date=pd.Timestamp(x.si_date), si_amount=Decimal(str(x.si_amount)),
        payment_status=x.payment_status,
        final_cr_date=pd.Timestamp(x.final_cr_date) if x.final_cr_date else None,
        total_cr_amount=Decimal(str(x.total_cr_amount)),
        total_ewt=Decimal(str(x.total_ewt)),
        reconciliation_amount=Decimal(str(x.reconciliation_amount)),
        reconciliation_difference=Decimal(str(x.reconciliation_difference)),
        reconciled=x.reconciled, review_reason=x.review_reason,
        conflicting_invoice=x.conflicting_invoice, rows=[],
    ) for x in db.scalars(select(InvoiceGroupRecord)).all()]


def latest_successful_run(db):
    return db.scalar(select(AnalyticsRun).where(AnalyticsRun.status == "successful")
                     .order_by(desc(AnalyticsRun.completed_at)).limit(1))


def persist_run_output(db, run, result):
    accounts = ensure_accounts(db, [x["account"] for x in result.get("rfm", [])])
    for row in result.get("rfm", []):
        db.add(RFMResult(analysis_run_id=run.analysis_run_id,
                         account_key=accounts[row["account"]].account_key, payload=row))
    for row in result.get("settlement", []):
        db.add(SettlementResult(analysis_run_id=run.analysis_run_id,
                                account_key=accounts[row["account"]].account_key, payload=row))
    for row in result.get("priorities", []):
        db.add(AccountPriorityResult(
            analysis_run_id=run.analysis_run_id,
            account_key=accounts[row["account"]].account_key,
            standardized_account_name=row["account"], payload=row))
    predictive = result.get("predictive") or {}
    db.add(ModelRun(analysis_run_id=run.analysis_run_id,
                    model_version=predictive.get("model_version") or "unavailable",
                    status=predictive.get("status", "model_unavailable"),
                    payload=predictive))
    reference = pd.Timestamp(result["analysis_reference_date"])
    for account, label in (predictive.get("predictions") or {}).items():
        if account in accounts:
            db.add(FutureTransactionPrediction(
                analysis_run_id=run.analysis_run_id,
                account_key=accounts[account].account_key,
                model_version=predictive.get("model_version") or "unavailable",
                cutoff_date=reference.date(),
                future_window_end=(reference + pd.DateOffset(months=12)).date(),
                predicted_class=label, monitoring_status="Pending outcome maturity"))
    for summary in result.get("sensitivity", []):
        scenarios = summary.get("scenarios", [])
        db.add(SensitivitySummaryRecord(
            analysis_run_id=run.analysis_run_id,
            weight_range=summary["weight_range"],
            payload={k: v for k, v in summary.items() if k != "scenarios"}))
        for row in scenarios:
            db.add(SensitivityScenarioRecord(
                analysis_run_id=run.analysis_run_id,
                weight_range=row["perturbation_level"], iteration=row["iteration"],
                account_key=accounts[row["account"]].account_key, payload=row))
    for row in result.get("critic_influence", []):
        db.add(CriticInfluenceRecord(
            analysis_run_id=run.analysis_run_id,
            removed_account_key=accounts[row["removed_account"]].account_key, payload=row))
    db.add(RankingBacktestRecord(analysis_run_id=run.analysis_run_id,
                                 payload=result.get("backtest", {})))
    for row in result.get("business_baselines", []):
        db.add(BusinessBaselineRecord(analysis_run_id=run.analysis_run_id,
                                      year=row["year"], payload=row))
    run.analysis_reference_date = reference.date()
    run.cutoff_date = reference.date()  # legacy physical column only
    run.latest_valid_si_date = (pd.Timestamp(result["latest_valid_si_date"]).date()
                                if result.get("latest_valid_si_date") else None)
    run.latest_final_cr_date = (pd.Timestamp(result["latest_final_cr_date"]).date()
                                if result.get("latest_final_cr_date") else None)
    run.methodology_version = result.get("effective_config", {}).get("version")
    run.status = result["status"]
    run.completed_at = datetime.now(timezone.utc)
    run.mcs_status = result.get("mcs_status", "unavailable")
    run.critic_weights = result.get("critic_weights", {})
    run.effective_config = result.get("effective_config", {})
    run.context_metrics = result.get("context_metrics", {})
    run.warnings = result.get("warnings", [])
    run.row_counts = {"logical_invoices": len(load_invoice_groups(db)),
                      "rfm_results": len(result.get("rfm", [])),
                      "settlement_results": len(result.get("settlement", []))}
    run.eligible_account_counts = {
        "verified_b2b": len(result.get("rfm", [])),
        "mcs": int(result.get("mcs_eligible_account_count", 0))}
    run.model_version = predictive.get("model_version") or None
    run.predictive_status = predictive.get("status") or "model_unavailable"
    run.duration_seconds = (run.completed_at - run.started_at).total_seconds()


def serialize_run(run):
    reference = run.analysis_reference_date or run.cutoff_date
    return {
        "analysis_run_id": run.analysis_run_id,
        "analysis_reference_date": reference.isoformat() if reference else None,
        "latest_valid_si_date": run.latest_valid_si_date.isoformat() if run.latest_valid_si_date else None,
        "latest_final_cr_date": run.latest_final_cr_date.isoformat() if run.latest_final_cr_date else None,
        "methodology_version": run.methodology_version,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "status": run.status, "mcs_status": run.mcs_status or "unavailable",
        "critic_weights": run.critic_weights or {}, "warnings": run.warnings or [],
        "duration_seconds": run.duration_seconds,
        "latest_import_batch_id": run.latest_import_batch_id,
        "row_counts": run.row_counts or {},
        "eligible_account_counts": run.eligible_account_counts or {},
        "model_version": run.model_version, "predictive_status": run.predictive_status,
    }


MCS_INELIGIBLE_REASON = "No valid settlement-duration evidence was available by the analysis reference date."


def current_account_rows(db, run):
    account_by_key = {x.account_key: x for x in db.scalars(select(DimAccount)).all()}
    rfm_rows = db.scalars(select(RFMResult).where(
        RFMResult.analysis_run_id == run.analysis_run_id)).all()
    settlement = {x.account_key: x.payload for x in db.scalars(
        select(SettlementResult).where(SettlementResult.analysis_run_id == run.analysis_run_id)).all()}
    priorities = {x.account_key: x.payload for x in db.scalars(
        select(AccountPriorityResult).where(
            AccountPriorityResult.analysis_run_id == run.analysis_run_id)).all()}
    model = db.scalar(select(ModelRun).where(ModelRun.analysis_run_id == run.analysis_run_id))
    predictive = model.payload if model else {}
    predictions = predictive.get("predictions") or {}
    reference = run.analysis_reference_date or run.cutoff_date
    result = []
    for record in rfm_rows:
        rfm, account = dict(record.payload), account_by_key[record.account_key]
        settled, priority = settlement.get(record.account_key, {}), priorities.get(record.account_key, {})
        latest = ((reference - timedelta(days=int(rfm["recency_days"]))).isoformat()
                  if reference is not None else None)
        row = {
            "account_key": record.account_key, "account": account.standardized_account_name,
            "display_name": account.display_name, "entity_type": account.entity_type,
            "business_category": account.business_category,
            "primary_business_type": account.primary_business_type,
            "b2b_priority_eligible": account.b2b_priority_eligible,
            "account_status": account.account_status,
            "last_verified": account.last_verified.isoformat() if account.last_verified else None,
            "analysis_run_id": run.analysis_run_id,
            "analysis_reference_date": reference.isoformat() if reference else None,
            "latest_valid_si_date": latest, "recency_days": rfm.get("recency_days"),
            "frequency": rfm.get("frequency"), "frequency_count": rfm.get("frequency"),
            "monetary": rfm.get("monetary"), "monetary_value": rfm.get("monetary"),
            "r_score": rfm.get("r_score"), "f_score": rfm.get("f_score"),
            "m_score": rfm.get("m_score"), "rfm_code": rfm.get("rfm_code"),
            "rfm_mean_score": rfm.get("rfm_mean_score"),
            "settlement_invoice_count": int(settled.get("settlement_invoice_count") or 0),
            "valid_settlement_record_count": int(settled.get("settlement_invoice_count") or 0),
            "average_settlement_days": settled.get("average_settlement_days"),
            "settlement_days_avg": settled.get("average_settlement_days"),
            "mcs_eligible": bool(priority),
            "mcs_eligibility_reason": None if priority else MCS_INELIGIBLE_REASON,
            "predicted_future_transaction_class": predictions.get(account.standardized_account_name),
            "model_version": predictive.get("model_version") if predictions.get(account.standardized_account_name) else None,
        }
        for field in ("normalized_recency", "normalized_frequency", "normalized_monetary",
                      "normalized_settlement", "recency_contribution", "frequency_contribution",
                      "monetary_contribution", "settlement_contribution", "final_priority_score",
                      "priority_rank", "priority_group", "baseline_recency_weight",
                      "baseline_frequency_weight", "baseline_monetary_weight",
                      "baseline_settlement_weight"):
            row[field] = priority.get(field)
        result.append(row)
    return sorted(result, key=lambda x: (x["priority_rank"] is None,
                  x["priority_rank"] or 0, x["account"].casefold()))


def filter_current_account_rows(rows, search="", priority_group=None,
                                predicted_future_transaction_class=None, eligibility=None):
    query = search.strip().casefold()
    rows = [x for x in rows if not query or query in x["account"].casefold()]
    if priority_group:
        rows = [x for x in rows if x.get("priority_group") == priority_group]
    if predicted_future_transaction_class:
        rows = [x for x in rows if x.get("predicted_future_transaction_class") ==
                predicted_future_transaction_class]
    if eligibility == "ranked":
        rows = [x for x in rows if x.get("mcs_eligible")]
    elif eligibility == "not_ranked":
        rows = [x for x in rows if not x.get("mcs_eligible")]
    return rows


def run_payload(db, run):
    def payloads(model):
        return [x.payload for x in db.scalars(select(model).where(
            model.analysis_run_id == run.analysis_run_id)).all()]
    priorities = sorted(payloads(AccountPriorityResult),
                        key=lambda x: (x["priority_rank"], x["account"]))
    model = db.scalar(select(ModelRun).where(ModelRun.analysis_run_id == run.analysis_run_id))
    backtest = db.scalar(select(RankingBacktestRecord).where(
        RankingBacktestRecord.analysis_run_id == run.analysis_run_id))
    baselines = [x.payload for x in db.scalars(select(BusinessBaselineRecord).where(
        BusinessBaselineRecord.analysis_run_id == run.analysis_run_id)
        .order_by(BusinessBaselineRecord.year)).all()]
    return {**serialize_run(run), "accounts": current_account_rows(db, run),
            "priorities": priorities, "rfm": payloads(RFMResult),
            "settlement": payloads(SettlementResult),
            "predictive": model.payload if model else {},
            "sensitivity": payloads(SensitivitySummaryRecord),
            "critic_influence": payloads(CriticInfluenceRecord),
            "backtest": backtest.payload if backtest else {},
            "business_baselines": baselines, "context_metrics": run.context_metrics or {}}
