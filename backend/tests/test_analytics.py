from __future__ import annotations

from decimal import Decimal

import pandas as pd

from app.analytics.descriptive.rfm import compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.prescriptive.scoring import assign_priority_groups, compute_priorities, critic_weights, normalize
from app.analytics.validation.backtest import top_decile_backtest
from app.analytics.validation.sensitivity import run_sensitivity
from app.etl.invoices import SourceRow, group_invoices


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


def test_tie_preserving_priority_groups_keep_boundaries_together():
    groups = assign_priority_groups([("A", 1.0), ("B", 1.0), ("C", 0.5), ("D", 0.1)])
    assert groups["A"] == groups["B"] == "High"


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
    assert 0 <= sensitivity.group_movement_rate <= 1
    backtest = top_decile_backtest(priorities, groups, repetitions=10, random_seed=42)
    assert backtest.lift_over_random >= 0
