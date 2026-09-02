from __future__ import annotations

from pathlib import Path

from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.imports.validators import parse_source_file, validate_rows
from app.services.analytics_runner import run_account_prioritization


def test_future_year_and_new_account_import_pipeline():
    content = Path("../sample_data/test_fixtures/future_valid.csv").read_bytes()
    parsed = parse_source_file("future_valid.csv", content)
    assert not parsed.issues
    frame = parsed.frames["CSV"]
    assert not [issue for issue in validate_rows(frame) if issue.severity == "error"]
    rows = dataframe_to_source_rows(frame, import_batch_id=parsed.file_hash[:12])
    groups = group_invoices(rows)
    assert any(group.si_date.year == 2030 for group in groups)
    assert any(group.standardized_account_name == "New Future Account" for group in groups)
    result = run_account_prioritization(groups)
    assert result.status == "successful"


def test_missing_columns_rejected():
    parsed = parse_source_file("bad.csv", b"ACCOUNT NAMES,SI NO.\nAcme,1\n")
    assert any(issue.severity == "error" for issue in parsed.issues)
