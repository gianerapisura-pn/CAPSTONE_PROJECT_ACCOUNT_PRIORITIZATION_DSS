from decimal import Decimal
import pandas as pd
import pytest
from app.analytics.descriptive.rfm import _quantile_scores, compute_rfm
from app.analytics.descriptive.settlement import compute_settlement_metrics
from app.analytics.prescriptive.scoring import assign_priority_groups, compute_priorities
from app.analytics.validation.backtest import run_historical_backtest, top_decile_backtest
from app.analytics.validation.sensitivity import run_leave_one_out_influence, run_sensitivity
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.etl.invoices import InvoiceGroup, SourceRow, group_invoices
from app.services.analytics_runner import run_account_prioritization, validate_analysis_reference


def group(account, si, si_date, amount, cr_date=None, settled=True):
    date = pd.Timestamp(si_date)
    final = pd.Timestamp(cr_date) if cr_date else None
    return InvoiceGroup(
        invoice_group_id=account + si, standardized_account_name=account,
        si_no=si, si_date=date, si_amount=Decimal(str(amount)),
        payment_status="Fully Paid", final_cr_date=final,
        total_cr_amount=Decimal(str(amount)) if settled else Decimal("0"),
        reconciliation_amount=Decimal(str(amount)) if settled else Decimal("0"),
        reconciliation_difference=Decimal("0") if settled else Decimal(str(amount)),
        reconciled=settled,
    )


def test_rfm_uses_explicit_reference_and_linear_quintiles_with_ties():
    groups = [
        group("A", "1", "2026-01-01", 100, "2026-01-10"),
        group("B", "2", "2026-02-01", 200, "2026-02-10"),
        group("C", "3", "2026-02-01", 200, "2026-02-10"),
        group("D", "4", "2026-03-01", 400, "2026-03-10"),
        group("E", "5", "2026-04-01", 500, "2026-04-10"),
    ]
    result = compute_rfm(groups, pd.Timestamp("2026-09-21"))
    assert {x.account for x in result} == {"A", "B", "C", "D", "E"}
    assert next(x for x in result if x.account == "A").recency_days == 263
    assert next(x for x in result if x.account == "B").r_score == next(
        x for x in result if x.account == "C").r_score
    assert all(len(x.rfm_code) == 3 for x in result)


def test_quantile_constant_component_gets_neutral_score():
    assert _quantile_scores({"A": 7, "B": 7}, True) == {"A": 3, "B": 3}


def test_logical_invoice_frequency_is_not_collection_row_count():
    rows = [
        SourceRow("A", "A", "SI-1", pd.Timestamp("2026-01-01"), Decimal("100"),
                  "CR-1", pd.Timestamp("2026-01-10"), Decimal("60"), None, "Cash",
                  "Fully Paid", "Fully Paid", False),
        SourceRow("A", "A", "SI-1", pd.Timestamp("2026-01-01"), Decimal("100"),
                  "CR-2", pd.Timestamp("2026-01-11"), Decimal("40"), None, "Cash",
                  "Fully Paid", "Fully Paid", False),
    ]
    groups = group_invoices(rows)
    metric = compute_rfm(groups, pd.Timestamp("2026-09-21"))[0]
    assert len(groups) == 1
    assert metric.frequency == 1
    assert metric.monetary == Decimal("100")


def test_reconciliation_uses_cent_tolerance():
    rows = [SourceRow(
        "A", "A", "SI-1", pd.Timestamp("2026-01-01"), Decimal("100.00"),
        "CR-1", pd.Timestamp("2026-01-10"), Decimal("98.99"), Decimal("1.00"),
        "Cash", "Fully Paid", "Fully Paid", False)]
    item = group_invoices(rows)[0]
    assert item.reconciliation_difference == Decimal("0.01")
    assert item.reconciled is True


def test_settlement_excludes_collection_evidence_after_reference():
    groups = [group("A", "1", "2026-01-01", 100, "2026-10-01")]
    assert compute_settlement_metrics(groups, pd.Timestamp("2026-09-21")) == []
    assert compute_settlement_metrics(groups, pd.Timestamp("2026-10-01"))[0].settlement_invoice_count == 1


def test_reference_must_cover_latest_si_and_final_cr():
    groups = [group("A", "1", "2026-01-01", 100, "2026-09-20")]
    with pytest.raises(ValueError, match="cannot precede"):
        validate_analysis_reference(groups, pd.Timestamp("2026-09-19"))
    validate_analysis_reference(groups, pd.Timestamp("2026-09-21"))

def test_b2b_eligibility_excludes_preserved_personal_history():
    groups = [
        group("BUSINESS", "1", "2025-01-01", 100, "2025-01-10"),
        group("PERSON", "2", "2025-01-01", 100, "2025-01-10"),
    ]
    result = run_account_prioritization(
        groups, pd.Timestamp("2026-09-21"), {"BUSINESS"})
    assert [x["account"] for x in result.rfm] == ["BUSINESS"]
    assert result.context_metrics["historical_account_count"] == 2


def test_priority_grouping_is_tie_safe_and_balanced_for_84_distinct_scores():
    groups = assign_priority_groups([(str(i), float(84 - i)) for i in range(84)])
    assert list(groups.values()).count("High") == 28
    assert list(groups.values()).count("Medium") == 28
    assert list(groups.values()).count("Low") == 28
    tied = assign_priority_groups([("A", 1.0), ("B", 1.0), ("C", 0.0)])
    assert tied["A"] == tied["B"]


def test_sensitivity_has_100_scenarios_and_separate_loo():
    groups = [
        group(str(i), str(i), "2025-01-01", 100 + i * 10,
              f"2025-01-{10 + i:02d}") for i in range(12)
    ]
    rfm = compute_rfm(groups, pd.Timestamp("2026-09-21"))
    settlement = compute_settlement_metrics(groups, pd.Timestamp("2026-09-21"))
    priorities, weights = compute_priorities(rfm, settlement)
    summary = run_sensitivity(priorities, weights, .4, 100, 42)
    assert summary.iterations == 100
    assert len(summary.scenarios) == 100 * len(priorities)
    influence = run_leave_one_out_influence(rfm, settlement, priorities, weights)
    assert len(influence) == len(priorities)


def test_backtest_uses_seven_cutoffs_and_exact_k_over_n_expectation():
    from app.analytics.prescriptive.scoring import AccountPriority
    priorities = [
        AccountPriority(str(i), 3, i, i + 1, Decimal(100 + i), i + 1,
                        .5, .5, .5, .5, .1, .1, .1, .1,
                        float(20 - i), i + 1, "High" if i < 7 else "Medium")
        for i in range(20)
    ]
    result = top_decile_backtest(priorities, [], "2020-12-31", "2021-12-31")
    assert result.selected_account_count == 2
    assert result.expected_random_capture == pytest.approx(2 / 20)
    summary = run_historical_backtest([], DEFAULT_ANALYTICS_CONFIG)
    assert summary.cutoff_count == 7
    assert [x["cutoff_date"] for x in summary.cutoffs] == list(
        DEFAULT_ANALYTICS_CONFIG.backtest_cutoffs)
