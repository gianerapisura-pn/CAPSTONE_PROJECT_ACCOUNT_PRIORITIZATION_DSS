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


def top_decile_backtest(
    priorities: list[AccountPriority],
    future_invoice_groups: list[InvoiceGroup],
    repetitions: int = 100,
    random_seed: int = 42,
) -> BacktestSummary:
    if not priorities:
        return BacktestSummary(0.0, 0.0, 0.0)
    account_sales: dict[str, Decimal] = {}
    for group in future_invoice_groups:
        if group.rfm_eligible:
            account_sales[group.standardized_account_name] = account_sales.get(group.standardized_account_name, Decimal("0")) + group.si_amount
    total_sales = sum(account_sales.values(), Decimal("0"))
    if total_sales == 0:
        return BacktestSummary(0.0, 0.0, 0.0)
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
    return BacktestSummary(capture, baseline, lift)


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
    future = [group for group in eligible if group.si_date > cutoff]
    priorities, _ = compute_priorities(compute_rfm(historical, cutoff), compute_settlement_metrics(historical))
    return top_decile_backtest(priorities, future, repetitions, random_seed)
