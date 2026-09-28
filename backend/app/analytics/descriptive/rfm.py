from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import pandas as pd

from app.etl.invoices import InvoiceGroup


@dataclass(frozen=True)
class AccountRFM:
    account: str
    recency_days: int
    frequency: int
    monetary: Decimal
    r_score: int
    f_score: int
    m_score: int
    rfm_code: str
    rfm_mean_score: float


def _quantile_scores(values: dict[str, float], higher_is_better: bool) -> dict[str, int]:
    """Apply empirical q20/q40/q60/q80 thresholds with ties kept together."""
    if not values:
        return {}
    series = np.asarray(list(values.values()), dtype=float)
    if np.all(series == series[0]):
        return {key: 3 for key in values}
    thresholds = np.quantile(series, [0.20, 0.40, 0.60, 0.80], method="linear")

    def score(value: float) -> int:
        band = int(1 + sum(value > threshold for threshold in thresholds))
        return band if higher_is_better else 6 - band

    return {key: score(value) for key, value in values.items()}


def compute_rfm(
    invoice_groups: list[InvoiceGroup],
    analysis_reference_date: pd.Timestamp,
    eligible_accounts: set[str] | None = None,
) -> list[AccountRFM]:
    reference = pd.Timestamp(analysis_reference_date)
    eligible = [
        group for group in invoice_groups
        if group.rfm_eligible
        and group.si_date <= reference
        and (eligible_accounts is None or group.standardized_account_name in eligible_accounts)
    ]
    if not eligible:
        return []
    accounts = sorted({group.standardized_account_name for group in eligible})
    recency: dict[str, float] = {}
    frequency: dict[str, float] = {}
    monetary: dict[str, float] = {}
    monetary_decimal: dict[str, Decimal] = {}
    for account in accounts:
        groups = [group for group in eligible if group.standardized_account_name == account]
        latest = max(group.si_date for group in groups)
        total = sum((group.si_amount for group in groups), Decimal("0"))
        recency[account] = float((reference - latest).days)
        frequency[account] = float(len(groups))
        monetary[account] = float(total)
        monetary_decimal[account] = total
    r_scores = _quantile_scores(recency, higher_is_better=False)
    f_scores = _quantile_scores(frequency, higher_is_better=True)
    m_scores = _quantile_scores(monetary, higher_is_better=True)
    return [
        AccountRFM(
            account=account,
            recency_days=int(recency[account]),
            frequency=int(frequency[account]),
            monetary=monetary_decimal[account],
            r_score=r_scores[account],
            f_score=f_scores[account],
            m_score=m_scores[account],
            rfm_code=f"{r_scores[account]}{f_scores[account]}{m_scores[account]}",
            rfm_mean_score=(r_scores[account] + f_scores[account] + m_scores[account]) / 3,
        )
        for account in accounts
    ]
