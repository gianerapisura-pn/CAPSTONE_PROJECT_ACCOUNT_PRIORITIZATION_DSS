from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr

from app.analytics.prescriptive.scoring import AccountPriority, assign_priority_groups


@dataclass(frozen=True)
class SensitivitySummary:
    iterations: int
    weight_range: float
    mean_spearman: float
    min_spearman: float
    group_movement_rate: float


def run_sensitivity(
    priorities: list[AccountPriority],
    base_weights: dict[str, float],
    weight_range: float,
    iterations: int,
    random_seed: int,
) -> SensitivitySummary:
    if not priorities:
        return SensitivitySummary(iterations, weight_range, 0.0, 0.0, 0.0)
    rng = np.random.default_rng(random_seed)
    base_order = {item.account: item.priority_rank for item in priorities}
    spearman_values: list[float] = []
    moved = 0
    total = 0
    for _ in range(iterations):
        rfm_weight = max(0.0, base_weights.get("rfm", 0.5) + rng.uniform(-weight_range, weight_range))
        settlement_weight = max(0.0, base_weights.get("settlement", 0.5) + rng.uniform(-weight_range, weight_range))
        total_weight = rfm_weight + settlement_weight or 1.0
        rfm_weight /= total_weight
        settlement_weight /= total_weight
        scores = {
            item.account: item.normalized_rfm * rfm_weight + item.normalized_settlement * settlement_weight
            for item in priorities
        }
        ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        new_rank = {account: index for index, (account, _) in enumerate(ordered, start=1)}
        corr = spearmanr(
            [base_order[item.account] for item in priorities],
            [new_rank[item.account] for item in priorities],
        ).correlation
        spearman_values.append(float(corr if not np.isnan(corr) else 1.0))
        new_groups = assign_priority_groups(list(scores.items()))
        for item in priorities:
            moved += int(new_groups[item.account] != item.priority_group)
            total += 1
    return SensitivitySummary(
        iterations=iterations,
        weight_range=weight_range,
        mean_spearman=float(np.mean(spearman_values)),
        min_spearman=float(np.min(spearman_values)),
        group_movement_rate=moved / total if total else 0.0,
    )
