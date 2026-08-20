from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from app.etl.invoices import InvoiceGroup


def annual_business_baselines(invoice_groups: list[InvoiceGroup], inactivity_months: int = 12) -> list[dict]:
    """Compute dynamic sales and account baselines from unique valid invoices."""
    valid = [group for group in invoice_groups if group.rfm_eligible]
    if not valid:
        return []
    latest_date = max(group.si_date for group in valid)
    sales: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    accounts: dict[int, set[str]] = defaultdict(set)
    for group in valid:
        sales[group.si_date.year] += group.si_amount
        accounts[group.si_date.year].add(group.standardized_account_name)
    results: list[dict] = []
    previous_sales: Decimal | None = None
    previous_accounts: int | None = None
    all_accounts = {group.standardized_account_name for group in valid}
    for year in sorted(sales):
        year_sales = sales[year]
        account_count = len(accounts[year])
        is_partial = year == latest_date.year and (latest_date.month, latest_date.day) < (12, 31)
        decline = None if previous_sales in (None, 0) or is_partial else float((previous_sales - year_sales) / previous_sales)
        account_decline = None if previous_accounts in (None, 0) or is_partial else (previous_accounts - account_count) / previous_accounts
        year_end = latest_date if year == latest_date.year else pd.Timestamp(year=year, month=12, day=31)
        inactivity_cutoff = year_end - pd.DateOffset(months=inactivity_months)
        recently_active = {g.standardized_account_name for g in valid if g.si_date.year <= year and inactivity_cutoff < g.si_date <= year_end}
        results.append({
            "year": year, "valid_si_sales": float(year_sales),
            "valid_invoice_count": sum(g.si_date.year == year for g in valid),
            "active_account_count": account_count, "sales_decline_rate": decline,
            "active_account_decline_rate": account_decline,
            "inactivity_rate": (len(all_accounts - recently_active) / len(all_accounts)) if all_accounts else 0.0,
            "is_partial_year": is_partial,
        })
        previous_sales, previous_accounts = year_sales, account_count
    return results
