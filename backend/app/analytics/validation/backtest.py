from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

import numpy as np
import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.prescriptive.scoring import AccountPriority, compute_priorities
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.etl.invoices import InvoiceGroup


@dataclass(frozen=True)
class BacktestCutoffResult:
    cutoff_date: str
    evaluation_end_date: str
    top_decile_capture: float | None
    expected_random_capture: float | None
    lift_over_expected_random: float | None
    eligible_account_count: int
    selected_account_count: int


@dataclass(frozen=True)
class HistoricalBacktestSummary:
    cutoffs: list[dict]
    cutoff_count: int
    evaluation_horizon_months: int


def top_decile_backtest(
    priorities: list[AccountPriority],
    future_invoice_groups: list[InvoiceGroup],
    cutoff_date: str = "",
    evaluation_end_date: str = "",
) -> BacktestCutoffResult:
    if not priorities:
        return BacktestCutoffResult(cutoff_date, evaluation_end_date, None, None, None, 0, 0)
    ordered = sorted(priorities, key=lambda item: (item.priority_rank, item.account))
    ranked_accounts = {item.account for item in ordered}
    target_count = max(1, int(np.ceil(len(ordered) * 0.10)))
    boundary_score = ordered[target_count - 1].final_priority_score
    selected = {
        item.account for item in ordered
        if item.final_priority_score > boundary_score
        or np.isclose(item.final_priority_score, boundary_score, rtol=0, atol=1e-12)
    }
    sales = {account: Decimal("0") for account in ranked_accounts}
    for group in future_invoice_groups:
        if group.rfm_eligible and group.standardized_account_name in ranked_accounts:
            sales[group.standardized_account_name] += group.si_amount
    total_sales = sum(sales.values(), Decimal("0"))
    n = len(ordered)
    k = len(selected)
    expected = k / n
    capture = (
        float(sum((sales[account] for account in selected), Decimal("0")) / total_sales)
        if total_sales else None
    )
    lift = capture / expected if capture is not None and expected > 0 else None
    return BacktestCutoffResult(
        cutoff_date, evaluation_end_date, capture, expected, lift, n, k
    )


def run_historical_backtest(
    invoice_groups: list[InvoiceGroup],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
    eligible_accounts: set[str] | None = None,
) -> HistoricalBacktestSummary:
    valid = [
        group for group in invoice_groups
        if group.rfm_eligible
        and (eligible_accounts is None or group.standardized_account_name in eligible_accounts)
    ]
    results: list[dict] = []
    for cutoff_text in config.backtest_cutoffs:
        cutoff = pd.Timestamp(cutoff_text)
        evaluation_end = cutoff + pd.DateOffset(months=config.backtest_horizon_months)
        future = [group for group in valid if cutoff < group.si_date <= evaluation_end]
        priorities, _ = compute_priorities(
            compute_rfm(valid, cutoff, eligible_accounts),
            compute_settlement_metrics(valid, cutoff),
        )
        results.append(asdict(top_decile_backtest(
            priorities, future, cutoff.date().isoformat(), evaluation_end.date().isoformat()
        )))
    return HistoricalBacktestSummary(
        cutoffs=results,
        cutoff_count=len(results),
        evaluation_horizon_months=config.backtest_horizon_months,
    )