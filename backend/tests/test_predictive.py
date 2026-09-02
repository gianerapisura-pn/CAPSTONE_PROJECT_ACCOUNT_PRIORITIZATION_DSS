from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.analytics.predictive.cart import (
    CANDIDATE_FEATURES,
    TARGET_COLUMN,
    _development_supported_features,
    build_cutoff_dataset,
    train_cart_temporal,
)
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.etl.invoices import SourceRow, group_invoices


def source(
    account: str,
    date: str,
    amount: str = "100",
    cr_date: str | None = None,
) -> SourceRow:
    collection = pd.Timestamp(cr_date) if cr_date else pd.Timestamp(date) + pd.Timedelta(days=10)
    return SourceRow(
        customer_name_raw=account,
        standardized_account_name=account.upper(),
        si_no=f"SI-{account}-{date}",
        si_date=pd.Timestamp(date),
        si_amount=Decimal(amount),
        cr_no="CR",
        cr_date=collection,
        cr_amount=Decimal(amount),
        ewt=Decimal("0"),
        payment_mode="Bank",
        payment_status_raw="Fully Paid",
        payment_status="Fully Paid",
        is_cancelled=False,
        import_batch_id="batch",
        source_sheet="Sheet1",
        source_row_number=1,
    )


def test_cutoff_features_use_component_specific_history_without_future_leakage():
    groups = group_invoices([
        source("A", "2017-01-01"),
        source("A", "2018-01-01"),
        source("A", "2019-06-01", "200"),
        source("A", "2021-01-01"),
        source("B", "2019-12-01", "50", "2021-01-01"),
    ])
    cutoff = pd.Timestamp("2020-12-31")
    frame = build_cutoff_dataset(groups, cutoff, 24, 12, include_outcome=False)
    account_a = frame[frame["account"] == "A"].iloc[0]
    account_b = frame[frame["account"] == "B"].iloc[0]
    assert account_a["recency_days"] == (cutoff - pd.Timestamp("2019-06-01")).days
    assert account_a["frequency_count"] == 1
    assert account_a["monetary_value"] == 200
    assert account_a["recent_transaction_count"] == 0
    assert account_a["account_activity_gap"] == (pd.Timestamp("2019-06-01") - pd.Timestamp("2018-01-01")).days
    assert account_a["avg_settlement_days"] == 10
    assert account_b["has_valid_settlement_record"] == 0
    assert pd.isna(account_b["avg_settlement_days"])
    assert TARGET_COLUMN not in frame


def test_historical_account_older_than_24_months_remains_in_cutoff_universe():
    frame = build_cutoff_dataset(
        group_invoices([source("OLD", "2017-01-01")]),
        pd.Timestamp("2020-12-31"),
        24,
        12,
        include_outcome=False,
    )
    assert frame.iloc[0]["account"] == "OLD"
    assert frame.iloc[0]["frequency_count"] == 0
    assert frame.iloc[0]["monetary_value"] == 0


def test_realized_outcome_is_distinct_and_requires_complete_future_window():
    groups = group_invoices([source("A", "2020-01-01"), source("A", "2020-12-01"), source("B", "2020-12-30"), source("B", "2021-01-01")])
    complete = build_cutoff_dataset(groups, pd.Timestamp("2020-06-30"), 24, 6)
    assert complete.iloc[0][TARGET_COLUMN] == "Lower"
    incomplete = build_cutoff_dataset(groups, pd.Timestamp("2021-01-01"), 24, 12)
    assert incomplete.empty


def test_final_candidate_features_and_exact_temporal_grid():
    config = DEFAULT_ANALYTICS_CONFIG
    assert "latest_transaction_year" not in CANDIDATE_FEATURES
    assert not {
        "rfm_score", "final_priority_score", "priority_rank", "priority_group",
        "normalized_recency", "normalized_frequency", "normalized_monetary",
        "normalized_settlement",
    } & set(CANDIDATE_FEATURES)
    assert config.cart_cutoffs == (
        "2018-12-31", "2019-12-31", "2020-12-31",
        "2021-12-31", "2022-12-31", "2023-12-31",
    )
    assert config.cart_development_cutoffs == config.cart_cutoffs[:-1]
    assert config.cart_oop_cutoff == "2023-12-31"
    assert config.cart_max_depth == (3, 4, 5)
    assert config.cart_min_samples_split == (4, 8, 12)
    assert config.cart_min_samples_leaf == (2, 4, 6)


def test_reduced_feature_selection_has_no_mandatory_rfm_retention():
    missingness = pd.Series({feature: 0.0 for feature in CANDIDATE_FEATURES})
    no_importance = {feature: 0.0 for feature in CANDIDATE_FEATURES}
    frequency_only = dict(no_importance, frequency_count=0.2)
    assert _development_supported_features(missingness, frequency_only, no_importance) == [
        "frequency_count"
    ]
    settlement_only = dict(no_importance, avg_settlement_days=0.2)
    assert _development_supported_features(missingness, settlement_only, no_importance) == [
        "avg_settlement_days"
    ]
    assert _development_supported_features(missingness, no_importance, no_importance) == []


def test_cart_insufficient_class_safeguard():
    dev = pd.DataFrame({
        "account": ["A", "B"],
        "recency_days": [1, 2],
        "frequency": [1, 1],
        "monetary": [100, 100],
        TARGET_COLUMN: ["Lower", "Lower"],
    })
    result = train_cart_temporal(dev, dev)
    assert result.status == "Predictive Context Unavailable / Insufficient Data"


def test_temporal_cart_reports_required_metrics_and_raw_features_only():
    development = pd.DataFrame({
        "account": [f"A{i}" for i in range(8)],
        "recency_days": [5, 10, 15, 20, 80, 90, 100, 110],
        "frequency_count": [5, 4, 4, 3, 2, 2, 1, 1],
        "monetary_value": [500, 450, 400, 350, 200, 180, 150, 100],
        TARGET_COLUMN: ["Lower"] * 4 + ["Higher"] * 4,
    })
    oop = pd.DataFrame({
        "account": ["O1", "O2", "O3", "O4"],
        "recency_days": [8, 18, 85, 105],
        "frequency_count": [5, 3, 2, 1],
        "monetary_value": [480, 360, 190, 120],
        TARGET_COLUMN: ["Lower", "Lower", "Higher", "Higher"],
    })
    result = train_cart_temporal(development, oop)
    assert result.status == "Validated"
    assert set(result.feature_columns) <= set(CANDIDATE_FEATURES)
    assert result.report["classification_error"] == 1 - result.report["accuracy"]
    assert {"Lower", "Higher"} <= result.report["per_class"].keys()
    assert result.majority_baseline_report is not None
    assert len(result.confusion_matrix or []) == 2


def test_cart_source_has_no_forbidden_preprocessing_or_oop_refit():
    source_text = Path("app/analytics/predictive/cart.py").read_text(encoding="utf-8")
    assert "StandardScaler" not in source_text
    assert "add_indicator=True" not in source_text
    assert "class_weight" not in source_text
    assert "operational_model.fit" not in source_text
    assert '"pipeline": frozen_model' in source_text
