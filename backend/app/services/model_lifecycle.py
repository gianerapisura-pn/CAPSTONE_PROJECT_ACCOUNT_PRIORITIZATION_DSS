from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.analytics.predictive.future_transaction import (
    FEATURE_COLUMNS,
    FUTURE_TRANSACTION,
    NO_FUTURE_TRANSACTION,
    FutureTransactionResult,
    classification_metrics,
    score_extra_trees_artifact,
)
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.db.models import (
    DimAccount,
    FutureTransactionPrediction,
    PredictiveModelVersion,
    PredictiveMonitoringEvaluation,
)
from app.etl.invoices import InvoiceGroup
from app.services.storage import ModelStorage

TARGET_DEFINITION = (
    "Future Transaction means at least one valid logical Sales Invoice after the cutoff "
    "and on or before the end of the next 12 months."
)
LOCKED_PARAMETERS = {
    "n_estimators": 300,
    "criterion": "gini",
    "max_depth": None,
    "min_samples_split": 2,
    "min_samples_leaf": 3,
    "max_features": 0.75,
    "class_weight": "balanced",
    "bootstrap": False,
    "random_state": 42,
}
LOCKED_DEVELOPMENT_METRICS = {
    "macro_f1": 0.8015103929068558,
    "classification_error": 0.0650150370168791,
    "accuracy": 0.9349849629831208,
    "balanced_accuracy": 0.817073754789272,
    "future_transaction_f1": 0.6388888888888888,
    "future_transaction_recall": 0.6722222222222222,
    "mcc": 0.6103695900043568,
}


def active_model_version(db: Session) -> PredictiveModelVersion | None:
    return db.scalar(
        select(PredictiveModelVersion)
        .where(PredictiveModelVersion.status == "active")
        .order_by(desc(PredictiveModelVersion.created_at))
        .limit(1)
    )


def _artifact_bytes(record: PredictiveModelVersion) -> bytes:
    if not record.artifact_path:
        raise ValueError("Active model has no artifact path.")
    content = ModelStorage().get(record.artifact_path)
    digest = sha256(content).hexdigest()
    if not record.artifact_hash or digest != record.artifact_hash:
        raise ValueError("Active model artifact hash verification failed.")
    return content


def _validate_artifact(artifact: object, config: AnalyticsConfig) -> dict:
    if sklearn.__version__ != "1.8.0":
        raise ValueError(
            f"Frozen artifact requires scikit-learn 1.8.0; runtime is {sklearn.__version__}."
        )
    if not isinstance(artifact, dict):
        raise ValueError("Frozen artifact must be a metadata-wrapped joblib dictionary.")
    if list(artifact.get("feature_columns") or []) != list(FEATURE_COLUMNS):
        raise ValueError("Frozen artifact does not declare the seven locked predictors in order.")
    estimator = artifact.get("pipeline") or artifact.get("model")
    if estimator is None or not hasattr(estimator, "predict"):
        raise ValueError("Frozen artifact does not contain a prediction pipeline.")
    version = artifact.get("model_version", config.model_version)
    if version != config.model_version:
        raise ValueError(f"Artifact model version must be {config.model_version}.")
    family = artifact.get("model_family", config.model_family)
    if family != config.model_family:
        raise ValueError(f"Artifact model family must be {config.model_family}.")
    return artifact


def _load_artifact(
    record: PredictiveModelVersion,
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> dict:
    if record.model_version != config.model_version:
        raise ValueError("Active artifact is not the locked Extra Trees model version.")
    if record.artifact_hash != config.model_sha256:
        raise ValueError("Registered artifact SHA-256 is not the locked expected SHA-256.")
    return _validate_artifact(joblib.load(BytesIO(_artifact_bytes(record))), config)


def register_frozen_model(
    db: Session,
    local_artifact_path: str | Path,
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> PredictiveModelVersion:
    path = Path(local_artifact_path).expanduser().resolve(strict=True)
    content = path.read_bytes()
    digest = sha256(content).hexdigest()
    if digest != config.model_sha256:
        raise ValueError(
            f"Artifact SHA-256 mismatch: expected {config.model_sha256}, received {digest}."
        )
    artifact = _validate_artifact(joblib.load(BytesIO(content)), config)
    existing = db.scalar(
        select(PredictiveModelVersion).where(
            PredictiveModelVersion.model_version == config.model_version
        )
    )
    if existing:
        raise ValueError(f"Model version {config.model_version} is already registered.")
    storage_path = ModelStorage().put(config.model_version, content)
    for prior in db.scalars(
        select(PredictiveModelVersion).where(PredictiveModelVersion.status == "active")
    ).all():
        prior.status = "retired"
    record = PredictiveModelVersion(
        model_version=config.model_version,
        model_family=config.model_family,
        model_parameters=LOCKED_PARAMETERS,
        target_definition=TARGET_DEFINITION,
        primary_selection_metric="Equal-year mean outer Macro F1",
        decision_threshold=config.decision_threshold,
        status="active",
        trained_through_date=date(2022, 12, 31),
        selected_outcome_horizon=config.target_horizon_months,
        predictive_lookback_months=config.predictive_lookback_months,
        recent_transaction_months=config.recent_transaction_months,
        retained_features=list(FEATURE_COLUMNS),
        preprocessing_config={
            "imputation": "training-fold median during temporal evaluation",
            "deployment_imputation_values": artifact.get("imputation_values", {}),
            "scaling": None,
        },
        tree_hyperparameters=LOCKED_PARAMETERS,
        random_seed=config.random_seed,
        development_metrics=LOCKED_DEVELOPMENT_METRICS,
        oop_metrics=dict(artifact.get("validation_report") or {}),
        last_validation_date=datetime.now(timezone.utc).date(),
        method_version=config.version,
        code_version=config.version,
        artifact_path=storage_path,
        artifact_hash=digest,
        review_recommended=False,
    )
    db.add(record)
    db.flush()
    return record


def unavailable_prediction(config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG) -> FutureTransactionResult:
    return FutureTransactionResult(
        status="model_unavailable",
        target_horizon_months=config.target_horizon_months,
        feature_columns=list(FEATURE_COLUMNS),
        predictions={},
        model_version=config.model_version,
    )


def future_transaction_for_current_run(
    db: Session,
    invoice_groups: list[InvoiceGroup],
    analysis_reference_date: pd.Timestamp,
    eligible_accounts: set[str],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> FutureTransactionResult:
    active = active_model_version(db)
    if active is None:
        return unavailable_prediction(config)
    try:
        artifact = _load_artifact(active, config)
        return score_extra_trees_artifact(
            invoice_groups,
            artifact,
            analysis_reference_date,
            eligible_accounts,
            active.model_version,
            active.artifact_hash or "",
        )
    except (OSError, ValueError, EOFError, KeyError):
        active.review_recommended = True
        return unavailable_prediction(config)


def monitor_registered_predictions(
    db: Session,
    invoice_groups: list[InvoiceGroup],
    as_of_date: date,
) -> dict:
    rows = db.scalars(
        select(FutureTransactionPrediction).where(
            FutureTransactionPrediction.matured.is_(False)
        )
    ).all()
    matured = [row for row in rows if row.future_window_end <= as_of_date]
    valid = [group for group in invoice_groups if group.rfm_eligible]
    account_names = {
        item.account_key: item.standardized_account_name
        for item in db.scalars(select(DimAccount)).all()
    }
    for row in matured:
        account_name = account_names.get(row.account_key)
        occurred = any(
            group.standardized_account_name == account_name
            and pd.Timestamp(row.cutoff_date) < group.si_date <= pd.Timestamp(row.future_window_end)
            for group in valid
        )
        row.actual_class = FUTURE_TRANSACTION if occurred else NO_FUTURE_TRANSACTION
        row.correct = row.actual_class == row.predicted_class
        row.matured = True
        row.evaluated_on = as_of_date
        row.monitoring_status = "Evaluated"
    actual = [row.actual_class for row in matured if row.actual_class]
    predicted = [row.predicted_class for row in matured if row.actual_class]
    metrics = classification_metrics(actual, predicted) if actual else {}
    status = "evaluated" if actual else "pending"
    payload = {
        "status": status,
        "matured": len(actual),
        "pending": len(rows) - len(matured),
        "metrics": metrics,
    }
    active = active_model_version(db)
    if active:
        db.add(PredictiveMonitoringEvaluation(
            predictive_model_version_id=active.predictive_model_version_id,
            cutoff_date=min((row.cutoff_date for row in matured), default=None),
            status=status,
            review_recommended=False,
            payload=payload,
        ))
    return payload
