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
    max_spearman: float
    group_movement_rate: float
    max_group_movement_rate: float
    scenarios: list[dict]


def run_sensitivity(
    priorities: list[AccountPriority],
    base_weights: dict[str, float],
    weight_range: float,
    iterations: int,
    random_seed: int,
) -> SensitivitySummary:
    if not priorities:
        return SensitivitySummary(iterations, weight_range, 0.0, 0.0, 0.0, 0.0, 0.0, [])
    rng = np.random.default_rng(random_seed)
    base_order = {item.account: item.priority_rank for item in priorities}
    spearman_values: list[float] = []
    movement_rates: list[float] = []
    scenarios: list[dict] = []
    for iteration in range(1, iterations + 1):
        rfm_weight = max(0.0, base_weights.get("rfm", 0.5) * (1 + rng.uniform(-weight_range, weight_range)))
        settlement_weight = max(0.0, base_weights.get("settlement", 0.5) * (1 + rng.uniform(-weight_range, weight_range)))
        total_weight = rfm_weight + settlement_weight or 1.0
        rfm_weight /= total_weight
        settlement_weight /= total_weight
        scores = {
            item.account: item.normalized_rfm * rfm_weight + item.normalized_settlement * settlement_weight
            for item in priorities
        }
        ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        new_rank: dict[str, int] = {}
        previous_score = None
        rank = 0
        for index, (account, score) in enumerate(ordered, start=1):
            if previous_score is None or not np.isclose(score, previous_score, rtol=0, atol=1e-12):
                rank = index
            new_rank[account] = rank
            previous_score = score
        corr = spearmanr(
            [base_order[item.account] for item in priorities],
            [new_rank[item.account] for item in priorities],
        ).correlation
        spearman_values.append(float(corr if not np.isnan(corr) else 1.0))
        new_groups = assign_priority_groups(list(scores.items()))
        moved = 0
        for item in priorities:
            did_move = new_groups[item.account] != item.priority_group
            moved += int(did_move)
            scenarios.append({
                "perturbation_level": weight_range, "iteration": iteration,
                "rfm_weight": rfm_weight, "settlement_weight": settlement_weight,
                "actual_rfm_weight": rfm_weight, "actual_settlement_weight": settlement_weight,
                "account": item.account, "baseline_score": item.final_priority_score,
                "scenario_score": scores[item.account], "baseline_rank": item.priority_rank,
                "scenario_rank": new_rank[item.account],
                "rank_difference": new_rank[item.account] - item.priority_rank,
                "rank_change": new_rank[item.account] - item.priority_rank,
                "baseline_priority_group": item.priority_group,
                "scenario_priority_group": new_groups[item.account],
                "moved_group": did_move, "group_changed": did_move,
            })
        movement_rates.append(moved / len(priorities))
    return SensitivitySummary(
        iterations=iterations,
        weight_range=weight_range,
        mean_spearman=float(np.mean(spearman_values)),
        min_spearman=float(np.min(spearman_values)),
        max_spearman=float(np.max(spearman_values)),
        group_movement_rate=float(np.mean(movement_rates)),
        max_group_movement_rate=float(np.max(movement_rates)),
        scenarios=scenarios,
    )
