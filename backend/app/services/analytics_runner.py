from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.predictive.cart import CartResult
from app.analytics.prescriptive.scoring import compute_priorities
from app.analytics.validation.backtest import run_historical_backtest
from app.analytics.validation.baselines import (
    annual_business_baselines,
    selected_horizon_no_transaction_rate,
)
from app.analytics.validation.sensitivity import run_sensitivity
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.etl.invoices import InvoiceGroup


@dataclass(frozen=True)
class AnalyticsRunResult:
    analysis_run_id: str
    cutoff_date: str | None
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
    cart: dict
    backtest: dict
    business_baselines: list[dict]
    context_metrics: dict
    warnings: list[str]
    effective_config: dict


def unavailable_cart(config: AnalyticsConfig) -> CartResult:
    return CartResult(
        status="model_unavailable",
        outcome_window_months=0,
        feature_columns=[],
        report={},
        predictions={},
        lookback_months=config.predictive_lookback_months,
        development_periods=list(config.cart_development_cutoffs),
        oop_period=config.cart_oop_cutoff,
    )


def run_account_prioritization(
    invoice_groups: list[InvoiceGroup],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
    cart_result: CartResult | None = None,
) -> AnalyticsRunResult:
    started = datetime.now(timezone.utc)
    eligible_dates = [group.si_date for group in invoice_groups if group.rfm_eligible]
    warnings: list[str] = []
    cutoff = max(eligible_dates) if eligible_dates else None
    rfm = compute_rfm(invoice_groups, cutoff_date=cutoff) if cutoff is not None else []
    settlement = compute_settlement_metrics(invoice_groups, cutoff_date=cutoff) if cutoff is not None else []
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
            "The four MCS criteria contain zero total CRITIC information; no official ranking or Priority Groups were produced."
        )
    else:
        mcs_status = "no_eligible_accounts"
        warnings.append("No accounts had all four defensible MCS criteria.")
    if not eligible_dates:
        warnings.append("No valid Sales Invoice activity was available for descriptive RFM.")

    sensitivity = [
        asdict(
            run_sensitivity(
                priorities,
                weights,
                weight_range,
                config.sensitivity_iterations,
                config.random_seed,
            )
        )
        for weight_range in config.sensitivity_ranges
    ] if priorities else []

    cart = cart_result or unavailable_cart(config)
    backtest = run_historical_backtest(
        invoice_groups,
        config=config,
        repetitions=config.random_baseline_repetitions,
        random_seed=config.random_seed,
    )
    context_metrics = {
        "selected_horizon_no_transaction_rate": selected_horizon_no_transaction_rate(
            invoice_groups, cart.outcome_window_months, config
        )
    }

    rfm_by_account = {item.account: item for item in rfm}
    settlement_by_account = {item.account: item for item in settlement}
    priority_rows: list[dict] = []
    for item in priorities:
        metric = rfm_by_account[item.account]
        settlement_metric = settlement_by_account[item.account]
        latest_transaction = (
            cutoff - pd.Timedelta(days=metric.recency_days)
        ).date().isoformat() if cutoff is not None else None
        predicted_risk = cart.predictions.get(item.account)
        row = asdict(item)
        row["monetary"] = float(item.monetary)
        row.update({
            "latest_valid_transaction": latest_transaction,
            "latest_valid_transaction_date": latest_transaction,
            "frequency_count": item.frequency,
            "monetary_value": float(item.monetary),
            "average_settlement_days": item.settlement_days_avg,
            "valid_settlement_record_count": settlement_metric.settlement_invoice_count,
            "baseline_recency_weight": weights.get("recency"),
            "baseline_frequency_weight": weights.get("frequency"),
            "baseline_monetary_weight": weights.get("monetary"),
            "baseline_settlement_weight": weights.get("settlement"),
            "recency_score": metric.recency_score,
            "frequency_score": metric.frequency_score,
            "monetary_score": metric.monetary_score,
            "predicted_inactivity_risk": predicted_risk,
            "inactivity_risk": predicted_risk,
            "model_version": cart.model_version or None,
        })
        priority_rows.append(row)

    completed = datetime.now(timezone.utc)
    return AnalyticsRunResult(
        analysis_run_id=str(uuid4()),
        cutoff_date=pd.Timestamp(cutoff).date().isoformat() if cutoff is not None else None,
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
        cart=asdict(cart),
        backtest=asdict(backtest),
        business_baselines=annual_business_baselines(invoice_groups),
        context_metrics=context_metrics,
        warnings=warnings,
        effective_config=config.serializable(),
    )
