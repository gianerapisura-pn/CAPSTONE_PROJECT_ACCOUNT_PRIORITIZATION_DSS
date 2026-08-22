from __future__ import annotations

import hashlib
from io import BytesIO
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from app.etl.status import standardize_payment_status

REQUIRED_COLUMNS = (
    "CUSTOMER NAME",
    "SI NO.",
    "SI DATE",
    "SI AMOUNT",
    "CR NO.",
    "CR DATE",
    "CR AMOUNT",
    "EWT",
    "PAYMENT MODE",
    "PAYMENT STATUS",
)


@dataclass(frozen=True)
class ValidationIssue:
    row_number: int | None
    column: str | None
    severity: str
    message: str
    issue_type: str = "validation"
    source_sheet: str | None = None


@dataclass(frozen=True)
class ParsedWorkbook:
    frames: dict[str, pd.DataFrame]
    issues: list[ValidationIssue]
    file_hash: str


def canonicalize_column(name: object) -> str:
    return " ".join(str(name).strip().upper().split())


def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonicalize_frame(frame: pd.DataFrame, sheet_name: str) -> tuple[pd.DataFrame | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    if frame.dropna(how="all").empty:
        return None, issues
    normalized = [canonicalize_column(column) for column in frame.columns]
    duplicates = sorted({column for column in normalized if normalized.count(column) > 1})
    if duplicates:
        issues.append(ValidationIssue(
            None, None, "error", f"{sheet_name}: duplicate canonical columns: {', '.join(duplicates)}",
            "duplicate_column", sheet_name,
        ))
        return None, issues
    renamed = dict(zip(frame.columns, normalized, strict=True))
    canonical = frame.rename(columns=renamed)
    missing = [column for column in REQUIRED_COLUMNS if column not in canonical.columns]
    if missing:
        issues.append(ValidationIssue(
            None, None, "error", f"{sheet_name}: missing required columns: {', '.join(missing)}",
            "missing_column", sheet_name,
        ))
        return None, issues
    canonical = canonical.loc[:, list(REQUIRED_COLUMNS)].copy()
    canonical["source_sheet"] = sheet_name
    canonical["source_row_number"] = range(2, len(canonical) + 2)
    return canonical, issues


def parse_source_file(file_name: str, content: bytes) -> ParsedWorkbook:
    suffix = Path(file_name).suffix.lower()
    issues: list[ValidationIssue] = []
    frames: dict[str, pd.DataFrame] = {}
    try:
        if suffix == ".csv":
            frame = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
            canonical, sheet_issues = _canonicalize_frame(frame, "CSV")
            issues.extend(sheet_issues)
            if canonical is not None:
                frames["CSV"] = canonical
        elif suffix == ".xlsx":
            workbook = pd.read_excel(BytesIO(content), sheet_name=None, dtype=str, keep_default_na=False)
            for sheet_name, frame in workbook.items():
                canonical, sheet_issues = _canonicalize_frame(frame, sheet_name)
                issues.extend(sheet_issues)
                if canonical is not None:
                    frames[sheet_name] = canonical
        else:
            issues.append(ValidationIssue(None, None, "error", "Only .csv and .xlsx files are supported.", "file_type"))
    except (ValueError, UnicodeError, OSError) as exc:
        issues.append(ValidationIssue(None, None, "error", f"The source file could not be parsed: {exc}", "file_parse"))
    if not frames and not any(issue.severity == "error" for issue in issues):
        issues.append(ValidationIssue(None, None, "error", "No non-empty worksheet or table was found."))
    return ParsedWorkbook(frames=frames, issues=issues, file_hash=compute_file_hash(content))


def parse_decimal(value: object) -> Decimal | None:
    text = str(value).strip()
    if text == "":
        return None
    cleaned = text.replace("PHP", "").replace("₱", "").replace(",", "").strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def validate_rows(frame: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for idx, row in frame.iterrows():
        row_number = int(row["source_row_number"])
        sheet = str(row.get("source_sheet", "")) or None
        status = standardize_payment_status(row["PAYMENT STATUS"])
        is_cancelled = status == "Cancelled"

        def add(column: str | None, severity: str, message: str, issue_type: str) -> None:
            issues.append(ValidationIssue(row_number, column, severity, message, issue_type, sheet))

        if status not in {"Fully Paid", "Cancelled", "Partially Paid"}:
            add("PAYMENT STATUS", "warning", "Unknown payment status requires review.", "unknown_payment_status")
        if not is_cancelled and str(row["CUSTOMER NAME"]).strip() == "":
            add("CUSTOMER NAME", "error", "Blank or unidentifiable customer.", "missing_customer")
        if not is_cancelled and str(row["SI NO."]).strip() == "":
            add("SI NO.", "error", "Blank Sales Invoice number.", "missing_si_number")
        if not is_cancelled and pd.isna(pd.to_datetime(row["SI DATE"], errors="coerce")):
            add("SI DATE", "error", "Invalid SI date.", "invalid_si_date")
        si_amount = parse_decimal(row["SI AMOUNT"])
        if not is_cancelled and (si_amount is None or si_amount <= 0):
            add("SI AMOUNT", "error", "SI amount must be a valid positive amount.", "invalid_si_amount")
        for column in (() if is_cancelled else ("CR AMOUNT", "EWT")):
            if str(row[column]).strip() and parse_decimal(row[column]) is None:
                add(column, "error", f"Invalid {column}.", "invalid_money")
        cr_date = pd.to_datetime(row["CR DATE"], errors="coerce")
        si_date = pd.to_datetime(row["SI DATE"], errors="coerce")
        if not is_cancelled and str(row["CR DATE"]).strip() and pd.isna(cr_date):
            add("CR DATE", "error", "Invalid CR date.", "invalid_cr_date")
        if not is_cancelled and not pd.isna(cr_date) and not pd.isna(si_date) and cr_date < si_date:
            add("CR DATE", "warning", "Collection date is earlier than SI date.", "negative_chronology")
    return issues
