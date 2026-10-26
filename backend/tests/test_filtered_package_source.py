"""Read-only checks for the active private source; no model is deserialized."""

from collections import Counter
from hashlib import sha256
import os

import pytest

from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.imports.validators import parse_source_file
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256, read_package_csv, read_package_member, verified_package,
)


PACKAGE = os.getenv("PESLC_FINAL_ANALYTICS_PACKAGE_PATH")


@pytest.mark.skipif(not PACKAGE, reason="Private package path is not configured.")
def test_active_source_has_verified_current_population():
    _, content = verified_package(PACKAGE, FINAL_PACKAGE_SHA256)
    workbook = read_package_member(content, "PESLC_RAW.xlsx")
    parsed = parse_source_file("PESLC_RAW.xlsx", workbook)
    rows = [
        row for frame in parsed.frames.values()
        for row in dataframe_to_source_rows(frame, "filtered-source-check")
    ]

    assert len(rows) == 291
    assert Counter(row.payment_status for row in rows) == {"Fully Paid": 291}
    assert sum(group.rfm_eligible for group in group_invoices(rows)) == 281
    assert len(read_package_csv(content, "account_master.csv")) == 84
    assert sha256(read_package_member(content, "03_MODEL/catboost.joblib")).hexdigest() == (
        "09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3"
    )
