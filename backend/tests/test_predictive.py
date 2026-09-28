from decimal import Decimal
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from app.analytics.predictive.future_transaction import (
    FEATURE_COLUMNS, FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION, TARGET_COLUMN,
    build_cutoff_dataset, classification_metrics, score_extra_trees_artifact,
)
from app.etl.invoices import InvoiceGroup


def group(account, si, date, amount=100, cr=None):
    return InvoiceGroup(
        invoice_group_id=account + si, standardized_account_name=account,
        si_no=si, si_date=pd.Timestamp(date), si_amount=Decimal(str(amount)),
        payment_status="Fully Paid", final_cr_date=pd.Timestamp(cr) if cr else None,
        total_cr_amount=Decimal(str(amount)), reconciliation_amount=Decimal(str(amount)),
        reconciliation_difference=Decimal("0"), reconciled=True,
    )


def test_exact_seven_predictors_and_cutoff_safe_windows():
    groups = [
        group("A", "1", "2019-01-01", 10, "2019-01-10"),
        group("A", "2", "2020-06-01", 20, "2020-06-10"),
        group("A", "3", "2021-06-01", 30, "2021-06-10"),
        group("A", "4", "2022-01-01", 999, "2022-01-10"),
    ]
    frame = build_cutoff_dataset(
        groups, pd.Timestamp("2021-06-30"), include_outcome=False)
    assert tuple(FEATURE_COLUMNS) == (
        "recency_days", "frequency_24m", "monetary_24m", "avg_settlement_days",
        "account_activity_gap", "recent_transaction_count_12m",
        "recent_monetary_value_12m")
    row = frame.iloc[0]
    assert row["frequency_24m"] == 2
    assert row["monetary_24m"] == 50
    assert row["recent_transaction_count_12m"] == 1
    assert row["recent_monetary_value_12m"] == 30


def test_outcome_orientation_and_completeness_guard():
    groups = [
        group("A", "1", "2020-01-01"),
        group("A", "2", "2021-03-01"),
        group("B", "3", "2020-01-01"),
        group("C", "4", "2022-01-01"),
    ]
    frame = build_cutoff_dataset(groups, pd.Timestamp("2020-12-31"),
                                 data_complete_through=pd.Timestamp("2022-01-01"))
    labels = dict(zip(frame["account"], frame[TARGET_COLUMN]))
    assert labels["A"] == FUTURE_TRANSACTION
    assert labels["B"] == NO_FUTURE_TRANSACTION
    incomplete = build_cutoff_dataset(
        groups, pd.Timestamp("2021-12-31"),
        data_complete_through=pd.Timestamp("2022-01-01"))
    assert incomplete.empty


def test_activity_gap_missingness_is_structural():
    frame = build_cutoff_dataset(
        [group("A", "1", "2020-01-01")], pd.Timestamp("2020-12-31"),
        include_outcome=False)
    assert np.isnan(frame.iloc[0]["account_activity_gap"])


def test_b2b_set_filters_unknown_or_personal_context():
    groups = [group("B2B", "1", "2020-01-01"), group("UNKNOWN", "2", "2020-01-01")]
    frame = build_cutoff_dataset(
        groups, pd.Timestamp("2020-12-31"), include_outcome=False,
        eligible_accounts={"B2B"})
    assert frame["account"].tolist() == ["B2B"]


def test_single_class_metrics_suppress_balanced_measures():
    result = classification_metrics(
        [NO_FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION],
        [NO_FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION])
    assert result["accuracy"] == 1
    assert result["macro_f1"] is None
    assert result["balanced_accuracy"] is None


def test_frozen_scoring_returns_only_categorical_class():
    class Model:
        def predict(self, frame):
            return [0] * len(frame)
    artifact = {"model": Model(), "feature_columns": list(FEATURE_COLUMNS)}
    result = score_extra_trees_artifact(
        [group("A", "1", "2020-01-01")], artifact,
        pd.Timestamp("2020-12-31"), {"A"}, "extra_trees_stage8", "hash")
    assert result.predictions == {"A": NO_FUTURE_TRANSACTION}
    assert not any("score" in key or "probability" in key
                   for key in result.__dict__)


def test_obsolete_cart_production_module_is_removed():
    assert not Path("app/analytics/predictive/cart.py").exists()
