from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

import numpy as np
import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.prescriptive.scoring import AccountPriority, compute_priorities, scoring_activity_24m
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
    closure_years: dict[str, int] | None = None,
    analysis_reference_date: pd.Timestamp | None = None,
) -> HistoricalBacktestSummary:
    reference = pd.Timestamp(analysis_reference_date) if analysis_reference_date is not None else None
    valid = [
        group for group in invoice_groups
        if group.rfm_eligible
        and (eligible_accounts is None or group.standardized_account_name in eligible_accounts)
        and (reference is None or group.si_date <= reference)
    ]
    results: list[dict] = []
    cutoffs = config.backtest_cutoffs
    if reference is not None:
        first_year = min(pd.Timestamp(value).year for value in config.backtest_cutoffs)
        cutoffs = tuple(
            f"{year}-12-31" for year in range(first_year, reference.year)
            if pd.Timestamp(f"{year + 1}-12-31") <= reference
        )
    for cutoff_text in cutoffs:
        cutoff = pd.Timestamp(cutoff_text)
        eligible_at_cutoff = (
            None if eligible_accounts is None else {
                account for account in eligible_accounts
                if (
                    not closure_years
                    or account not in closure_years
                    or cutoff.year < closure_years[account]
                )
            }
        )
        evaluation_end = cutoff + pd.DateOffset(months=config.backtest_horizon_months)
        cutoff_valid = [
            group for group in valid
            if eligible_at_cutoff is None
            or group.standardized_account_name in eligible_at_cutoff
        ]
        future = [
            group for group in cutoff_valid if cutoff < group.si_date <= evaluation_end
        ]
        priorities, _ = compute_priorities(
            compute_rfm(cutoff_valid, cutoff, eligible_at_cutoff),
            compute_settlement_metrics(cutoff_valid, cutoff),
            scoring_activity_24m(cutoff_valid, cutoff, {
                group.standardized_account_name for group in cutoff_valid
                if group.rfm_eligible and group.si_date <= cutoff
            }),
        )
        results.append(asdict(top_decile_backtest(
            priorities, future, cutoff.date().isoformat(), evaluation_end.date().isoformat()
        )))
    return HistoricalBacktestSummary(
        cutoffs=results,
        cutoff_count=len(results),
        evaluation_horizon_months=config.backtest_horizon_months,
    )
