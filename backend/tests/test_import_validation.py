from io import BytesIO

import pandas as pd

from app.imports.validators import REQUIRED_COLUMNS, parse_source_file, validate_rows


def valid_row(**changes):
    row = {"ACCOUNT NAMES":"Future Co","SI NO.":"001","SI DATE":"2035-01-01","SI AMOUNT":"100.00",
           "CR NO.":"CR-1","CR DATE":"2035-01-10","CR AMOUNT":"98.00","EWT":"2.00",
           "PAYMENT MODE":"Bank","PAYMENT STATUS":"Fully Paid"}
    row.update(changes)
    return row


def test_valid_xlsx_and_multiple_nonempty_sheets():
    output=BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        pd.DataFrame([valid_row()]).to_excel(writer,sheet_name="2035",index=False)
        pd.DataFrame([valid_row(**{"SI NO.":"002"})]).to_excel(writer,sheet_name="2036",index=False)
        pd.DataFrame().to_excel(writer,sheet_name="Empty",index=False)
    parsed=parse_source_file("future.xlsx",output.getvalue())
    assert set(parsed.frames)=={"2035","2036"}
    assert all("source_row_number" in frame for frame in parsed.frames.values())


def test_cancelled_collection_blanks_are_valid_but_bad_values_fail():
    cancelled=pd.DataFrame([valid_row(**{"ACCOUNT NAMES":"","SI DATE":"","SI AMOUNT":"","PAYMENT STATUS":"Cancelled","CR DATE":"","CR AMOUNT":"","EWT":""})])
    cancelled["source_sheet"]="CSV";cancelled["source_row_number"]=2
    assert not [issue for issue in validate_rows(cancelled) if issue.severity=="error"]
    bad=pd.DataFrame([valid_row(**{"SI DATE":"not-a-date","SI AMOUNT":"oops"})])
    bad["source_sheet"]="CSV";bad["source_row_number"]=2
    assert len([issue for issue in validate_rows(bad) if issue.severity=="error"])==2


def test_column_case_and_whitespace_are_canonicalized():
    frame=pd.DataFrame([valid_row()]);frame.columns=[f" {column.lower()} " for column in frame.columns]
    parsed=parse_source_file("source.csv",frame.to_csv(index=False).encode())
    assert tuple(parsed.frames["CSV"].columns[:len(REQUIRED_COLUMNS)])==REQUIRED_COLUMNS


def test_duplicate_canonical_headers_are_rejected():
    columns = list(REQUIRED_COLUMNS) + [" account names "]
    frame = pd.DataFrame([list(valid_row().values()) + ["Duplicate"]], columns=columns)
    parsed = parse_source_file("duplicate.csv", frame.to_csv(index=False).encode())
    assert not parsed.frames
    assert any(issue.issue_type == "duplicate_column" for issue in parsed.issues)


def test_customer_name_compatibility_alias_maps_to_account_names():
    frame = pd.DataFrame([valid_row()]).rename(columns={"ACCOUNT NAMES": "CUSTOMER NAME"})
    parsed = parse_source_file("legacy.csv", frame.to_csv(index=False).encode())
    assert not parsed.issues
    assert parsed.frames["CSV"].iloc[0]["ACCOUNT NAMES"] == "Future Co"
    assert "CUSTOMER NAME" not in parsed.frames["CSV"]


def test_account_name_and_compatibility_alias_together_are_rejected():
    frame = pd.DataFrame([valid_row()])
    frame["CUSTOMER NAME"] = "Ambiguous Co"
    parsed = parse_source_file("ambiguous.csv", frame.to_csv(index=False).encode())
    assert not parsed.frames
    assert any(issue.issue_type == "ambiguous_column_alias" for issue in parsed.issues)


def test_cancelled_synonyms_and_unknown_status_are_handled_before_required_fields():
    rows = pd.DataFrame([
        valid_row(**{"ACCOUNT NAMES":"", "SI NO.":"", "SI DATE":"", "SI AMOUNT":"", "PAYMENT STATUS":"Voided"}),
        valid_row(**{"PAYMENT STATUS":"Needs Review"}),
        valid_row(**{"PAYMENT STATUS":"Partially Paid"}),
    ])
    rows["source_sheet"] = "CSV"
    rows["source_row_number"] = [2, 3, 4]
    issues = validate_rows(rows)
    assert not [issue for issue in issues if issue.row_number == 2 and issue.severity == "error"]
    assert any(issue.row_number == 3 and issue.issue_type == "unknown_payment_status" for issue in issues)
    assert any(issue.row_number == 4 and issue.issue_type == "unknown_payment_status" for issue in issues)


def test_blank_si_and_invalid_collection_values_are_typed():
    frame = pd.DataFrame([valid_row(**{"SI NO.":"", "CR DATE":"bad", "CR AMOUNT":"bad", "EWT":"bad"})])
    frame["source_sheet"] = "CSV"
    frame["source_row_number"] = 2
    issue_types = {issue.issue_type for issue in validate_rows(frame)}
    assert {"missing_si_number", "invalid_cr_date", "invalid_money"} <= issue_types
