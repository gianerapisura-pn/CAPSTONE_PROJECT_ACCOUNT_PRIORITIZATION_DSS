from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np
import pandas as pd

from app.analytics.descriptive.rfm import AccountRFM
from app.analytics.descriptive.settlement import AccountSettlement

CRITERIA = ("recency", "frequency", "monetary", "settlement")


@dataclass(frozen=True)
class AccountPriority:
    account: str
    rfm_score: float
    recency_days: int
    frequency: int
    monetary: Decimal
    settlement_days_avg: float
    normalized_recency: float
    normalized_frequency: float
    normalized_monetary: float
    normalized_settlement: float
    recency_contribution: float
    frequency_contribution: float
    monetary_contribution: float
    settlement_contribution: float
    final_priority_score: float
    priority_rank: int
    priority_group: str


def normalize(values: dict[str, float], benefit: bool) -> dict[str, float]:
    if not values:
        return {}
    minimum, maximum = min(values.values()), max(values.values())
    if maximum == minimum:
        return {key: 0.5 for key in values}
    if benefit:
        return {key: (value - minimum) / (maximum - minimum) for key, value in values.items()}
    return {key: (maximum - value) / (maximum - minimum) for key, value in values.items()}


def critic_weights(criteria_frame: pd.DataFrame) -> dict[str, float]:
    """Return Pearson CRITIC weights, or no weights when total information is zero."""
    if criteria_frame.empty:
        return {}
    frame = criteria_frame.loc[:, list(CRITERIA)]
    std = frame.std(axis=0, ddof=0).fillna(0.0)
    informative = [criterion for criterion in CRITERIA if std[criterion] > 0.0]
    if not informative:
        return {}
    corr = frame.loc[:, informative].corr(method="pearson")
    information = std.loc[informative] * (1.0 - corr).sum(axis=0)
    total = float(information.sum())
    if np.isclose(total, 0.0, rtol=0.0, atol=1e-15):
        return {}
    return {
        criterion: float(information[criterion] / total) if criterion in informative else 0.0
        for criterion in CRITERIA
    }


def analytical_ranks(scored: list[tuple[str, float]]) -> dict[str, int]:
    ranks: dict[str, int] = {}
    previous_score: float | None = None
    current_rank = 0
    for position, (account, score) in enumerate(
        sorted(scored, key=lambda item: (-item[1], item[0])), start=1
    ):
        if previous_score is None or not np.isclose(score, previous_score, rtol=0, atol=1e-12):
            current_rank = position
        ranks[account] = current_rank
        previous_score = score
    return ranks


def assign_priority_groups(scored: list[tuple[str, float]]) -> dict[str, str]:
    """Assign high/medium/low thirds while keeping equal-score boundaries intact."""
    if not scored:
        return {}
    ordered = sorted(scored, key=lambda item: (-item[1], item[0]))
    if len({score for _, score in ordered}) == 1:
        return {account: "Medium" for account, _ in ordered}
    total = len(ordered)
    high_target = int(np.ceil(total / 3))
    low_target = int(np.ceil(total / 3))
    first = high_target
    while first < total and np.isclose(
        ordered[first - 1][1], ordered[first][1], rtol=0, atol=1e-12
    ):
        first += 1
    second = max(first, total - low_target)
    while second < total and np.isclose(
        ordered[second - 1][1], ordered[second][1], rtol=0, atol=1e-12
    ):
        second += 1
    return {
        account: "High" if index < first else "Medium" if index < second else "Low"
        for index, (account, _) in enumerate(ordered)
    }


def compute_priorities(
    rfm: list[AccountRFM], settlement: list[AccountSettlement]
) -> tuple[list[AccountPriority], dict[str, float]]:
    settlement_by_account = {
        item.account: item for item in settlement if item.average_settlement_days is not None
    }
    rfm_by_account = {item.account: item for item in rfm}
    accounts = sorted(set(rfm_by_account) & set(settlement_by_account))
    if not accounts:
        return [], {}
    raw = {
        "recency": {account: float(rfm_by_account[account].recency_days) for account in accounts},
        "frequency": {account: float(rfm_by_account[account].frequency) for account in accounts},
        "monetary": {account: float(rfm_by_account[account].monetary) for account in accounts},
        "settlement": {
            account: float(settlement_by_account[account].average_settlement_days)
            for account in accounts
        },
    }
    normalized = {
        "recency": normalize(raw["recency"], benefit=False),
        "frequency": normalize(raw["frequency"], benefit=True),
        "monetary": normalize(raw["monetary"], benefit=True),
        "settlement": normalize(raw["settlement"], benefit=False),
    }
    frame = pd.DataFrame(
        {criterion: [normalized[criterion][account] for account in accounts] for criterion in CRITERIA},
        index=accounts,
    )
    weights = critic_weights(frame)
    if not weights:
        return [], {}
    contributions = {
        account: {
            criterion: normalized[criterion][account] * weights[criterion]
            for criterion in CRITERIA
        }
        for account in accounts
    }
    scores = {account: sum(contributions[account].values()) for account in accounts}
    ranks = analytical_ranks(list(scores.items()))
    groups = assign_priority_groups(list(scores.items()))
    priorities = [
        AccountPriority(
            account=account,
            rfm_score=rfm_by_account[account].rfm_score,
            recency_days=rfm_by_account[account].recency_days,
            frequency=rfm_by_account[account].frequency,
            monetary=rfm_by_account[account].monetary,
            settlement_days_avg=raw["settlement"][account],
            normalized_recency=normalized["recency"][account],
            normalized_frequency=normalized["frequency"][account],
            normalized_monetary=normalized["monetary"][account],
            normalized_settlement=normalized["settlement"][account],
            recency_contribution=contributions[account]["recency"],
            frequency_contribution=contributions[account]["frequency"],
            monetary_contribution=contributions[account]["monetary"],
            settlement_contribution=contributions[account]["settlement"],
            final_priority_score=scores[account],
            priority_rank=ranks[account],
            priority_group=groups[account],
        )
        for account in accounts
    ]
    priorities.sort(key=lambda item: (item.priority_rank, item.account))
    return priorities, weights
