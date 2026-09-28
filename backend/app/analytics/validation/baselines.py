from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from app.etl.invoices import InvoiceGroup


def annual_business_baselines(
    invoice_groups: list[InvoiceGroup],
    analysis_reference_date: pd.Timestamp,
    eligible_accounts: set[str] | None = None,
) -> list[dict]:
    reference = pd.Timestamp(analysis_reference_date)
    valid = [
        group for group in invoice_groups
        if group.rfm_eligible
        and group.si_date <= reference
        and (eligible_accounts is None or group.standardized_account_name in eligible_accounts)
    ]
    if not valid:
        return []
    sales: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    accounts: dict[int, set[str]] = defaultdict(set)
    invoices: dict[int, int] = defaultdict(int)
    for group in valid:
        sales[group.si_date.year] += group.si_amount
        accounts[group.si_date.year].add(group.standardized_account_name)
        invoices[group.si_date.year] += 1
    results: list[dict] = []
    previous_sales: Decimal | None = None
    previous_accounts: int | None = None
    for year in range(min(sales), reference.year + 1):
        year_sales = sales[year]
        account_count = len(accounts[year])
        is_partial = year == reference.year and (reference.month, reference.day) < (12, 31)
        results.append({
            "year": year,
            "valid_si_sales": float(year_sales),
            "valid_invoice_count": invoices[year],
            "transacting_account_count": account_count,
            "sales_decline_rate": (
                None if previous_sales in (None, 0) or is_partial
                else float((previous_sales - year_sales) / previous_sales)
            ),
            "transacting_account_decline_rate": (
                None if previous_accounts in (None, 0) or is_partial
                else (previous_accounts - account_count) / previous_accounts
            ),
            "is_partial_year": is_partial,
            "data_complete_through": reference.date().isoformat(),
        })
        previous_sales, previous_accounts = year_sales, account_count
    return results