from __future__ import annotations

from datetime import datetime, timezone
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
        "mcs": len(result.get("priorities", [])),
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


def run_payload(db: Session, run: AnalyticsRun) -> dict:
    priorities = [item.payload for item in db.scalars(select(AccountPriorityResult).where(AccountPriorityResult.analysis_run_id == run.analysis_run_id)).all()]
    priorities.sort(key=lambda row: (row["priority_rank"], row["account"]))
    rfm = [item.payload for item in db.scalars(select(RFMResult).where(RFMResult.analysis_run_id == run.analysis_run_id)).all()]
    settlement = [item.payload for item in db.scalars(select(SettlementResult).where(SettlementResult.analysis_run_id == run.analysis_run_id)).all()]
    model = db.scalar(select(ModelRun).where(ModelRun.analysis_run_id == run.analysis_run_id))
    sensitivity = [item.payload for item in db.scalars(select(SensitivitySummaryRecord).where(SensitivitySummaryRecord.analysis_run_id == run.analysis_run_id)).all()]
    backtest = db.scalar(select(RankingBacktestRecord).where(RankingBacktestRecord.analysis_run_id == run.analysis_run_id))
    baselines = [item.payload for item in db.scalars(select(BusinessBaselineRecord).where(BusinessBaselineRecord.analysis_run_id == run.analysis_run_id).order_by(BusinessBaselineRecord.year)).all()]
    return {**serialize_run(run), "priorities": priorities, "rfm": rfm, "settlement": settlement,
            "cart": model.payload if model else {}, "sensitivity": sensitivity,
            "backtest": backtest.payload if backtest else {}, "business_baselines": baselines,
            "context_metrics": run.context_metrics or {}}
