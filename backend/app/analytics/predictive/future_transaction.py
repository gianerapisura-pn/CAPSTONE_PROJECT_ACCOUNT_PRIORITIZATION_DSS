from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
)

from app.etl.invoices import InvoiceGroup

FUTURE_TRANSACTION = "Future Transaction"
NO_FUTURE_TRANSACTION = "No Future Transaction"
TARGET_COLUMN = "actual_future_transaction_class"
FEATURE_COLUMNS = (
    "recency_days",
    "frequency_24m",
    "monetary_24m",
    "avg_settlement_days",
    "account_activity_gap",
    "recent_transaction_count_12m",
    "recent_monetary_value_12m",
)


@dataclass(frozen=True)
class FutureTransactionResult:
    status: str
    target_horizon_months: int
    feature_columns: list[str]
    predictions: dict[str, str]
    model_version: str = ""
    model_family: str = "Extra Trees Classifier"
    artifact_hash: str | None = None
    analysis_reference_date: str | None = None
    report: dict | None = None
    monitoring_status: str = "Unavailable / model artifact not registered"


def build_cutoff_dataset(
    invoice_groups: list[InvoiceGroup],
    cutoff_date: pd.Timestamp,
    outcome_window_months: int = 12,
    include_outcome: bool = True,
    data_complete_through: pd.Timestamp | None = None,
    eligible_accounts: set[str] | None = None,
) -> pd.DataFrame:
    cutoff = pd.Timestamp(cutoff_date)
    valid = [
        group for group in invoice_groups
        if group.rfm_eligible
        and (eligible_accounts is None or group.standardized_account_name in eligible_accounts)
    ]
    history = [group for group in valid if group.si_date <= cutoff]
    columns = ("account", "cutoff_date", *FEATURE_COLUMNS, TARGET_COLUMN)
    if not history:
        return pd.DataFrame(columns=columns)
    future_end = cutoff + pd.DateOffset(months=outcome_window_months)
    evidence_end = pd.Timestamp(data_complete_through) if data_complete_through is not None else max(
        group.si_date for group in valid
    )
    if include_outcome and evidence_end < future_end:
        return pd.DataFrame(columns=columns)
    lookback_start = cutoff - pd.DateOffset(months=24)
    recent_start = cutoff - pd.DateOffset(months=12)
    future_accounts = {
        group.standardized_account_name
        for group in valid
        if cutoff < group.si_date <= future_end
    }
    rows: list[dict] = []
    for account in sorted({group.standardized_account_name for group in history}):
        account_history = sorted(
            (group for group in history if group.standardized_account_name == account),
            key=lambda group: group.si_date,
        )
        history_24m = [group for group in account_history if lookback_start < group.si_date <= cutoff]
        history_12m = [group for group in account_history if recent_start < group.si_date <= cutoff]
        dates = [group.si_date for group in account_history]
        settlement_days = [
            group.settlement_days
            for group in account_history
            if group.settlement_eligible
            and group.final_cr_date is not None
            and group.final_cr_date <= cutoff
            and group.settlement_days is not None
        ]
        row = {
            "account": account,
            "cutoff_date": cutoff,
            "recency_days": int((cutoff - dates[-1]).days),
            "frequency_24m": len(history_24m),
            "monetary_24m": float(sum((group.si_amount for group in history_24m), start=0)),
            "avg_settlement_days": float(np.mean(settlement_days)) if settlement_days else np.nan,
            "account_activity_gap": float((dates[-1] - dates[-2]).days) if len(dates) > 1 else np.nan,
            "recent_transaction_count_12m": len(history_12m),
            "recent_monetary_value_12m": float(
                sum((group.si_amount for group in history_12m), start=0)
            ),
        }
        if include_outcome:
            row[TARGET_COLUMN] = (
                FUTURE_TRANSACTION if account in future_accounts else NO_FUTURE_TRANSACTION
            )
        rows.append(row)
    return pd.DataFrame(rows)


def classification_metrics(actual, predicted) -> dict:
    actual_series = pd.Series(actual)
    predicted_array = np.asarray(predicted)
    accuracy = float(accuracy_score(actual_series, predicted_array))
    both_classes = set(actual_series) == {FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION}
    report = classification_report(
        actual_series,
        predicted_array,
        labels=[FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION],
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": accuracy,
        "classification_error": 1.0 - accuracy,
        "macro_f1": (
            float(f1_score(actual_series, predicted_array, average="macro", zero_division=0))
            if both_classes else None
        ),
        "balanced_accuracy": (
            float(balanced_accuracy_score(actual_series, predicted_array))
            if both_classes else None
        ),
        "mcc": float(matthews_corrcoef(actual_series, predicted_array)),
        "class_distribution": {
            label: int((actual_series == label).sum())
            for label in (FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION)
        },
        "per_class": {
            label: {
                "precision": float(report[label]["precision"]),
                "recall": float(report[label]["recall"]),
                "f1": float(report[label]["f1-score"]),
                "support": int(report[label]["support"]),
            }
            for label in (FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION)
        },
        "confusion_matrix": confusion_matrix(
            actual_series,
            predicted_array,
            labels=[FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION],
        ).tolist(),
    }


def _canonical_class(value: object) -> str:
    if value in (FUTURE_TRANSACTION, 0, False, "0"):
        return FUTURE_TRANSACTION
    if value in (NO_FUTURE_TRANSACTION, 1, True, "1"):
        return NO_FUTURE_TRANSACTION
    raise ValueError(f"Frozen artifact returned unsupported class label: {value!r}")


def score_extra_trees_artifact(
    invoice_groups: list[InvoiceGroup],
    artifact: object,
    analysis_reference_date: pd.Timestamp,
    eligible_accounts: set[str],
    model_version: str,
    artifact_hash: str,
) -> FutureTransactionResult:
    feature_columns = list(getattr(artifact, "feature_names_in_", []))
    if feature_columns != list(FEATURE_COLUMNS):
        raise ValueError("Frozen artifact feature contract does not match the seven locked predictors.")
    if not hasattr(artifact, "predict"):
        raise ValueError("Frozen artifact is not a fitted scikit-learn prediction pipeline.")
    frame = build_cutoff_dataset(
        invoice_groups,
        pd.Timestamp(analysis_reference_date),
        include_outcome=False,
        eligible_accounts=eligible_accounts,
    )
    raw_predictions = artifact.predict(frame[feature_columns]) if not frame.empty else []
    predictions = {
        account: _canonical_class(value)
        for account, value in zip(frame.get("account", []), raw_predictions, strict=False)
    }
    return FutureTransactionResult(
        status="Validated",
        target_horizon_months=12,
        feature_columns=feature_columns,
        predictions=predictions,
        model_version=model_version,
        artifact_hash=artifact_hash,
        analysis_reference_date=pd.Timestamp(analysis_reference_date).date().isoformat(),
        report=None,
        monitoring_status="Pending outcome maturity",
    )