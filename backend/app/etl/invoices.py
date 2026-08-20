from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha1

import pandas as pd

from app.etl.standardization import standardize_account_name
from app.etl.status import standardize_payment_status
from app.imports.validators import parse_decimal


@dataclass
class SourceRow:
    customer_name_raw: str
    standardized_account_name: str
    si_no: str
    si_date: pd.Timestamp
    si_amount: Decimal
    cr_no: str
    cr_date: pd.Timestamp | None
    cr_amount: Decimal
    ewt: Decimal
    payment_mode: str
    payment_status_raw: str
    payment_status: str
    is_cancelled: bool
    import_batch_id: str = "demo"
    source_sheet: str = "CSV"
    source_row_number: int = 0


@dataclass
class InvoiceGroup:
    invoice_group_id: str
    standardized_account_name: str
    si_no: str
    si_date: pd.Timestamp
    si_amount: Decimal
    payment_status: str
    rows: list[SourceRow] = field(default_factory=list)
    final_cr_date: pd.Timestamp | None = None
    total_cr_amount: Decimal = Decimal("0")
    total_ewt: Decimal = Decimal("0")
    reconciliation_amount: Decimal = Decimal("0")
    reconciliation_difference: Decimal = Decimal("0")
    reconciled: bool = False
    review_reason: str | None = None

    @property
    def is_cancelled(self) -> bool:
        return self.payment_status == "Cancelled"

    @property
    def rfm_eligible(self) -> bool:
        return not self.is_cancelled and self.si_date is not pd.NaT and self.si_amount > 0

    @property
    def settlement_eligible(self) -> bool:
        if self.is_cancelled or self.final_cr_date is None or not self.reconciled:
            return False
        return (self.final_cr_date - self.si_date).days >= 0

    @property
    def settlement_days(self) -> int | None:
        if not self.settlement_eligible or self.final_cr_date is None:
            return None
        return int((self.final_cr_date - self.si_date).days)


def dataframe_to_source_rows(frame: pd.DataFrame, import_batch_id: str = "demo") -> list[SourceRow]:
    rows: list[SourceRow] = []
    for _, row in frame.iterrows():
        status = standardize_payment_status(row["PAYMENT STATUS"])
        is_cancelled = status == "Cancelled"
        si_date = pd.to_datetime(row["SI DATE"], errors="coerce")
        cr_date_raw = pd.to_datetime(row["CR DATE"], errors="coerce")
        cr_date = None if pd.isna(cr_date_raw) else cr_date_raw
        rows.append(
            SourceRow(
                customer_name_raw=str(row["CUSTOMER NAME"]).strip(),
                standardized_account_name=standardize_account_name(row["CUSTOMER NAME"]),
                si_no=str(row["SI NO."]).strip(),
                si_date=si_date,
                si_amount=parse_decimal(row["SI AMOUNT"]) or Decimal("0"),
                cr_no=str(row["CR NO."]).strip(),
                cr_date=cr_date,
                cr_amount=parse_decimal(row["CR AMOUNT"]) or Decimal("0"),
                ewt=parse_decimal(row["EWT"]) or Decimal("0"),
                payment_mode=str(row["PAYMENT MODE"]).strip(),
                payment_status_raw=str(row["PAYMENT STATUS"]).strip(),
                payment_status=status,
                is_cancelled=is_cancelled,
                import_batch_id=import_batch_id,
                source_sheet=str(row.get("source_sheet", "CSV")),
                source_row_number=int(row.get("source_row_number", 0)),
            )
        )
    return rows


def invoice_group_key(row: SourceRow) -> str:
    parts = [
        row.import_batch_id,
        row.source_sheet,
        row.standardized_account_name,
        row.si_no,
        str(row.si_date.date() if not pd.isna(row.si_date) else ""),
        str(row.si_amount),
    ]
    return sha1("|".join(parts).encode("utf-8")).hexdigest()


def group_invoices(rows: list[SourceRow], precision: Decimal = Decimal("0.01")) -> list[InvoiceGroup]:
    grouped: dict[str, InvoiceGroup] = {}
    for row in rows:
        key = invoice_group_key(row)
        if key not in grouped:
            grouped[key] = InvoiceGroup(
                invoice_group_id=key,
                standardized_account_name=row.standardized_account_name,
                si_no=row.si_no,
                si_date=row.si_date,
                si_amount=row.si_amount,
                payment_status=row.payment_status,
            )
        grouped[key].rows.append(row)
    for group in grouped.values():
        cr_dates = [row.cr_date for row in group.rows if row.cr_date is not None]
        group.final_cr_date = max(cr_dates) if cr_dates else None
        group.total_cr_amount = sum((row.cr_amount for row in group.rows), Decimal("0"))
        group.total_ewt = sum((row.ewt for row in group.rows), Decimal("0"))
        group.reconciliation_amount = group.total_cr_amount + group.total_ewt
        group.reconciliation_difference = (group.reconciliation_amount - group.si_amount).quantize(precision)
        group.reconciled = abs(group.reconciliation_difference) <= precision
        if group.is_cancelled:
            group.review_reason = "Cancelled; excluded from analytics."
        elif group.payment_status == "Fully Paid" and not group.reconciled:
            group.review_reason = "Fully Paid invoice does not reconcile to SI amount."
        elif group.final_cr_date is not None and (group.final_cr_date - group.si_date).days < 0:
            group.review_reason = "Collection date is earlier than SI date."
    return list(grouped.values())
