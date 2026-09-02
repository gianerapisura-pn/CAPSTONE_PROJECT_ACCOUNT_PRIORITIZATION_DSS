from __future__ import annotations

import os
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from app.analytics.predictive.cart import run_cart_analysis
from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.etl.status import standardize_payment_status
from app.imports.validators import parse_source_file, validate_rows
from app.services.analytics_runner import run_account_prioritization


OFFICIAL_RAW_ENV = "PESLC_OFFICIAL_RAW_PATH"
OFFICIAL_RAW_PATH = os.getenv(OFFICIAL_RAW_ENV)
pytestmark = pytest.mark.skipif(
    not OFFICIAL_RAW_PATH,
    reason=f"Set {OFFICIAL_RAW_ENV} to the private PESLC_2017_2025_RAW_DATASET.xlsx path.",
)

EXPECTED_WEIGHTS = {
    "recency": 0.32501690349592166,
    "frequency": 0.18859313665772925,
    "monetary": 0.18128440467431278,
    "settlement": 0.3051055551720364,
}

EXPECTED_TOP_TEN = [
    ("MEGAWORLD CORPORATION", 0.8455278933823807),
    ("LOXON PHILIPPINES INC", 0.81521415849776),
    ("RYXEN INC", 0.7838656036678737),
    ("METRO WORX PROPERTIES INC", 0.7718280150468787),
    ("EXQUADRA INC", 0.7317860506365343),
    ("WILL DECENA & ASSOCIATES INC", 0.715255104555997),
    ("BCE PROPERTIES INC", 0.6954028628219637),
    ("WEE COMMUNITY DEVELOPERS INC", 0.6810958643186328),
    ("EXECUTIVE GENESIS SERVICES INC", 0.6674287321415685),
    ("LYCEUM OF THE PHILIPPINES UNIVERSITY INC", 0.6410534388734388),
]

EXPECTED_SENSITIVITY = {
    0.10: (0.9993595986734394, 0.9984467486671423, 0.04819277108433735),
    0.20: (0.9982767306158432, 0.9922967129843414, 0.04819277108433735),
    0.30: (0.9955919146971158, 0.9803114898618867, 0.0963855421686747),
    0.40: (0.9931346291087696, 0.9402837832164895, 0.12048192771084337),
}

EXPECTED_BACKTEST = {
    "2018-12-31": (0.6697513435829391, 0.09141634252902751, 7.326385250758335),
    "2019-12-31": (0.04075919572460492, 0.12028933277389071, 0.33884297788250656),
    "2020-12-31": (0.419400223380573, 0.1194657426711641, 3.5106317007963925),
    "2021-12-31": (0.26978362472908696, 0.14188463155692188, 1.9014295048639853),
    "2022-12-31": (0.2722835689067238, 0.11334167627222938, 2.402325233418467),
    "2023-12-31": (0.6444680087782653, 0.1257877709506336, 5.12345519685846),
}


def test_official_raw_reproduces_locked_capstone_outputs():
    path = Path(OFFICIAL_RAW_PATH or "")
    assert path.is_file(), f"{OFFICIAL_RAW_ENV} does not identify a readable file."
    assert path.name == "PESLC_2017_2025_RAW_DATASET.xlsx"

    parsed = parse_source_file(path.name, path.read_bytes())
    assert set(parsed.frames) == {str(year) for year in range(2017, 2026)}
    validation_errors = sum(
        issue.severity == "error"
        for issue in parsed.issues
    ) + sum(
        issue.severity == "error"
        for frame in parsed.frames.values()
        for issue in validate_rows(frame)
    )
    assert validation_errors == 0, f"Official RAW validation produced {validation_errors} errors."

    frames = list(parsed.frames.values())
    assert sum(len(frame) for frame in frames) == 363
    status_counts = Counter(
        standardize_payment_status(value)
        for frame in frames
        for value in frame["PAYMENT STATUS"]
    )
    assert status_counts == Counter({"Fully Paid": 292, "Cancelled": 71})

    rows = [row for frame in frames for row in dataframe_to_source_rows(frame, "official-regression")]
    groups = group_invoices([
        row for row in rows
        if row.standardized_account_name and row.si_no and not pd.isna(row.si_date) and row.si_amount > 0
    ])
    valid_groups = [group for group in groups if group.rfm_eligible]
    assert len(valid_groups) == 282
    valid_sales = sum((group.si_amount for group in valid_groups), Decimal("0"))
    naive_fully_paid_sales = sum(
        (row.si_amount for row in rows if row.payment_status == "Fully Paid"), Decimal("0")
    )
    assert valid_sales == Decimal("167467524.93")
    assert naive_fully_paid_sales == Decimal("172107496.97")
    assert naive_fully_paid_sales - valid_sales == Decimal("4639972.04")
    multirow_valid_groups = [group for group in valid_groups if len(group.rows) > 1]
    assert len(multirow_valid_groups) == 8
    assert sum(len(group.rows) for group in multirow_valid_groups) == 18
    assert max(row.cr_date for row in rows if row.cr_date is not None).date() == date(2025, 12, 13)
    post_cutoff_settlements = [
        group for group in valid_groups
        if group.settlement_eligible and group.final_cr_date.date() > date(2025, 8, 13)
    ]
    assert len(post_cutoff_settlements) == 7
    assert len({group.standardized_account_name for group in post_cutoff_settlements}) == 6

    cart, artifact = run_cart_analysis(groups, include_artifact=True)
    assert artifact is not None
    result = run_account_prioritization(groups, cart_result=cart)
    assert result.cutoff_date == "2025-08-13"
    assert len(result.rfm) == 85
    assert result.mcs_eligible_account_count == 83
    assert {row["account"] for row in result.rfm} - {row["account"] for row in result.priorities} == {
        "RIVER GREEN RESIDENCES", "STATEFIELDS SCHOOL INC",
    }
    assert Counter(row["priority_group"] for row in result.priorities) == Counter({
        "High": 28, "Medium": 27, "Low": 28,
    })
    assert result.critic_weights == pytest.approx(EXPECTED_WEIGHTS, rel=0, abs=1e-12)
    for actual, (expected_account, expected_score) in zip(
        result.priorities[:10], EXPECTED_TOP_TEN, strict=True
    ):
        assert actual["account"] == expected_account
        assert actual["final_priority_score"] == pytest.approx(expected_score, rel=0, abs=1e-12)

    assert cart.outcome_window_months == 12
    assert cart.feature_columns == [
        "recency_days", "frequency_count", "monetary_value",
        "avg_settlement_days", "account_activity_gap",
    ]
    assert cart.model_version == "cart_final_data_run_v3"
    assert cart.hyperparameters == {"max_depth": 3, "min_samples_split": 12, "min_samples_leaf": 6}
    assert cart.tree_depth == 3
    assert cart.leaf_count == 8
    assert cart.report["class_distribution"]["Lower"] + cart.report["class_distribution"]["Higher"] == 79
    assert cart.report["accuracy"] == pytest.approx(0.8860759493670886, rel=0, abs=1e-12)
    assert cart.report["classification_error"] == pytest.approx(0.11392405063291144, rel=0, abs=1e-12)
    assert cart.report["macro_f1"] == pytest.approx(0.7033792240300376, rel=0, abs=1e-12)
    assert cart.report["per_class"]["Lower"]["f1"] == pytest.approx(0.47058823529411764, rel=0, abs=1e-12)
    assert cart.report["per_class"]["Higher"]["f1"] == pytest.approx(0.9361702127659575, rel=0, abs=1e-12)
    assert cart.majority_baseline_report["macro_f1"] == pytest.approx(0.4697986577181208, rel=0, abs=1e-12)
    assert Counter(cart.predictions.values()) == Counter({"Lower": 6, "Higher": 79})

    assert sum(len(summary["scenarios"]) for summary in result.sensitivity) == 33200
    for summary in result.sensitivity:
        expected = EXPECTED_SENSITIVITY[summary["weight_range"]]
        actual = (summary["mean_spearman"], summary["min_spearman"], summary["max_group_movement_rate"])
        assert actual == pytest.approx(expected, rel=0, abs=1e-12)
        assert all(
            {"rank_change", "spearman_correlation"} <= scenario.keys()
            for scenario in summary["scenarios"]
        )

    assert result.backtest["cutoff_count"] == 6
    for row in result.backtest["cutoffs"]:
        expected = EXPECTED_BACKTEST[row["cutoff_date"]]
        actual = (row["top_decile_capture"], row["random_baseline_capture"], row["lift_over_random"])
        assert actual == pytest.approx(expected, rel=0, abs=1e-12)
