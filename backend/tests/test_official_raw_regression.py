"""Private final-lock regression. It remains pending unless authorized inputs are configured."""
from collections import Counter
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import os

import joblib
import pandas as pd
import pytest

from app.analytics.predictive.future_transaction import score_extra_trees_artifact
from app.analytics.validation.baselines import annual_business_baselines
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.etl.standardization import standardize_account_name
from app.imports.validators import parse_source_file
from app.services.analytics_runner import run_account_prioritization
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256,
    read_package_csv,
    read_package_member,
    verified_package,
)
from app.services.model_lifecycle import _validate_artifact

PACKAGE = os.getenv("PESLC_FINAL_ANALYTICS_PACKAGE_PATH")
RAW = os.getenv("PESLC_OFFICIAL_RAW_PATH")
MODEL = os.getenv("PESLC_LOCKED_MODEL_PATH")
MASTER = os.getenv("PESLC_ACCOUNT_MASTER_PATH")
STATUS = os.getenv("PESLC_ACCOUNT_STATUS_PATH")
AVAILABLE = bool(PACKAGE or all((RAW, MODEL, MASTER)))
pytestmark = pytest.mark.skipif(
    not AVAILABLE,
    reason="Authorized private final analytics package/inputs are not configured.",
)

EXPECTED_SENSITIVITY = {
    0.10: (0.9987951807228914, 0.9957071985420674, 0.013095238095238, 0.0476190476190476, 6),
    0.20: (0.9968324389996964, 0.9880328034828392, 0.0304761904761904, 0.0714285714285714, 12),
    0.30: (0.9933925280955757, 0.9783740002024908, 0.0449999999999999, 0.119047619047619, 18),
    0.40: (0.9920609496810772, 0.9682494684620836, 0.0495238095238095, 0.119047619047619, 23),
}
EXPECTED_TOP_TEN = [
    "MEGAWORLD CORPORATION", "LOXON PHILIPPINES INC", "METRO WORX PROPERTIES INC",
    "RYXEN INC", "EXQUADRA INC", "WILL DECENA AND ASSOCIATES, INC.",
    "WEE COMMUNITY DEVELOPERS INC", "BCE PROPERTIES INC",
    "EXECUTIVE GENESIS SERVICES INC", "WEECOMM CENTRE PROPERTIES, INC.",
]
EXPECTED_SALES = {
    2017: 22685859.51, 2018: 28141212.85, 2019: 25104956.78,
    2020: 7422135.75, 2021: 17072550.27, 2022: 16803717.74,
    2023: 20244551.54, 2024: 21069452.09, 2025: 8923088.40,
    2026: 0.0,
}


def _private_inputs():
    if PACKAGE:
        _, package_content = verified_package(PACKAGE, FINAL_PACKAGE_SHA256)
        raw = read_package_member(package_content, "PESLC_RAW.xlsx")
        master = read_package_csv(package_content, "01_DATA/01_ACCOUNTS/account_master.csv")
        status = read_package_csv(package_content, "01_DATA/01_ACCOUNTS/account_status.csv")
        model_bytes = read_package_member(package_content, "03_MODEL/extra_trees.joblib")
        return raw, master, status, model_bytes
    raw_path, model_path, master_path = map(Path, (RAW, MODEL, MASTER))
    status = pd.read_csv(STATUS) if STATUS else None
    return raw_path.read_bytes(), pd.read_csv(master_path), status, model_path.read_bytes()


def test_private_final_locked_end_to_end(monkeypatch):
    raw_bytes, master, status, model_bytes = _private_inputs()
    parsed = parse_source_file("PESLC_RAW.xlsx", raw_bytes)
    rows = [row for frame in parsed.frames.values()
            for row in dataframe_to_source_rows(frame, "official")]
    assert len(rows) == 363
    assert Counter(row.payment_status for row in rows) == {
        "Fully Paid": 292, "Cancelled": 71}
    groups = group_invoices(rows)
    valid = [item for item in groups if item.rfm_eligible]
    assert len(valid) == 282
    assert sum((item.si_amount for item in valid), Decimal("0")) == Decimal("167467524.93")
    assert list(master.columns) == [
        "account_key", "account_name", "entity_type", "business_category",
        "primary_business_type",
    ]
    if status is not None:
        assert list(status.columns) == ["account_key", "account_status", "last_verified"]
        assert len(master.merge(status, on="account_key", how="left", validate="one_to_one")) == 85
    master = master.copy()
    master["standardized"] = master["account_name"].map(standardize_account_name)
    eligible = set(master.loc[
        master["entity_type"].astype(str) != "Individual/Personal", "standardized"
    ])
    assert len(master) == 85
    assert len(eligible) == 84
    personal = master.loc[master["entity_type"] == "Individual/Personal"]
    assert personal["standardized"].tolist() == ["ROD DE GUIA"]
    assert sha256(model_bytes).hexdigest() == DEFAULT_ANALYTICS_CONFIG.model_sha256
    monkeypatch.setattr("app.services.model_lifecycle.sklearn.__version__", "1.8.0")
    artifact = _validate_artifact(joblib.load(BytesIO(model_bytes)), DEFAULT_ANALYTICS_CONFIG)
    predictive = score_extra_trees_artifact(
        groups, artifact, pd.Timestamp("2026-09-21"), eligible,
        DEFAULT_ANALYTICS_CONFIG.model_version,
        DEFAULT_ANALYTICS_CONFIG.model_sha256,
    )
    result = run_account_prioritization(
        groups, pd.Timestamp("2026-09-21"), eligible, predictive_result=predictive
    )
    assert result.latest_valid_si_date == "2025-08-13"
    assert result.latest_final_cr_date == "2025-12-13"
    assert len(result.priorities) == 84
    assert Counter(item["priority_group"] for item in result.priorities) == {
        "High": 28, "Medium": 28, "Low": 28,
    }
    assert Counter(predictive.predictions.values()) == {"No Future Transaction": 84}
    assert result.critic_weights == pytest.approx({
        "recency": 0.374388292558304,
        "frequency": 0.19126358898879575,
        "monetary": 0.17978654445098569,
        "settlement": 0.2545615740019145,
    }, abs=1e-12)
    assert [item["account"] for item in result.priorities[:10]] == EXPECTED_TOP_TEN
    assert len(result.sensitivity) == 4
    assert sum(summary["iterations"] for summary in result.sensitivity) == 400
    assert sum(len(summary["scenarios"]) for summary in result.sensitivity) == 33600
    for summary in result.sensitivity:
        expected = EXPECTED_SENSITIVITY[summary["weight_range"]]
        assert summary["mean_spearman"] == pytest.approx(expected[0], abs=1e-12)
        assert summary["min_spearman"] == pytest.approx(expected[1], abs=1e-12)
        assert summary["group_movement_rate"] == pytest.approx(expected[2], abs=1e-12)
        assert summary["max_group_movement_rate"] == pytest.approx(expected[3], abs=1e-12)
        assert summary["accounts_changing_group_at_least_once"] == expected[4]
        assert summary["baseline_top_ten_remain_high"] is True
    baseline = annual_business_baselines(groups, pd.Timestamp("2026-09-21"), eligible)
    assert {row["year"]: row["all_recorded_sales"] for row in baseline} == pytest.approx(EXPECTED_SALES)
    assert next(row for row in baseline if row["year"] == 2018)["b2b_recorded_sales"] == pytest.approx(28128062.85)
    assert next(row for row in baseline if row["year"] == 2025)["period_status"] == "Complete year"
    ytd = next(row for row in baseline if row["year"] == 2026)
    assert ytd["period_status"] == "YTD through 2026-09-21"
    assert ytd["all_sales_yoy_change_pct"] is None
    cutoffs = result.backtest["cutoffs"]
    assert [(item["eligible_account_count"], item["selected_account_count"]) for item in cutoffs] == [
        (49, 5), (57, 6), (62, 7), (67, 7), (69, 7), (77, 8), (79, 8),
    ]
    expected_lifts = [6.563563, 0.387212, 3.714688, 2.582215, 2.683938, 6.203005, 2.795802]
    for item, expected in zip(cutoffs, expected_lifts, strict=True):
        assert item["expected_random_capture"] == pytest.approx(
            item["selected_account_count"] / item["eligible_account_count"]
        )
        assert item["lift_over_expected_random"] == pytest.approx(expected, abs=1e-6)
    assert sum(item["lift_over_expected_random"] > 1 for item in cutoffs) == 6