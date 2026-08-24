from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.analytics.predictive.cart import HIGHER_RISK, TARGET_COLUMN, build_cutoff_dataset
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.etl.invoices import InvoiceGroup


def annual_business_baselines(invoice_groups: list[InvoiceGroup]) -> list[dict]:
    """Compute annual sales/account context from unique valid logical invoices."""
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
    for year in sorted(sales):
        year_sales = sales[year]
        account_count = len(accounts[year])
        is_partial = year == latest_date.year and (latest_date.month, latest_date.day) < (12, 31)
        decline = (
            None
            if previous_sales in (None, 0) or is_partial
            else float((previous_sales - year_sales) / previous_sales)
        )
        account_decline = (
            None
            if previous_accounts in (None, 0) or is_partial
            else (previous_accounts - account_count) / previous_accounts
        )
        results.append({
            "year": year,
            "valid_si_sales": float(year_sales),
            "valid_invoice_count": sum(group.si_date.year == year for group in valid),
            "active_account_count": account_count,
            "sales_decline_rate": decline,
            "active_account_decline_rate": account_decline,
            "is_partial_year": is_partial,
        })
        previous_sales, previous_accounts = year_sales, account_count
    return results


def selected_horizon_no_transaction_rate(
    invoice_groups: list[InvoiceGroup],
    selected_horizon_months: int,
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> dict:
    if selected_horizon_months not in config.candidate_outcome_windows:
        return {
            "status": "unavailable",
            "selected_horizon_months": None,
            "eligible_observations": 0,
            "no_transaction_observations": 0,
            "rate": None,
        }
    frames = [
        build_cutoff_dataset(
            invoice_groups,
            cutoff,
            config.predictive_lookback_months,
            selected_horizon_months,
            config.recent_transaction_months,
        )
        for cutoff in config.cart_cutoffs
    ]
    frames = [frame for frame in frames if not frame.empty]
    eligible = sum(len(frame) for frame in frames)
    no_transaction = sum(
        int((frame[TARGET_COLUMN] == HIGHER_RISK).sum()) for frame in frames
    )
    return {
        "status": "available" if eligible else "unavailable",
        "selected_horizon_months": selected_horizon_months,
        "eligible_observations": eligible,
        "no_transaction_observations": no_transaction,
        "rate": no_transaction / eligible if eligible else None,
    }
