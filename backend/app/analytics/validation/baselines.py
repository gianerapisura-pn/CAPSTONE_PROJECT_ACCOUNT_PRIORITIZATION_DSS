from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from app.etl.invoices import InvoiceGroup


def annual_business_baselines(
    invoice_groups: list[InvoiceGroup],
    analysis_reference_date: pd.Timestamp,
    eligible_accounts: set[str],
) -> list[dict]:
    """Separate source-wide valid SI history from the verified-B2B subset."""
    reference = pd.Timestamp(analysis_reference_date)
    all_valid = [
        group for group in invoice_groups
        if group.rfm_eligible and group.si_date <= reference
    ]
    if not all_valid:
        return []
    all_sales: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    all_invoices: dict[int, int] = defaultdict(int)
    b2b_sales: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    b2b_invoices: dict[int, int] = defaultdict(int)
    b2b_accounts: dict[int, set[str]] = defaultdict(set)
    for group in all_valid:
        year = group.si_date.year
        all_sales[year] += group.si_amount
        all_invoices[year] += 1
        if group.standardized_account_name in eligible_accounts:
            b2b_sales[year] += group.si_amount
            b2b_invoices[year] += 1
            b2b_accounts[year].add(group.standardized_account_name)
    results: list[dict] = []
    previous_all_sales: Decimal | None = None
    previous_b2b_accounts: int | None = None
    for year in range(min(all_sales), reference.year + 1):
        complete = year < reference.year or (reference.month, reference.day) == (12, 31)
        year_all_sales = all_sales[year]
        year_b2b_accounts = len(b2b_accounts[year])
        results.append({
            "year": year,
            "period_status": "Complete year" if complete else f"YTD through {reference.date().isoformat()}",
            "all_valid_invoice_count": all_invoices[year],
            "all_recorded_sales": float(year_all_sales),
            "b2b_valid_invoice_count": b2b_invoices[year],
            "b2b_recorded_sales": float(b2b_sales[year]),
            "b2b_transacting_account_count": year_b2b_accounts,
            "all_sales_yoy_change_pct": (
                float((year_all_sales - previous_all_sales) / previous_all_sales * 100)
                if complete and previous_all_sales not in (None, 0) else None
            ),
            "b2b_transacting_accounts_yoy_change_pct": (
                (year_b2b_accounts - previous_b2b_accounts) / previous_b2b_accounts * 100
                if complete and previous_b2b_accounts not in (None, 0) else None
            ),
            "data_complete_through": reference.date().isoformat(),
        })
        previous_all_sales = year_all_sales
        previous_b2b_accounts = year_b2b_accounts
    return results