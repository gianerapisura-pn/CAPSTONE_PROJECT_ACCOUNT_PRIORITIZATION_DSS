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
    random_baseline_capture: float | None
    lift_over_random: float | None
    eligible_account_count: int
    selected_account_count: int
    repetitions: int = 100
    random_seed: int = 42


@dataclass(frozen=True)
class HistoricalBacktestSummary:
    cutoffs: list[dict]
    cutoff_count: int
    evaluation_horizon_months: int
    repetitions: int
    random_seed: int


def top_decile_backtest(
    priorities: list[AccountPriority],
    future_invoice_groups: list[InvoiceGroup],
    repetitions: int = 100,
    random_seed: int = 42,
    cutoff_date: str = "",
    evaluation_end_date: str = "",
) -> BacktestCutoffResult:
    if not priorities:
        return BacktestCutoffResult(
            cutoff_date, evaluation_end_date, None, None, None, 0, 0, repetitions, random_seed
        )
    ranked_accounts = {item.account for item in priorities}
    ordered = sorted(priorities, key=lambda item: (item.priority_rank, item.account))
    target_count = max(1, int(np.ceil(len(ordered) * 0.10)))
    boundary_score = ordered[target_count - 1].final_priority_score
    selected = {
        item.account
        for item in ordered
        if item.final_priority_score >= boundary_score
        or np.isclose(item.final_priority_score, boundary_score, rtol=0, atol=1e-12)
    }
    account_sales: dict[str, Decimal] = {account: Decimal("0") for account in ranked_accounts}
    for group in future_invoice_groups:
        if group.rfm_eligible and group.standardized_account_name in ranked_accounts:
            account_sales[group.standardized_account_name] += group.si_amount
    total_sales = sum(account_sales.values(), Decimal("0"))
    if total_sales == 0:
        return BacktestCutoffResult(
            cutoff_date,
            evaluation_end_date,
            None,
            None,
            None,
            len(priorities),
            len(selected),
            repetitions,
            random_seed,
        )
    capture = float(
        sum((account_sales[account] for account in selected), Decimal("0")) / total_sales
    )
    rng = np.random.default_rng(random_seed)
    accounts = sorted(ranked_accounts)
    random_captures = [
        float(
            sum(
                (account_sales[account] for account in rng.choice(accounts, size=len(selected), replace=False)),
                Decimal("0"),
            )
            / total_sales
        )
        for _ in range(repetitions)
    ]
    baseline = float(np.mean(random_captures))
    lift = capture / baseline if baseline > 0 else None
    return BacktestCutoffResult(
        cutoff_date,
        evaluation_end_date,
        capture,
        baseline,
        lift,
        len(priorities),
        len(selected),
        repetitions,
        random_seed,
    )


def run_historical_backtest(
    invoice_groups: list[InvoiceGroup],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
    repetitions: int | None = None,
    random_seed: int | None = None,
) -> HistoricalBacktestSummary:
    """Run the fixed six-cutoff, 12-calendar-month historical ranking protocol."""
    repetitions = repetitions or config.random_baseline_repetitions
    random_seed = config.random_seed if random_seed is None else random_seed
    valid = [group for group in invoice_groups if group.rfm_eligible]
    results: list[dict] = []
    for cutoff_text in config.backtest_cutoffs:
        cutoff = pd.Timestamp(cutoff_text)
        evaluation_end = cutoff + pd.DateOffset(months=config.backtest_horizon_months)
        historical = [group for group in valid if group.si_date <= cutoff]
        future = [group for group in valid if cutoff < group.si_date <= evaluation_end]
        priorities, _ = compute_priorities(
            compute_rfm(historical, cutoff),
            compute_settlement_metrics(historical, cutoff),
        )
        result = top_decile_backtest(
            priorities,
            future,
            repetitions,
            random_seed,
            cutoff.date().isoformat(),
            evaluation_end.date().isoformat(),
        )
        results.append(asdict(result))
    return HistoricalBacktestSummary(
        cutoffs=results,
        cutoff_count=len(results),
        evaluation_horizon_months=config.backtest_horizon_months,
        repetitions=repetitions,
        random_seed=random_seed,
    )
