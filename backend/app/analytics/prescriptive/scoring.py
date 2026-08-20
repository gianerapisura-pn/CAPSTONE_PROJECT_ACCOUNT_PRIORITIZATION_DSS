from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.analytics.descriptive.rfm import AccountRFM
from app.analytics.descriptive.settlement import AccountSettlement


@dataclass(frozen=True)
class AccountPriority:
    account: str
    rfm_score: float
    settlement_days_avg: float
    normalized_rfm: float
    normalized_settlement: float
    final_priority_score: float
    priority_rank: int
    priority_group: str


def normalize(values: dict[str, float], benefit: bool) -> dict[str, float]:
    if not values:
        return {}
    minimum = min(values.values())
    maximum = max(values.values())
    if maximum == minimum:
        return {key: 1.0 for key in values}
    if benefit:
        return {key: (value - minimum) / (maximum - minimum) for key, value in values.items()}
    return {key: (maximum - value) / (maximum - minimum) for key, value in values.items()}


def critic_weights(criteria_frame: pd.DataFrame) -> dict[str, float]:
    if criteria_frame.empty:
        return {}
    std = criteria_frame.std(axis=0, ddof=0).fillna(0)
    corr = criteria_frame.corr().fillna(0)
    conflict = (1 - corr).sum(axis=0)
    information = std * conflict
    total = float(information.sum())
    if total == 0:
        equal = 1 / len(criteria_frame.columns)
        return {column: equal for column in criteria_frame.columns}
    return {column: float(information[column] / total) for column in criteria_frame.columns}


def assign_priority_groups(scored: list[tuple[str, float]]) -> dict[str, str]:
    if not scored:
        return {}
    ordered = sorted(scored, key=lambda item: (-item[1], item[0]))
    unique_scores = sorted({score for _, score in ordered}, reverse=True)
    high_cut_index = max(0, int(np.ceil(len(unique_scores) / 3)) - 1)
    medium_cut_index = max(high_cut_index, int(np.ceil(len(unique_scores) * 2 / 3)) - 1)
    high_threshold = unique_scores[high_cut_index]
    medium_threshold = unique_scores[medium_cut_index]
    groups: dict[str, str] = {}
    for account, score in ordered:
        if score >= high_threshold:
            groups[account] = "High"
        elif score >= medium_threshold:
            groups[account] = "Medium"
        else:
            groups[account] = "Low"
    return groups


def compute_priorities(rfm: list[AccountRFM], settlement: list[AccountSettlement]) -> tuple[list[AccountPriority], dict[str, float]]:
    settlement_by_account = {item.account: item for item in settlement if item.average_settlement_days is not None}
    rfm_by_account = {item.account: item for item in rfm}
    accounts = sorted(set(rfm_by_account) & set(settlement_by_account))
    if not accounts:
        return [], {}
    rfm_values = {account: rfm_by_account[account].rfm_score for account in accounts}
    settlement_values = {account: float(settlement_by_account[account].average_settlement_days or 0) for account in accounts}
    normalized_rfm = normalize(rfm_values, benefit=True)
    normalized_settlement = normalize(settlement_values, benefit=False)
    frame = pd.DataFrame(
        {
            "rfm": [normalized_rfm[account] for account in accounts],
            "settlement": [normalized_settlement[account] for account in accounts],
        },
        index=accounts,
    )
    weights = critic_weights(frame)
    raw_scores = {
        account: (normalized_rfm[account] * weights["rfm"]) + (normalized_settlement[account] * weights["settlement"])
        for account in accounts
    }
    ranks: dict[str, int] = {}
    previous_score: float | None = None
    current_rank = 0
    for position, (account, score) in enumerate(sorted(raw_scores.items(), key=lambda item: (-item[1], item[0])), start=1):
        if previous_score is None or score != previous_score:
            current_rank = position
        ranks[account] = current_rank
        previous_score = score
    groups = assign_priority_groups(list(raw_scores.items()))
    priorities = [
        AccountPriority(
            account=account,
            rfm_score=rfm_values[account],
            settlement_days_avg=settlement_values[account],
            normalized_rfm=normalized_rfm[account],
            normalized_settlement=normalized_settlement[account],
            final_priority_score=raw_scores[account],
            priority_rank=ranks[account],
            priority_group=groups[account],
        )
        for account in accounts
    ]
    priorities.sort(key=lambda item: (item.priority_rank, item.account))
    return priorities, weights
