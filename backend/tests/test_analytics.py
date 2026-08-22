from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.prescriptive.scoring import AccountPriority, assign_priority_groups, compute_priorities, critic_weights, normalize
from app.analytics.validation.backtest import top_decile_backtest
from app.analytics.validation.sensitivity import run_sensitivity
from app.etl.invoices import SourceRow, group_invoices, invoice_group_key


def row(account: str, si: str, si_date: str, si_amount: str, cr: str, cr_date: str, cr_amount: str, ewt: str = "0", status: str = "Fully Paid") -> SourceRow:
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


def test_invoice_grouping_prevents_frequency_and_monetary_inflation():
    groups = group_invoices(
        [
            row("Acme", "SI-1", "2026-01-01", "100.00", "CR-1", "2026-01-10", "50.00"),
            row("Acme", "SI-1", "2026-01-01", "100.00", "CR-2", "2026-01-20", "50.00"),
        ]
    )
    assert len(groups) == 1
    rfm = compute_rfm(groups, cutoff_date=pd.Timestamp("2026-12-31"))[0]
    assert rfm.frequency == 1
    assert rfm.monetary == Decimal("100.00")
    assert groups[0].final_cr_date == pd.Timestamp("2026-01-20")


def test_reconciliation_uses_cr_plus_ewt_and_flags_failures():
    ok, bad = group_invoices(
        [
            row("A", "SI-1", "2026-01-01", "100.00", "CR-1", "2026-01-05", "98.00", "2.00"),
            row("B", "SI-2", "2026-01-01", "100.00", "CR-2", "2026-01-05", "90.00", "1.00"),
        ]
    )
    assert ok.reconciled
    assert not bad.reconciled
    assert bad.review_reason is not None


def test_invoice_identity_is_stable_across_batches_and_one_cent_does_not_reconcile():
    original = row("A", "SI-1", "2026-01-01", "100.00", "CR-1", "2026-01-05", "99.99")
    later_batch = replace(original, import_batch_id="later", source_sheet="Other", source_row_number=99)
    assert invoice_group_key(original) == invoice_group_key(later_batch)
    group = group_invoices([original])[0]
    assert group.reconciliation_difference == Decimal("-0.01")
    assert not group.reconciled


def test_negative_chronology_is_retained_for_rfm_but_excluded_from_settlement():
    group = group_invoices([row("A", "SI-1", "2026-02-01", "100", "CR-1", "2026-01-31", "100")])[0]
    assert group.rfm_eligible
    assert not group.settlement_eligible
    assert compute_rfm([group])
    assert compute_settlement_metrics([group]) == []


def test_cancelled_excluded_from_settlement_and_rfm():
    groups = group_invoices([row("A", "SI-X", "2026-01-01", "100.00", "", "", "0", "0", "Cancelled")])
    assert compute_rfm(groups) == []
    assert compute_settlement_metrics(groups) == []


def test_normalization_and_critic_mcs_priority():
    groups = group_invoices(
        [
            row("A", "SI-1", "2026-01-01", "100.00", "CR-1", "2026-01-10", "100.00"),
            row("A", "SI-2", "2026-02-01", "100.00", "CR-2", "2026-02-05", "100.00"),
            row("B", "SI-3", "2026-01-01", "50.00", "CR-3", "2026-04-01", "50.00"),
            row("C", "SI-4", "2026-03-01", "75.00", "CR-4", "2026-03-20", "75.00"),
        ]
    )
    assert normalize({"a": 1, "b": 3}, benefit=True)["b"] == 1
    assert normalize({"a": 1, "b": 3}, benefit=False)["a"] == 1
    weights = critic_weights(pd.DataFrame({"rfm": [1, 0.5, 0], "settlement": [0, 0.5, 1]}))
    assert round(sum(weights.values()), 6) == 1
    priorities, weights = compute_priorities(compute_rfm(groups), compute_settlement_metrics(groups))
    assert priorities
    assert priorities[0].priority_rank == 1
    assert set(weights) == {"rfm", "settlement"}
    assert all(abs(item.rfm_contribution + item.settlement_contribution - item.final_priority_score) < 1e-12 for item in priorities)


def test_tie_preserving_priority_groups_keep_boundaries_together():
    groups = assign_priority_groups([("A", 1.0), ("B", 1.0), ("C", 0.5), ("D", 0.1)])
    assert groups["A"] == groups["B"] == "High"


def test_priority_groups_use_account_thirds_and_preserve_both_boundary_ties():
    normal = assign_priority_groups([(letter, float(7-index)) for index, letter in enumerate("ABCDEF", start=1)])
    assert [normal[letter] for letter in "ABCDEF"] == ["High", "High", "Medium", "Medium", "Low", "Low"]
    first_tie = assign_priority_groups([("A", 6), ("B", 5), ("C", 5), ("D", 3), ("E", 2), ("F", 1)])
    assert first_tie["B"] == first_tie["C"] == "High"
    second_tie = assign_priority_groups([("A", 6), ("B", 5), ("C", 4), ("D", 3), ("E", 3), ("F", 1)])
    assert second_tie["D"] == second_tie["E"] == "Medium"
    assert assign_priority_groups([("A", 2), ("B", 1)]) == {"A": "High", "B": "Medium"}


def test_rfm_account_percentiles_preserve_ties_and_direction():
    groups = group_invoices([
        row("A", "1", "2026-12-21", "10", "1", "2026-12-22", "10"),
        row("B", "2", "2026-09-22", "20", "2", "2026-09-23", "20"),
        row("C", "3", "2026-09-22", "20", "3", "2026-09-24", "20"),
        row("D", "4", "2026-01-01", "40", "4", "2026-01-03", "40"),
    ])
    results = {item.account: item for item in compute_rfm(groups, pd.Timestamp("2026-12-31"))}
    assert results["A"].recency_score > results["D"].recency_score
    assert results["B"].recency_score == results["C"].recency_score
    assert results["B"].monetary_score == results["C"].monetary_score


def test_all_equal_priority_scores_remain_one_tied_group():
    groups = assign_priority_groups([("A", 0.5), ("B", 0.5), ("C", 0.5)])
    assert set(groups.values()) == {"Medium"}


def test_settlement_cutoff_excludes_future_collection_evidence():
    group = group_invoices([row("A", "SI-1", "2026-01-01", "100", "CR-1", "2026-03-01", "100")])[0]
    assert compute_settlement_metrics([group], pd.Timestamp("2026-02-01")) == []
    result = compute_settlement_metrics([group], pd.Timestamp("2026-03-01"))[0]
    assert result.settlement_invoice_count == 1
    assert result.average_settlement_days == 59


def test_sensitivity_and_backtest_are_reproducible():
    groups = group_invoices(
        [
            row("A", "SI-1", "2026-01-01", "100.00", "CR-1", "2026-01-10", "100.00"),
            row("B", "SI-2", "2026-01-01", "50.00", "CR-2", "2026-04-01", "50.00"),
            row("C", "SI-3", "2026-03-01", "75.00", "CR-3", "2026-03-20", "75.00"),
        ]
    )
    priorities, weights = compute_priorities(compute_rfm(groups), compute_settlement_metrics(groups))
    sensitivity = run_sensitivity(priorities, weights, 0.10, 100, 42)
    assert sensitivity.iterations == 100
    assert len(sensitivity.scenarios) == 300
    assert all(abs(row["rfm_weight"] + row["settlement_weight"] - 1) < 1e-12 for row in sensitivity.scenarios)
    assert all({"actual_rfm_weight", "actual_settlement_weight", "rank_change", "group_changed"} <= row.keys() for row in sensitivity.scenarios)
    assert 0 <= sensitivity.group_movement_rate <= 1
    repeated = run_sensitivity(priorities, weights, 0.10, 100, 42)
    assert sensitivity.scenarios == repeated.scenarios
    all_levels = [run_sensitivity(priorities, weights, level, 100, 42) for level in (0.10, 0.20, 0.30, 0.40)]
    assert sum(item.iterations for item in all_levels) == 400
    backtest = top_decile_backtest(priorities, groups, repetitions=10, random_seed=42)
    assert backtest.lift_over_random >= 0


def test_backtest_denominator_excludes_completely_new_future_accounts():
    priorities = [
        AccountPriority(account, 4, 10, 1, 1, .5, .5, 1, rank, group)
        for account, rank, group in (("A", 1, "High"), ("B", 2, "Medium"), ("C", 3, "Low"))
    ]
    future = group_invoices([
        row("A", "F-1", "2027-01-01", "100", "CR-1", "2027-01-02", "100"),
        row("NEW", "F-2", "2027-01-01", "10000", "CR-2", "2027-01-02", "10000"),
    ])
    result = top_decile_backtest(priorities, future, repetitions=20, random_seed=42)
    assert result.top_decile_capture == 1
    assert result.eligible_account_count == 3
    assert result.selected_account_count == 1
