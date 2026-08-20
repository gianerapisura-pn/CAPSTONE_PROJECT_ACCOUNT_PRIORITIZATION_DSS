from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from app.analytics.prescriptive.scoring import AccountPriority
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
