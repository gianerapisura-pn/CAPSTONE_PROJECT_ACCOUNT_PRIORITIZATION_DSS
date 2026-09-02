from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr

from app.analytics.prescriptive.scoring import CRITERIA, AccountPriority, analytical_ranks, assign_priority_groups


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
    if not priorities or set(base_weights) != set(CRITERIA):
        return SensitivitySummary(iterations, weight_range, 0.0, 0.0, 0.0, 0.0, 0.0, [])
    rng = np.random.default_rng(random_seed)
    baseline_ranks = {item.account: item.priority_rank for item in priorities}
    spearman_values: list[float] = []
    movement_rates: list[float] = []
    scenarios: list[dict] = []
    for iteration in range(1, iterations + 1):
        perturbed = {
            criterion: base_weights[criterion] * (1.0 + rng.uniform(-weight_range, weight_range))
            for criterion in CRITERIA
        }
        total = sum(perturbed.values())
        perturbed = {criterion: value / total for criterion, value in perturbed.items()}
        scores = {
            item.account: sum(
                getattr(item, f"normalized_{criterion}") * perturbed[criterion]
                for criterion in CRITERIA
            )
            for item in priorities
        }
        ranks = analytical_ranks(list(scores.items()))
        groups = assign_priority_groups(list(scores.items()))
        correlation = spearmanr(
            [baseline_ranks[item.account] for item in priorities],
            [ranks[item.account] for item in priorities],
        ).correlation
        correlation_value = float(correlation if not np.isnan(correlation) else 1.0)
        spearman_values.append(correlation_value)
        moved = 0
        for item in priorities:
            changed = groups[item.account] != item.priority_group
            moved += int(changed)
            scenarios.append({
                "perturbation_level": weight_range,
                "iteration": iteration,
                **{f"perturbed_{criterion}_weight": perturbed[criterion] for criterion in CRITERIA},
                "account": item.account,
                "baseline_score": item.final_priority_score,
                "scenario_score": scores[item.account],
                "baseline_rank": item.priority_rank,
                "scenario_rank": ranks[item.account],
                "rank_change": ranks[item.account] - item.priority_rank,
                "spearman_correlation": correlation_value,
                "baseline_priority_group": item.priority_group,
                "scenario_priority_group": groups[item.account],
                "group_changed": changed,
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
