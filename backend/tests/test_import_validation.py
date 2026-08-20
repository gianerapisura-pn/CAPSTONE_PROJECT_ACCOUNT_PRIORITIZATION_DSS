from io import BytesIO

import pandas as pd

from app.imports.validators import REQUIRED_COLUMNS, parse_source_file, validate_rows


def valid_row(**changes):
    row = {"CUSTOMER NAME":"Future Co","SI NO.":"001","SI DATE":"2035-01-01","SI AMOUNT":"100.00",
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
    cancelled=pd.DataFrame([valid_row(**{"CUSTOMER NAME":"","SI DATE":"","SI AMOUNT":"","PAYMENT STATUS":"Cancelled","CR DATE":"","CR AMOUNT":"","EWT":""})])
    cancelled["source_sheet"]="CSV";cancelled["source_row_number"]=2
    assert not [issue for issue in validate_rows(cancelled) if issue.severity=="error"]
    bad=pd.DataFrame([valid_row(**{"SI DATE":"not-a-date","SI AMOUNT":"oops"})])
    bad["source_sheet"]="CSV";bad["source_row_number"]=2
    assert len([issue for issue in validate_rows(bad) if issue.severity=="error"])==2


def test_column_case_and_whitespace_are_canonicalized():
    frame=pd.DataFrame([valid_row()]);frame.columns=[f" {column.lower()} " for column in frame.columns]
    parsed=parse_source_file("source.csv",frame.to_csv(index=False).encode())
    assert tuple(parsed.frames["CSV"].columns[:len(REQUIRED_COLUMNS)])==REQUIRED_COLUMNS
