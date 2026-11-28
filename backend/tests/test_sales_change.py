from copy import deepcopy
from decimal import Decimal

import pandas as pd
import pytest

from app.analytics.validation.sales_change import annual_account_sales, sales_change_report
from app.analytics.validation.baselines import annual_business_baselines
from app.etl.invoices import InvoiceGroup


def invoice(name, year, value, identity=None, status="Fully Paid"):
    return InvoiceGroup(identity or f"{name}-{year}", name, "SI", pd.Timestamp(f"{year}-01-01"),
                        Decimal(value), status)


def report(groups, reference="2031-12-31", context=None):
    reference = pd.Timestamp(reference)
    return sales_change_report(annual_account_sales(groups, reference),
        annual_business_baselines(groups, reference, set()), context or [])


def test_exact_bridge_group_membership_and_union_excludes_neither_year():
    result = report([invoice("BOTH", 2030, "12.34"), invoice("BOTH", 2031, "9.99"),
                     invoice("PREVIOUS", 2030, "20.01"), invoice("CURRENT", 2031, "7.00"),
                     invoice("OLDER", 2029, "999")])["comparison"]
    assert result["account_count"] == 3
    assert [r["account_count"] for r in result["groups"]] == [1, 1, 1]
    assert [Decimal(r["change"]) for r in result["groups"]] == [Decimal("-2.35"), Decimal("-20.01"), Decimal("7")]
    assert Decimal(result["change"]) == Decimal("-15.36")
    assert sum(Decimal(r["change"]) for r in result["accounts"]) == Decimal(result["change"])


def test_partial_year_not_compared_and_future_si_not_included():
    result = report([invoice("A", 2030, "10"), invoice("A", 2031, "20"),
                     invoice("A", 2032, "30")], "2031-06-30")
    assert result["comparison"] is None
    assert result["available_periods"] == []


def test_zero_sales_year_is_available_and_percentage_is_undefined():
    result = report([invoice("OLD", 2029, "10"), invoice("NEW", 2031, "3")])["comparison"]
    assert result["previous_year"] == 2030
    assert result["change_pct"] is None
    assert result["accounts"][0]["previous_share_pct"] is None


def test_cancelled_conflicting_zero_and_invalid_sis_do_not_contribute():
    conflict = invoice("CONFLICT", 2031, "999"); conflict.conflicting_invoice = True
    result = report([invoice("A", 2030, "10"), invoice("A", 2031, "20"), conflict,
                     invoice("CANCELLED", 2031, "999", status="Cancelled"),
                     invoice("ZERO", 2031, "0")])["comparison"]
    assert result["account_count"] == 1
    assert Decimal(result["current_total"]) == 20


def test_repeated_logical_invoice_fails_instead_of_inflating_sales():
    row = invoice("A", 2030, "10")
    with pytest.raises(ValueError, match="Duplicate logical"):
        annual_account_sales([row, deepcopy(row)], pd.Timestamp("2031-12-31"))


def test_current_closed_unranked_account_remains_in_historical_sales():
    result = report([invoice("CLOSED", 2030, "10"), invoice("CURRENT", 2031, "20")], context=[
        {"account": "CLOSED", "account_key": "closed", "is_ranked": False},
        {"account": "CURRENT", "account_key": "current", "is_ranked": True, "priority_rank": 1}
    ])["comparison"]
    closed = next(r for r in result["accounts"] if r["account"] == "CLOSED")
    assert closed["account_key"] == "closed"
    assert closed["ranking_note"]
    assert Decimal(result["previous_total"]) == 10


@pytest.mark.parametrize("years", [(2030, 2030), (2029, 2031), (2031, 2032), (None, 2031)])
def test_invalid_or_incomplete_pair_is_rejected(years):
    groups = [invoice("A", 2030, "10"), invoice("A", 2031, "20")]
    ref = pd.Timestamp("2031-12-31")
    with pytest.raises(ValueError, match="consecutive complete"):
        sales_change_report(annual_account_sales(groups, ref), annual_business_baselines(groups, ref, set()), [], *years)


def test_mismatched_publication_summary_fails_closed():
    annual = [{"year": 2030, "account": "A", "sales": "10.00", "invoice_count": 1}]
    baselines = [{"year": y, "period_status": "Complete year", "all_recorded_sales": "100.00"} for y in (2030, 2031)]
    with pytest.raises(ValueError, match="reconcile"):
        sales_change_report(annual, baselines, [])


def test_duplicate_account_year_rejected():
    row = {"year": 2030, "account": "A", "sales": "10.00", "invoice_count": 1}
    baselines = [{"year": y, "period_status": "Complete year", "all_recorded_sales": 10} for y in (2030, 2031)]
    with pytest.raises(ValueError, match="Duplicate account-year"):
        sales_change_report([row, row], baselines, [])
