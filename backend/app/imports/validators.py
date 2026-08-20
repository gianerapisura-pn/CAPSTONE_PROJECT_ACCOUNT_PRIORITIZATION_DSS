from __future__ import annotations

import hashlib
from io import BytesIO
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import BinaryIO

import pandas as pd

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
    renamed = {column: canonicalize_column(column) for column in frame.columns}
    canonical = frame.rename(columns=renamed)
    missing = [column for column in REQUIRED_COLUMNS if column not in canonical.columns]
    if missing:
        issues.append(ValidationIssue(None, None, "error", f"{sheet_name}: missing required columns: {', '.join(missing)}"))
        return None, issues
    canonical = canonical.loc[:, list(REQUIRED_COLUMNS)].copy()
    canonical["source_sheet"] = sheet_name
    canonical["source_row_number"] = range(2, len(canonical) + 2)
    return canonical, issues


def parse_source_file(file_name: str, content: bytes) -> ParsedWorkbook:
    suffix = Path(file_name).suffix.lower()
    issues: list[ValidationIssue] = []
    frames: dict[str, pd.DataFrame] = {}
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
        issues.append(ValidationIssue(None, None, "error", "Only .csv and .xlsx files are supported."))
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
        status = " ".join(str(row["PAYMENT STATUS"]).strip().lower().split())
        is_cancelled = status == "cancelled"
        if not is_cancelled and str(row["CUSTOMER NAME"]).strip() == "":
            issues.append(ValidationIssue(row_number, "CUSTOMER NAME", "error", "Blank or unidentifiable customer."))
        if not is_cancelled and pd.isna(pd.to_datetime(row["SI DATE"], errors="coerce")):
            issues.append(ValidationIssue(row_number, "SI DATE", "error", "Invalid SI date."))
        if parse_decimal(row["SI AMOUNT"]) is None and not is_cancelled:
            issues.append(ValidationIssue(row_number, "SI AMOUNT", "error", "Invalid SI amount."))
        for column in (() if is_cancelled else ("CR AMOUNT", "EWT")):
            if str(row[column]).strip() and parse_decimal(row[column]) is None:
                issues.append(ValidationIssue(row_number, column, "error", f"Invalid {column}."))
        cr_date = pd.to_datetime(row["CR DATE"], errors="coerce")
        si_date = pd.to_datetime(row["SI DATE"], errors="coerce")
        if not is_cancelled and str(row["CR DATE"]).strip() and pd.isna(cr_date):
            issues.append(ValidationIssue(row_number, "CR DATE", "error", "Invalid CR date."))
        if not is_cancelled and not pd.isna(cr_date) and not pd.isna(si_date) and cr_date < si_date:
            issues.append(ValidationIssue(row_number, "CR DATE", "warning", "Collection date is earlier than SI date."))
    return issues
