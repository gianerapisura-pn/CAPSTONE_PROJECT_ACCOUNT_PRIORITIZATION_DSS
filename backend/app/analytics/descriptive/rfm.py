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
    recency_score: int
    frequency_score: int
    monetary_score: int
    rfm_score: float


def _tie_preserving_score(values: dict[str, float], higher_is_better: bool) -> dict[str, int]:
    """Map account-level average percentile ranks to tie-preserving 1-5 bands."""
    if not values:
        return {}
    series = pd.Series(values, dtype="float64")
    if series.nunique(dropna=True) <= 1:
        return {key: 3 for key in values}
    percentiles = series.rank(method="average", pct=True, ascending=True)
    if not higher_is_better:
        percentiles = 1 - percentiles + (1 / len(series))
    bands = np.ceil(percentiles * 5).clip(1, 5).astype(int)
    return {str(key): int(score) for key, score in bands.items()}


def compute_rfm(invoice_groups: list[InvoiceGroup], cutoff_date: pd.Timestamp | None = None) -> list[AccountRFM]:
    eligible = [group for group in invoice_groups if group.rfm_eligible]
    if not eligible:
        return []
    cutoff = cutoff_date or max(group.si_date for group in eligible)
    accounts = sorted({group.standardized_account_name for group in eligible})
    recency: dict[str, float] = {}
    frequency: dict[str, float] = {}
    monetary: dict[str, float] = {}
    monetary_decimal: dict[str, Decimal] = {}
    for account in accounts:
        groups = [group for group in eligible if group.standardized_account_name == account and group.si_date <= cutoff]
        if not groups:
            continue
        latest = max(group.si_date for group in groups)
        total = sum((group.si_amount for group in groups), Decimal("0"))
        recency[account] = float((cutoff - latest).days)
        frequency[account] = float(len(groups))
        monetary[account] = float(total)
        monetary_decimal[account] = total
    r_scores = _tie_preserving_score(recency, higher_is_better=False)
    f_scores = _tie_preserving_score(frequency, higher_is_better=True)
    m_scores = _tie_preserving_score(monetary, higher_is_better=True)
    results = []
    for account in sorted(recency):
        rfm_score = (r_scores[account] + f_scores[account] + m_scores[account]) / 3
        results.append(
            AccountRFM(
                account=account,
                recency_days=int(recency[account]),
                frequency=int(frequency[account]),
                monetary=monetary_decimal[account],
                recency_score=r_scores[account],
                frequency_score=f_scores[account],
                monetary_score=m_scores[account],
                rfm_score=rfm_score,
            )
        )
    return results
