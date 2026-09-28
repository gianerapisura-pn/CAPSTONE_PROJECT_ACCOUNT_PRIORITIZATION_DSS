from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.predictive.future_transaction import FutureTransactionResult
from app.analytics.prescriptive.scoring import compute_priorities
from app.analytics.validation.backtest import run_historical_backtest
from app.analytics.validation.baselines import annual_business_baselines
from app.analytics.validation.sensitivity import (
    run_leave_one_out_influence,
    run_sensitivity_suite,
)
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.etl.invoices import InvoiceGroup
from app.services.model_lifecycle import unavailable_prediction


@dataclass(frozen=True)
class AnalyticsRunResult:
    analysis_run_id: str
    analysis_reference_date: str
    latest_valid_si_date: str | None
    latest_final_cr_date: str | None
    started_at: str
    completed_at: str
    status: str
    mcs_status: str
    mcs_eligible_account_count: int
    critic_weights: dict[str, float]
    rfm: list[dict]
    settlement: list[dict]
    priorities: list[dict]
    sensitivity: list[dict]
    critic_influence: list[dict]
    predictive: dict
    backtest: dict
    business_baselines: list[dict]
    context_metrics: dict
    warnings: list[str]
    effective_config: dict


def validate_analysis_reference(
    invoice_groups: list[InvoiceGroup],
    analysis_reference_date: pd.Timestamp,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    valid = [group for group in invoice_groups if group.rfm_eligible]
    latest_si = max((group.si_date for group in valid), default=None)
    latest_cr = max(
        (group.final_cr_date for group in valid if group.final_cr_date is not None),
        default=None,
    )
    reference = pd.Timestamp(analysis_reference_date)
    latest_evidence = max(
        (value for value in (latest_si, latest_cr) if value is not None),
        default=None,
    )
    if latest_evidence is not None and reference < latest_evidence:
        raise ValueError(
            "Analysis reference date cannot precede the latest accepted SI or final CR evidence."
        )
    return latest_si, latest_cr


def run_account_prioritization(
    invoice_groups: list[InvoiceGroup],
    analysis_reference_date: pd.Timestamp,
    eligible_accounts: set[str],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
    predictive_result: FutureTransactionResult | None = None,
) -> AnalyticsRunResult:
    started = datetime.now(timezone.utc)
    reference = pd.Timestamp(analysis_reference_date)
    latest_si, latest_cr = validate_analysis_reference(invoice_groups, reference)
    analytical_groups = [
        group for group in invoice_groups
        if group.standardized_account_name in eligible_accounts
    ]
    warnings: list[str] = []
    rfm = compute_rfm(analytical_groups, reference, eligible_accounts)
    settlement = compute_settlement_metrics(analytical_groups, cutoff_date=reference)
    priorities, weights = compute_priorities(rfm, settlement)
    eligible_mcs_accounts = {
        item.account for item in rfm
    } & {
        item.account for item in settlement if item.average_settlement_days is not None
    }
    if priorities:
        mcs_status = "ranked"
    elif eligible_mcs_accounts:
        mcs_status = "non_discriminating"
        warnings.append(
            "The four MCS criteria contain zero total CRITIC information; no ranking was produced."
        )
    else:
        mcs_status = "no_eligible_accounts"
        warnings.append(
            "No verified B2B accounts had all four defensible MCS criteria."
        )
    sensitivity = [
        asdict(summary) for summary in run_sensitivity_suite(
            priorities,
            weights,
            config.sensitivity_ranges,
            config.sensitivity_iterations,
            config.random_seed,
        )
    ] if priorities else []
    influence = run_leave_one_out_influence(rfm, settlement, priorities, weights) if priorities else []
    predictive = predictive_result or unavailable_prediction(config)
    rfm_by_account = {item.account: item for item in rfm}
    settlement_by_account = {item.account: item for item in settlement}
    priority_rows: list[dict] = []
    for item in priorities:
        metric = rfm_by_account[item.account]
        settlement_metric = settlement_by_account[item.account]
        latest_transaction = (
            reference - pd.Timedelta(days=metric.recency_days)
        ).date().isoformat()
        row = asdict(item)
        row["monetary"] = float(item.monetary)
        row.update({
            "latest_valid_si_date": latest_transaction,
            "frequency_count": item.frequency,
            "monetary_value": float(item.monetary),
            "average_settlement_days": item.settlement_days_avg,
            "valid_settlement_record_count": settlement_metric.settlement_invoice_count,
            "baseline_recency_weight": weights.get("recency"),
            "baseline_frequency_weight": weights.get("frequency"),
            "baseline_monetary_weight": weights.get("monetary"),
            "baseline_settlement_weight": weights.get("settlement"),
            "r_score": metric.r_score,
            "f_score": metric.f_score,
            "m_score": metric.m_score,
            "rfm_code": metric.rfm_code,
            "rfm_mean_score": metric.rfm_mean_score,
            "predicted_future_transaction_class": predictive.predictions.get(item.account),
            "model_version": predictive.model_version or None,
        })
        priority_rows.append(row)
    if predictive.status != "Validated":
        warnings.append(
            "Future Transaction prediction is unavailable because the genuine frozen "
            "Extra Trees artifact is not registered and validated."
        )
    completed = datetime.now(timezone.utc)
    return AnalyticsRunResult(
        analysis_run_id=str(uuid4()),
        analysis_reference_date=reference.date().isoformat(),
        latest_valid_si_date=latest_si.date().isoformat() if latest_si is not None else None,
        latest_final_cr_date=latest_cr.date().isoformat() if latest_cr is not None else None,
        started_at=started.isoformat(),
        completed_at=completed.isoformat(),
        status="successful",
        mcs_status=mcs_status,
        mcs_eligible_account_count=len(eligible_mcs_accounts),
        critic_weights=weights,
        rfm=[{**asdict(item), "monetary": float(item.monetary)} for item in rfm],
        settlement=[asdict(item) for item in settlement],
        priorities=priority_rows,
        sensitivity=sensitivity,
        critic_influence=influence,
        predictive=asdict(predictive),
        backtest=asdict(run_historical_backtest(
            analytical_groups, config=config, eligible_accounts=eligible_accounts,
        )),
        business_baselines=annual_business_baselines(
            invoice_groups, reference, eligible_accounts,
        ),
        context_metrics={
            "historical_account_count": len({
                group.standardized_account_name
                for group in invoice_groups if group.rfm_eligible
            }),
            "verified_b2b_account_count": len(rfm),
            "prediction_class_counts": {
                label: sum(value == label for value in predictive.predictions.values())
                for label in ("Future Transaction", "No Future Transaction")
            },
        },
        warnings=warnings,
        effective_config=config.serializable(),
    )