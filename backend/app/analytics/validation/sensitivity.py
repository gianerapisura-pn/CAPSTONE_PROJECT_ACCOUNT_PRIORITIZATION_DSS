from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.stats import spearmanr

from app.analytics.descriptive.rfm import AccountRFM
from app.analytics.descriptive.settlement import AccountSettlement
from app.analytics.prescriptive.scoring import (
    CRITERIA,
    AccountPriority,
    analytical_ranks,
    assign_priority_groups,
    compute_priorities,
)


@dataclass(frozen=True)
class SensitivitySummary:
    iterations: int
    weight_range: float
    mean_spearman: float
    min_spearman: float
    max_spearman: float
    group_movement_rate: float
    max_group_movement_rate: float
    accounts_changing_group_at_least_once: int
    baseline_top_ten_remain_high: bool
    scenarios: list[dict]


@dataclass(frozen=True)
class CriticInfluence:
    removed_account: str
    recomputed_weights: dict[str, float]
    maximum_absolute_weight_change: float
    spearman_correlation: float
    group_movement_rate: float


def run_sensitivity(
    priorities: list[AccountPriority],
    base_weights: dict[str, float],
    weight_range: float,
    iterations: int,
    random_seed: int,
) -> SensitivitySummary:
    if not priorities or set(base_weights) != set(CRITERIA):
        return SensitivitySummary(
            iterations, weight_range, 0.0, 0.0, 0.0, 0.0, 0.0, 0, False, []
        )
    rng = np.random.default_rng(random_seed)
    baseline_ranks = {item.account: item.priority_rank for item in priorities}
    baseline_top_ten = {
        item.account for item in priorities if item.priority_rank <= 10
    }
    changed_accounts: set[str] = set()
    top_ten_stable = True
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
            if changed:
                changed_accounts.add(item.account)
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
        top_ten_stable = top_ten_stable and all(
            groups.get(account) == "High" for account in baseline_top_ten
        )
        movement_rates.append(moved / len(priorities))
    return SensitivitySummary(
        iterations=iterations,
        weight_range=weight_range,
        mean_spearman=float(np.mean(spearman_values)),
        min_spearman=float(np.min(spearman_values)),
        max_spearman=float(np.max(spearman_values)),
        group_movement_rate=float(np.mean(movement_rates)),
        max_group_movement_rate=float(np.max(movement_rates)),
        accounts_changing_group_at_least_once=len(changed_accounts),
        baseline_top_ten_remain_high=top_ten_stable,
        scenarios=scenarios,
    )


def run_leave_one_out_influence(
    rfm: list[AccountRFM],
    settlement: list[AccountSettlement],
    baseline_priorities: list[AccountPriority],
    baseline_weights: dict[str, float],
) -> list[dict]:
    baseline_rank = {item.account: item.priority_rank for item in baseline_priorities}
    baseline_group = {item.account: item.priority_group for item in baseline_priorities}
    results: list[dict] = []
    for removed in sorted(baseline_rank):
        reduced_priorities, weights = compute_priorities(
            [item for item in rfm if item.account != removed],
            [item for item in settlement if item.account != removed],
        )
        if not reduced_priorities or not weights:
            continue
        common = [item.account for item in reduced_priorities if item.account in baseline_rank]
        reduced_rank = {item.account: item.priority_rank for item in reduced_priorities}
        reduced_group = {item.account: item.priority_group for item in reduced_priorities}
        correlation = spearmanr(
            [baseline_rank[account] for account in common],
            [reduced_rank[account] for account in common],
        ).correlation
        result = CriticInfluence(
            removed_account=removed,
            recomputed_weights=weights,
            maximum_absolute_weight_change=max(
                abs(weights[criterion] - baseline_weights[criterion])
                for criterion in CRITERIA
            ),
            spearman_correlation=float(correlation if not np.isnan(correlation) else 1.0),
            group_movement_rate=sum(
                reduced_group[account] != baseline_group[account] for account in common
            ) / len(common),
        )
        results.append(asdict(result))
    return results