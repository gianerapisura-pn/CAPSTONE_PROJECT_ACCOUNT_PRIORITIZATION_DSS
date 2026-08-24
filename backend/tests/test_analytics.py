from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pandas as pd

from app.analytics.descriptive.rfm import _tie_preserving_score, compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.prescriptive.scoring import (
    CRITERIA,
    AccountPriority,
    analytical_ranks,
    assign_priority_groups,
    compute_priorities,
    critic_weights,
    normalize,
)
from app.analytics.validation.backtest import run_historical_backtest, top_decile_backtest
from app.analytics.validation.sensitivity import run_sensitivity
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.etl.invoices import SourceRow, group_invoices, invoice_group_key


def row(
    account: str,
    si: str,
    si_date: str,
    si_amount: str,
    cr: str,
    cr_date: str,
    cr_amount: str,
    ewt: str = "0",
    status: str = "Fully Paid",
) -> SourceRow:
    return SourceRow(
        customer_name_raw=account,
        standardized_account_name=account.upper(),
        si_no=si,
        si_date=pd.Timestamp(si_date),
        si_amount=Decimal(si_amount),
        cr_no=cr,
        cr_date=pd.Timestamp(cr_date) if cr_date else None,
        cr_amount=Decimal(cr_amount),
        ewt=Decimal(ewt),
        payment_mode="Bank",
        payment_status_raw=status,
        payment_status=status,
        is_cancelled=status == "Cancelled",
        import_batch_id="batch",
        source_sheet="Sheet1",
        source_row_number=1,
    )


def priority(account: str, score: float, rank: int, group: str) -> AccountPriority:
    return AccountPriority(
        account=account,
        rfm_score=3.0,
        recency_days=10,
        frequency=2,
        monetary=Decimal("100"),
        settlement_days_avg=20.0,
        normalized_recency=score,
        normalized_frequency=score,
        normalized_monetary=score,
        normalized_settlement=score,
        recency_contribution=score / 4,
        frequency_contribution=score / 4,
        monetary_contribution=score / 4,
        settlement_contribution=score / 4,
        final_priority_score=score,
        priority_rank=rank,
        priority_group=group,
    )


def test_invoice_grouping_prevents_frequency_and_monetary_inflation():
    groups = group_invoices([
        row("Acme", "SI-1", "2026-01-01", "100.00", "CR-1", "2026-01-10", "50.00"),
        row("Acme", "SI-1", "2026-01-01", "100.00", "CR-2", "2026-01-20", "50.00"),
    ])
    assert len(groups) == 1
    metric = compute_rfm(groups, cutoff_date=pd.Timestamp("2026-12-31"))[0]
    assert metric.frequency == 1
    assert metric.monetary == Decimal("100.00")
    assert groups[0].final_cr_date == pd.Timestamp("2026-01-20")
    assert compute_settlement_metrics(groups)[0].average_settlement_days == 19


def test_reconciliation_uses_cr_plus_ewt_exactly_after_cent_rounding():
    ok, one_cent_short = group_invoices([
        row("A", "SI-1", "2026-01-01", "100.00", "CR-1", "2026-01-05", "98.00", "2.00"),
        row("B", "SI-2", "2026-01-01", "100.00", "CR-2", "2026-01-05", "98.00", "1.99"),
    ])
    assert ok.reconciled
    assert one_cent_short.reconciliation_difference == Decimal("-0.01")
    assert not one_cent_short.reconciled


def test_invoice_identity_excludes_lineage():
    original = row("A", "SI-1", "2026-01-01", "100.00", "CR-1", "2026-01-05", "100")
    later = replace(original, import_batch_id="later", source_sheet="Other", source_row_number=99)
    assert invoice_group_key(original) == invoice_group_key(later)


def test_negative_chronology_and_cancelled_component_eligibility():
    negative = group_invoices([
        row("A", "SI-1", "2026-02-01", "100", "CR-1", "2026-01-31", "100")
    ])[0]
    cancelled = group_invoices([
        row("B", "SI-X", "2026-01-01", "100", "", "", "0", status="Cancelled")
    ])[0]
    assert negative.rfm_eligible and not negative.settlement_eligible
    assert compute_settlement_metrics([negative]) == []
    assert not cancelled.rfm_eligible and not cancelled.settlement_eligible


def test_unsupported_payment_status_is_ineligible_for_all_analytics():
    unsupported = group_invoices([
        row("A", "SI-1", "2026-01-01", "100", "CR-1", "2026-01-05", "100", status="Needs Review")
    ])[0]
    assert not unsupported.rfm_eligible
    assert not unsupported.settlement_eligible
    assert unsupported.review_reason == "Unsupported payment status; excluded from analytics pending review."


def test_settlement_cutoff_prevents_future_collection_leakage():
    group = group_invoices([
        row("A", "SI-1", "2026-01-01", "100", "CR-1", "2026-03-01", "100")
    ])[0]
    assert compute_settlement_metrics([group], pd.Timestamp("2026-02-01")) == []
    assert compute_settlement_metrics([group], pd.Timestamp("2026-03-01"))[0].average_settlement_days == 59


def test_rfm_average_rank_formula_ties_direction_and_constant_component():
    values = {"A": 10, "B": 20, "C": 20, "D": 40}
    assert _tie_preserving_score(values, True) == {"A": 2, "B": 4, "C": 4, "D": 5}
    assert _tie_preserving_score(values, False) == {"A": 5, "B": 4, "C": 4, "D": 2}
    assert set(_tie_preserving_score({"A": 7, "B": 7}, True).values()) == {3}


def test_four_criterion_normalization_critic_and_fps():
    groups = group_invoices([
        row("A", "A1", "2026-01-01", "100", "A1", "2026-01-11", "100"),
        row("A", "A2", "2026-04-01", "200", "A2", "2026-04-06", "200"),
        row("B", "B1", "2026-02-01", "80", "B1", "2026-04-02", "80"),
        row("C", "C1", "2026-03-01", "50", "C1", "2026-03-21", "50"),
    ])
    assert normalize({"a": 1, "b": 3}, benefit=False)["a"] == 1
    assert normalize({"a": 1, "b": 3}, benefit=True)["b"] == 1
    assert normalize({"a": 2, "b": 2}, benefit=True) == {"a": 0.5, "b": 0.5}
    priorities, weights = compute_priorities(compute_rfm(groups), compute_settlement_metrics(groups))
    assert priorities
    assert set(weights) == set(CRITERIA)
    assert abs(sum(weights.values()) - 1) < 1e-12
    for item in priorities:
        total = (
            item.recency_contribution
            + item.frequency_contribution
            + item.monetary_contribution
            + item.settlement_contribution
        )
        assert abs(total - item.final_priority_score) < 1e-12


def test_constant_criterion_has_zero_weight_and_all_constant_is_non_discriminating():
    frame = pd.DataFrame({
        "recency": [0.0, 0.5, 1.0],
        "frequency": [0.0, 0.5, 1.0],
        "monetary": [1.0, 0.5, 0.0],
        "settlement": [0.5, 0.5, 0.5],
    })
    weights = critic_weights(frame)
    assert weights["settlement"] == 0
    assert abs(sum(weights.values()) - 1) < 1e-12
    assert critic_weights(pd.DataFrame({name: [0.5, 0.5] for name in CRITERIA})) == {}


def test_priority_ranks_and_both_group_boundaries_preserve_ties():
    assert analytical_ranks([("B", 1), ("A", 1), ("C", 0.5)]) == {"A": 1, "B": 1, "C": 3}
    normal = assign_priority_groups([(letter, float(7-index)) for index, letter in enumerate("ABCDEF", start=1)])
    assert [normal[letter] for letter in "ABCDEF"] == ["High", "High", "Medium", "Medium", "Low", "Low"]
    first = assign_priority_groups([("A", 6), ("B", 5), ("C", 5), ("D", 3), ("E", 2), ("F", 1)])
    second = assign_priority_groups([("A", 6), ("B", 5), ("C", 4), ("D", 3), ("E", 3), ("F", 1)])
    assert first["B"] == first["C"] == "High"
    assert second["D"] == second["E"] == "Medium"


def test_sensitivity_perturbs_four_weights_reproducibly_for_all_ranges():
    groups = group_invoices([
        row("A", "A1", "2026-01-01", "100", "A1", "2026-01-10", "100"),
        row("B", "B1", "2026-02-01", "50", "B1", "2026-04-01", "50"),
        row("C", "C1", "2026-03-01", "75", "C1", "2026-03-20", "75"),
    ])
    priorities, weights = compute_priorities(compute_rfm(groups), compute_settlement_metrics(groups))
    results = [run_sensitivity(priorities, weights, level, 100, 42) for level in (0.10, 0.20, 0.30, 0.40)]
    required = {f"perturbed_{criterion}_weight" for criterion in CRITERIA}
    assert sum(result.iterations for result in results) == 400
    assert sum(len(result.scenarios) for result in results) == 400 * len(priorities)
    assert all(required <= scenario.keys() for result in results for scenario in result.scenarios)
    assert all(
        abs(sum(scenario[key] for key in required) - 1) < 1e-12
        for result in results for scenario in result.scenarios
    )
    assert results[0].scenarios == run_sensitivity(priorities, weights, 0.10, 100, 42).scenarios


def test_backtest_expands_top_decile_ties_and_excludes_future_new_accounts():
    priorities = [
        priority("A", 1.0, 1, "High"),
        priority("B", 1.0, 1, "High"),
        priority("C", 0.2, 3, "Low"),
    ]
    future = group_invoices([
        row("A", "F-1", "2024-01-01", "100", "1", "2024-01-02", "100"),
        row("NEW", "F-2", "2024-01-01", "10000", "2", "2024-01-02", "10000"),
    ])
    result = top_decile_backtest(priorities, future, repetitions=100, random_seed=42)
    assert result.eligible_account_count == 3
    assert result.selected_account_count == 2
    assert result.top_decile_capture == 1
    assert result.random_baseline_capture is not None


def test_backtest_zero_denominators_are_unavailable_and_six_cutoffs_persist():
    priorities = [priority("A", 1.0, 1, "High")]
    empty = top_decile_backtest(priorities, [], repetitions=100, random_seed=42)
    assert empty.top_decile_capture is None
    assert empty.lift_over_random is None
    summary = run_historical_backtest([], DEFAULT_ANALYTICS_CONFIG)
    assert [row["cutoff_date"] for row in summary.cutoffs] == list(DEFAULT_ANALYTICS_CONFIG.backtest_cutoffs)
    assert all(row["evaluation_end_date"].endswith("-12-31") for row in summary.cutoffs)
    assert summary.cutoff_count == 6


def test_non_discriminating_population_publishes_without_fake_ranking():
    from app.services.analytics_runner import run_account_prioritization

    groups = group_invoices([
        row("A", "A1", "2026-01-01", "100", "A1", "2026-01-11", "100"),
        row("B", "B1", "2026-01-01", "100", "B1", "2026-01-11", "100"),
    ])
    result = run_account_prioritization(groups)
    assert result.status == "successful"
    assert result.mcs_status == "non_discriminating"
    assert result.critic_weights == {}
    assert result.priorities == []
    assert result.sensitivity == []
    assert result.warnings
