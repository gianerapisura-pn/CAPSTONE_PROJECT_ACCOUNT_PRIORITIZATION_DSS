from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

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
    if not values:
        return {}
    series = pd.Series(values, dtype="float64")
    unique = sorted(series.dropna().unique(), reverse=higher_is_better)
    if len(unique) == 1:
        return {key: 3 for key in values}
    scores: dict[str, int] = {}
    for key, value in values.items():
        rank = unique.index(value)
        percentile = 1 - (rank / max(len(unique) - 1, 1))
        if higher_is_better:
            score = 1 + round(percentile * 4)
        else:
            score = 5 - round(percentile * 4)
        scores[key] = int(max(1, min(5, score)))
    return scores


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
