from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from app.analytics.descriptive.rfm import compute_rfm
from app.etl.invoices import InvoiceGroup


@dataclass(frozen=True)
class CartResult:
    status: str
    outcome_window_months: int
    feature_columns: list[str]
    report: dict
    predictions: dict[str, str]


def _add_months(ts: pd.Timestamp, months: int) -> pd.Timestamp:
    return ts + pd.DateOffset(months=months)


def build_cutoff_dataset(
    invoice_groups: list[InvoiceGroup],
    cutoff_date: pd.Timestamp,
    lookback_months: int,
    outcome_window_months: int,
) -> pd.DataFrame:
    feature_start = cutoff_date - pd.DateOffset(months=lookback_months)
    feature_groups = [g for g in invoice_groups if g.rfm_eligible and feature_start <= g.si_date <= cutoff_date]
    future_end = _add_months(cutoff_date, outcome_window_months)
    future_groups = [g for g in invoice_groups if g.rfm_eligible and cutoff_date < g.si_date <= future_end]
    rfm = compute_rfm(feature_groups, cutoff_date=cutoff_date)
    future_accounts = {g.standardized_account_name for g in future_groups}
    rows = []
    for item in rfm:
        rows.append(
            {
                "account": item.account,
                "recency_days": item.recency_days,
                "frequency": item.frequency,
                "monetary": float(item.monetary),
                "rfm_score": item.rfm_score,
                "inactivity_risk": "Lower" if item.account in future_accounts else "Higher",
            }
        )
    return pd.DataFrame(rows)


def train_cart_temporal(
    development_frame: pd.DataFrame,
    oop_frame: pd.DataFrame,
    random_seed: int = 42,
    min_class_count: int = 2,
) -> CartResult:
    feature_columns = ["recency_days", "frequency", "monetary"]
    if development_frame.empty or oop_frame.empty:
        return CartResult("insufficient_data", 0, feature_columns, {}, {})
    class_counts = development_frame["inactivity_risk"].value_counts()
    if len(class_counts) < 2 or class_counts.min() < min_class_count:
        return CartResult("insufficient_classes", 0, feature_columns, {}, {})
    pipeline = Pipeline(
        [
            ("scale", StandardScaler()),
            ("tree", DecisionTreeClassifier(random_state=random_seed, max_depth=3, class_weight="balanced")),
        ]
    )
    pipeline.fit(development_frame[feature_columns], development_frame["inactivity_risk"])
    predicted = pipeline.predict(oop_frame[feature_columns])
    report = classification_report(oop_frame["inactivity_risk"], predicted, output_dict=True, zero_division=0)
    predictions = dict(zip(oop_frame["account"], predicted, strict=False))
    return CartResult("trained", 0, feature_columns, report, predictions)
