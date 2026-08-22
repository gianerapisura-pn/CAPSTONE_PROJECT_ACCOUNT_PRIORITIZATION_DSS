from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.prescriptive.scoring import AccountPriority
from app.analytics.prescriptive.scoring import compute_priorities
from app.etl.invoices import InvoiceGroup


@dataclass(frozen=True)
class BacktestSummary:
    top_decile_capture: float
    random_baseline_capture: float
    lift_over_random: float
    cutoff_date: str | None = None
    evaluation_end_date: str | None = None
    eligible_account_count: int = 0
    selected_account_count: int = 0
    repetitions: int = 100
    random_seed: int = 42


def top_decile_backtest(
    priorities: list[AccountPriority],
    future_invoice_groups: list[InvoiceGroup],
    repetitions: int = 100,
    random_seed: int = 42,
) -> BacktestSummary:
    if not priorities:
        return BacktestSummary(0.0, 0.0, 0.0)
    ranked_accounts = {item.account for item in priorities}
    account_sales: dict[str, Decimal] = {account: Decimal("0") for account in ranked_accounts}
    for group in future_invoice_groups:
        if group.rfm_eligible and group.standardized_account_name in ranked_accounts:
            account_sales[group.standardized_account_name] += group.si_amount
    total_sales = sum(account_sales.values(), Decimal("0"))
    if total_sales == 0:
        return BacktestSummary(0.0, 0.0, 0.0, eligible_account_count=len(priorities),
                               selected_account_count=max(1, int(np.ceil(len(priorities) * 0.10))),
                               repetitions=repetitions, random_seed=random_seed)
    ordered = sorted(priorities, key=lambda item: (item.priority_rank, item.account))
    n = max(1, int(np.ceil(len(ordered) * 0.10)))
    selected = {item.account for item in ordered[:n]}
    capture = float(sum((account_sales.get(account, Decimal("0")) for account in selected), Decimal("0")) / total_sales)
    rng = np.random.default_rng(random_seed)
    accounts = [item.account for item in priorities]
    random_captures = []
    for _ in range(repetitions):
        picked = set(rng.choice(accounts, size=n, replace=False))
        random_captures.append(float(sum((account_sales.get(account, Decimal("0")) for account in picked), Decimal("0")) / total_sales))
    baseline = float(np.mean(random_captures))
    lift = capture / baseline if baseline else 0.0
    return BacktestSummary(capture, baseline, lift, eligible_account_count=len(priorities),
                           selected_account_count=n, repetitions=repetitions, random_seed=random_seed)


def run_historical_backtest(
    invoice_groups: list[InvoiceGroup],
    holdout_months: int = 12,
    repetitions: int = 100,
    random_seed: int = 42,
) -> BacktestSummary:
    """Rank on pre-cutoff evidence and evaluate only later holdout invoices."""
    eligible = [group for group in invoice_groups if group.rfm_eligible]
    if not eligible:
        return BacktestSummary(0.0, 0.0, 0.0)
    cutoff = max(group.si_date for group in eligible) - pd.DateOffset(months=holdout_months)
    historical: list[InvoiceGroup] = []
    for original in eligible:
        if original.si_date > cutoff:
            continue
        group = deepcopy(original)
        if group.final_cr_date is not None and group.final_cr_date > cutoff:
            group.final_cr_date = None
            group.reconciled = False
            group.review_reason = "Settlement evidence was unavailable at the historical cutoff."
        historical.append(group)
    evaluation_end = cutoff + pd.DateOffset(months=holdout_months)
    future = [group for group in eligible if cutoff < group.si_date <= evaluation_end]
    priorities, _ = compute_priorities(
        compute_rfm(historical, cutoff),
        compute_settlement_metrics(historical, cutoff),
    )
    summary = top_decile_backtest(priorities, future, repetitions, random_seed)
    return BacktestSummary(
        summary.top_decile_capture,
        summary.random_baseline_capture,
        summary.lift_over_random,
        cutoff.date().isoformat(),
        evaluation_end.date().isoformat(),
        summary.eligible_account_count,
        summary.selected_account_count,
        repetitions,
        random_seed,
    )
