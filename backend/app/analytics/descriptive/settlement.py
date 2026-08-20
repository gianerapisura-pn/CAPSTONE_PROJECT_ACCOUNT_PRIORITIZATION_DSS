from __future__ import annotations

from dataclasses import dataclass

from app.etl.invoices import InvoiceGroup


@dataclass(frozen=True)
class AccountSettlement:
    account: str
    settlement_invoice_count: int
    average_settlement_days: float | None
    final_collection_days_max: int | None


def compute_settlement_metrics(invoice_groups: list[InvoiceGroup]) -> list[AccountSettlement]:
    eligible = [group for group in invoice_groups if group.settlement_eligible]
    accounts = sorted({group.standardized_account_name for group in eligible})
    results: list[AccountSettlement] = []
    for account in accounts:
        days = [group.settlement_days for group in eligible if group.standardized_account_name == account and group.settlement_days is not None]
        if not days:
            continue
        results.append(
            AccountSettlement(
                account=account,
                settlement_invoice_count=len(days),
                average_settlement_days=sum(days) / len(days),
                final_collection_days_max=max(days),
            )
        )
    return results
