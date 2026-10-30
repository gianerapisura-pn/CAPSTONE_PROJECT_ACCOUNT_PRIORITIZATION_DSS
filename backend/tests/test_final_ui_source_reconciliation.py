"""Compare the approved QA archive with the existing verified study sources."""
import os
from hashlib import sha256

import pytest

from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256, FINAL_QA_PACKAGE_SHA256,
    package_members, read_package_csv, read_package_member, verified_package,
)


def test_latest_qa_core_and_composition_reconcile_to_source():
    latest = os.getenv("PESLC_FINAL_QA_PACKAGE_PATH")
    previous = os.getenv("PESLC_FINAL_ANALYTICS_PACKAGE_PATH")
    if not latest or not previous:
        pytest.skip("Configure both authorized private packages for source reconciliation.")
    _, qa = verified_package(latest, FINAL_QA_PACKAGE_SHA256)
    _, original = verified_package(previous, FINAL_PACKAGE_SHA256)
    members = [name.split("PESLC_FINAL_ANALYTICS/", 1)[-1] for name in package_members(original)
               if "/01_DATA/" in name or "/03_MODEL/" in name]
    assert members
    for member in members:
        if member.endswith("/") or member.endswith("README.md"):
            continue
        assert sha256(read_package_member(qa, member)).digest() == sha256(read_package_member(original, member)).digest(), member
    master = read_package_csv(qa, "01_DATA/01_ACCOUNTS/account_master.csv")
    priority = read_package_csv(qa, "01_DATA/06_PRIORITY/current_priority.csv")
    category = read_package_csv(qa, "01_DATA/06_PRIORITY/business_category_summary.csv")
    types = read_package_csv(qa, "01_DATA/06_PRIORITY/business_type_summary.csv")
    population = priority.merge(master, on="account_key", suffixes=("", "_master"), validate="one_to_one")
    for frame, field in ((category, "business_category"), (types, "primary_business_type")):
        source_field = field + "_master" if field + "_master" in population else field
        counts = population.groupby(source_field).size().to_dict()
        assert frame.set_index(field).account_count.to_dict() == counts
        assert frame.account_count.sum() == len(priority)
    assert priority.account_key.is_unique
