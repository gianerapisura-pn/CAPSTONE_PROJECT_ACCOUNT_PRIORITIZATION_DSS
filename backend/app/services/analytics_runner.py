from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.predictive.cart import CartResult, run_cart_analysis
from app.analytics.prescriptive.scoring import compute_priorities
from app.analytics.validation.backtest import run_historical_backtest
from app.analytics.validation.baselines import annual_business_baselines
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
    critic_weights: dict[str, float]
    rfm: list[dict]
    settlement: list[dict]
    priorities: list[dict]
    sensitivity: list[dict]
    cart: dict
    backtest: dict
    business_baselines: list[dict]
    warnings: list[str]
    effective_config: dict


def run_account_prioritization(
    invoice_groups: list[InvoiceGroup],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
    cart_result: CartResult | None = None,
) -> AnalyticsRunResult:
    started = datetime.now(timezone.utc)
    eligible_dates = [group.si_date for group in invoice_groups if group.rfm_eligible]
    warnings: list[str] = []
    if not eligible_dates:
        return AnalyticsRunResult(
            analysis_run_id=str(uuid4()),
            cutoff_date=None,
            started_at=started.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            status="no_mcs_eligible_accounts",
            critic_weights={},
            rfm=[],
            settlement=[],
            priorities=[],
            sensitivity=[],
            cart={},
            backtest={},
            business_baselines=[],
            warnings=["No MCS-eligible accounts were found."],
            effective_config=config.serializable(),
        )
    cutoff = max(eligible_dates)
    rfm = compute_rfm(invoice_groups, cutoff_date=cutoff)
    # Current runs may use all collection evidence already present at execution.
    # Historical model/backtest slices pass an explicit cutoff separately.
    settlement = compute_settlement_metrics(invoice_groups)
    priorities, weights = compute_priorities(rfm, settlement)
    if not priorities:
        warnings.append("No accounts had both RFM and eligible settlement metrics.")
    sensitivity = [
        asdict(run_sensitivity(priorities, weights, weight_range, config.sensitivity_iterations, config.random_seed + index))
        for index, weight_range in enumerate(config.sensitivity_ranges)
    ] if priorities else []
    cart = cart_result or run_cart_analysis(invoice_groups, config)
    if isinstance(cart, tuple):
        cart = cart[0]
    backtest = run_historical_backtest(
        invoice_groups,
        repetitions=config.random_baseline_repetitions,
        random_seed=config.random_seed,
    )
    rfm_by_account = {item.account: item for item in rfm}
    priority_rows: list[dict] = []
    for item in priorities:
        metric = rfm_by_account[item.account]
        row = asdict(item)
        row.update({
            "latest_valid_transaction": (cutoff - pd.Timedelta(days=metric.recency_days)).date().isoformat(),
            "recency_days": metric.recency_days,
            "frequency": metric.frequency,
            "monetary": float(metric.monetary),
            "recency_score": metric.recency_score,
            "frequency_score": metric.frequency_score,
            "monetary_score": metric.monetary_score,
            "inactivity_risk": cart.predictions.get(item.account),
            "model_version": cart.model_version,
        })
        priority_rows.append(row)
    completed = datetime.now(timezone.utc)
    return AnalyticsRunResult(
        analysis_run_id=str(uuid4()),
        cutoff_date=pd.Timestamp(cutoff).date().isoformat(),
        started_at=started.isoformat(),
        completed_at=completed.isoformat(),
        status="successful",
        critic_weights=weights,
        rfm=[{**asdict(item), "monetary": float(item.monetary)} for item in rfm],
        settlement=[asdict(item) for item in settlement],
        priorities=priority_rows,
        sensitivity=sensitivity,
        cart=asdict(cart),
        backtest=asdict(backtest),
        business_baselines=annual_business_baselines(invoice_groups),
        warnings=warnings,
        effective_config=config.serializable(),
    )
