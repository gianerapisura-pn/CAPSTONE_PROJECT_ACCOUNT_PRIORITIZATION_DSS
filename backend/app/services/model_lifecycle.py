from __future__ import annotations

from dataclasses import replace
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

import joblib
import numpy as np
import pandas as pd
import sklearn
import catboost
from catboost import CatBoostClassifier
from sklearn.impute import SimpleImputer
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.analytics.predictive.future_transaction import (
    FEATURE_COLUMNS,
    FUTURE_TRANSACTION,
    NO_FUTURE_TRANSACTION,
    FutureTransactionResult,
    classification_metrics,
    score_frozen_artifact,
)
from catboost_model import FrozenCatBoost
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.db.models import (
    DimAccount,
    FutureTransactionPrediction,
    PredictiveBenchmarkRecord,
    PredictiveHorizonEvaluation,
    PredictiveModelVersion,
    PredictiveMonitoringEvaluation,
    PredictiveOOPEvaluation,
)
from app.etl.invoices import InvoiceGroup
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256,
    read_package_csv,
    read_package_json,
    read_package_member,
    verified_package,
)
from app.services.storage import ModelStorage

TARGET_DEFINITION = (
    "Future Transaction means at least one valid logical Sales Invoice after the cutoff "
    "and on or before the end of the next 12 months."
)
LOCKED_PARAMETERS = {
    "iterations": 150,
    "depth": 5,
    "learning_rate": 0.05,
    "loss_function": "Logloss",
    "auto_class_weights": "Balanced",
    "verbose": False,
    "random_seed": 42,
    "thread_count": 1,
    "allow_writing_files": False,
}
PUBLIC_PARAMETERS = {
    key: value for key, value in LOCKED_PARAMETERS.items()
    if key not in {"verbose", "thread_count", "allow_writing_files"}
}
LOCKED_IMPUTER_MEDIANS = (746.5, 0.0, 0.0, 10.0, 94.0, 0.0, 0.0)
LOCKED_DEVELOPMENT_METRICS = {
    "macro_f1": 0.7997344352724599,
    "classification_error": 0.0704674831809556,
    "accuracy": 0.9295325168190444,
    "balanced_accuracy": 0.8138836074861483,
    "future_transaction_f1": 0.6388888888888888,
    "future_transaction_recall": 0.6722222222222222,
    "mcc": 0.6025330115316253,
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


def _validate_artifact(artifact: object, config: AnalyticsConfig) -> FrozenCatBoost:
    if sklearn.__version__ != "1.8.0":
        raise ValueError(
            f"Frozen artifact requires scikit-learn 1.8.0; runtime is {sklearn.__version__}."
        )
    if catboost.__version__ != "1.2.8":
        raise ValueError(
            f"Frozen artifact requires CatBoost 1.2.8; runtime is {catboost.__version__}."
        )
    if type(artifact) is not FrozenCatBoost:
        raise ValueError("Frozen artifact must be the authorized FrozenCatBoost object.")
    if artifact.params != LOCKED_PARAMETERS:
        raise ValueError("Frozen CatBoost wrapper parameters do not match the locked contract.")
    if list(getattr(artifact, "named_steps", {})) != ["imputer", "model"]:
        raise ValueError("Frozen CatBoost must contain exactly the fitted imputer and model steps.")
    imputer = artifact.named_steps["imputer"]
    estimator = artifact.named_steps["model"]
    if not isinstance(imputer, SimpleImputer) or imputer.strategy != "median":
        raise ValueError("Frozen CatBoost imputer must be SimpleImputer(strategy='median').")
    if list(getattr(imputer, "feature_names_in_", [])) != list(FEATURE_COLUMNS):
        raise ValueError("Frozen artifact does not declare the seven locked predictors in order.")
    if not hasattr(imputer, "statistics_") or not np.allclose(
        np.asarray(imputer.statistics_, dtype=float),
        np.asarray(LOCKED_IMPUTER_MEDIANS, dtype=float),
        rtol=0.0,
        atol=1e-12,
        equal_nan=False,
    ):
        raise ValueError("Frozen CatBoost imputer medians do not match the locked values.")
    if not isinstance(estimator, CatBoostClassifier):
        raise ValueError("Frozen CatBoost model step must be CatBoostClassifier.")
    if list(getattr(estimator, "classes_", [])) != [0, 1]:
        raise ValueError("Frozen CatBoost classes must be exactly [0, 1].")
    if config.model_version != "catboost_stage8" or config.model_family != "CatBoost Classifier":
        raise ValueError("Runtime configuration does not identify the locked CatBoost model.")
    return artifact


def _load_artifact(
    record: PredictiveModelVersion,
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> FrozenCatBoost:
    if record.model_version != config.model_version:
        raise ValueError("Active artifact is not the locked CatBoost model version.")
    if record.artifact_hash != config.model_sha256:
        raise ValueError("Registered artifact SHA-256 is not the locked expected SHA-256.")
    return _validate_artifact(joblib.load(BytesIO(_artifact_bytes(record))), config)


def _json_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    return value


def _rows(frame: pd.DataFrame) -> list[dict]:
    return [
        {str(key): _json_value(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _find_column(frame: pd.DataFrame, candidates: set[str]) -> str | None:
    for column in frame.columns:
        normalized = re.sub(r"[^a-z0-9]+", "_", str(column).strip().casefold()).strip("_")
        if normalized in candidates:
            return str(column)
    return None


def seed_locked_predictive_evidence(
    db: Session,
    record: PredictiveModelVersion,
    package_content: bytes,
) -> dict:
    db.execute(delete(PredictiveHorizonEvaluation).where(PredictiveHorizonEvaluation.predictive_model_version_id == record.predictive_model_version_id))
    db.execute(delete(PredictiveBenchmarkRecord).where(PredictiveBenchmarkRecord.predictive_model_version_id == record.predictive_model_version_id))
    db.execute(delete(PredictiveOOPEvaluation).where(PredictiveOOPEvaluation.predictive_model_version_id == record.predictive_model_version_id))

    horizon = read_package_csv(package_content, "01_DATA/05_PREDICTIVE/02_HORIZON/horizon_summary.csv")
    if len(horizon) != 3 or set(horizon["horizon_months"].astype(int)) != {3, 6, 12}:
        raise ValueError("Locked horizon summary must contain exactly the 3-, 6-, and 12-month rows.")
    for source in _rows(horizon):
        db.add(PredictiveHorizonEvaluation(predictive_model_version_id=record.predictive_model_version_id, horizon_months=int(source["horizon_months"]), payload={"source_member": "horizon_summary.csv", **source}))

    canonical = read_package_csv(package_content, "01_DATA/05_PREDICTIVE/05_BENCHMARK/model_benchmark.csv")
    if len(canonical) != 22 or "family" not in canonical or canonical["family"].nunique() != 22:
        raise ValueError("Canonical locked benchmark must contain 22 unique classifier families.")
    for source in _rows(canonical):
        db.add(PredictiveBenchmarkRecord(predictive_model_version_id=record.predictive_model_version_id, benchmark_scope="canonical_21_classifiers_plus_majority", model_name=str(source["family"]), payload={"source_member": "model_benchmark.csv", **source}))

    confusion = read_package_csv(package_content, "01_DATA/05_PREDICTIVE/05_BENCHMARK/confusion_matrices.csv")
    selected_confusion = confusion.loc[confusion["family"] == "CatBoost"]
    if (len(selected_confusion) != 6
            or set(selected_confusion["outer_year"].astype(int)) != {2020, 2021, 2022}
            or set(selected_confusion["actual_class"]) != {"Future Transaction", "No Future Transaction"}
            or selected_confusion.groupby("outer_year").size().ne(2).any()):
        raise ValueError("Locked CatBoost confusion evidence must contain two classes for each outer year.")
    for source in _rows(selected_confusion):
        db.add(PredictiveBenchmarkRecord(
            predictive_model_version_id=record.predictive_model_version_id,
            benchmark_scope="selected_confusion_matrix", model_name="CatBoost",
            payload={"source_member": "confusion_matrices.csv",
                     "source_package_sha256": FINAL_PACKAGE_SHA256, **source},
        ))

    supplemental = read_package_csv(package_content, "01_DATA/05_PREDICTIVE/08_EXTENDED_AUDIT/supplemental_model_benchmark.csv")
    if len(supplemental) != 9 or "family" not in supplemental or supplemental["family"].nunique() != 9:
        raise ValueError("Supplemental locked benchmark must contain nine unique models.")
    for source in _rows(supplemental):
        db.add(PredictiveBenchmarkRecord(predictive_model_version_id=record.predictive_model_version_id, benchmark_scope="supplemental_nine_classifier_audit", model_name=str(source["family"]), payload={"source_member": "supplemental_model_benchmark.csv", **source}))

    later = read_package_csv(package_content, "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_summary.csv")
    if len(later) != 2:
        raise ValueError("Locked later-period summary must contain exactly two periods.")
    for source in _rows(later):
        parsed = pd.to_datetime(source.get("cutoff_date"), errors="coerce")
        db.add(PredictiveOOPEvaluation(predictive_model_version_id=record.predictive_model_version_id, oop_cutoff=None if pd.isna(parsed) else parsed.date(), payload={"source_member": "later_period_summary.csv", **source}))
    return {"horizons": 3, "canonical_benchmarks": 22, "selected_confusion_rows": 6,
            "supplemental_benchmarks": 9, "later_checks": 2}


def _metadata_date(metadata: dict, *keys: str) -> date | None:
    for key in keys:
        value = metadata.get(key)
        if value:
            parsed = pd.to_datetime(value, errors="coerce")
            if not pd.isna(parsed):
                return parsed.date()
    return None


def register_frozen_model(
    db: Session,
    local_artifact_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
    package_path: str | Path | None = None,
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
) -> PredictiveModelVersion:
    package_content: bytes | None = None
    if package_path is not None:
        _, package_content = verified_package(package_path, FINAL_PACKAGE_SHA256)
        content = read_package_member(package_content, "03_MODEL/catboost.joblib")
        metadata = read_package_json(package_content, "03_MODEL/model_metadata.json")
    else:
        if local_artifact_path is None or metadata_path is None:
            raise ValueError("Provide either a verified final package or both artifact and metadata paths.")
        artifact_path = Path(local_artifact_path).expanduser().resolve(strict=True)
        metadata_file = Path(metadata_path).expanduser().resolve(strict=True)
        content = artifact_path.read_bytes()
        metadata = json.loads(metadata_file.read_text(encoding="utf-8-sig"))
        if not isinstance(metadata, dict):
            raise ValueError("Model metadata must be a JSON object.")
    digest = sha256(content).hexdigest()
    if digest != config.model_sha256:
        raise ValueError(
            f"Artifact SHA-256 mismatch: expected {config.model_sha256}, received {digest}."
        )
    artifact = _validate_artifact(joblib.load(BytesIO(content)), config)
    existing = db.scalar(select(PredictiveModelVersion).where(
        PredictiveModelVersion.model_version == config.model_version
    ))
    if existing:
        raise ValueError(f"Model version {config.model_version} is already registered.")
    storage_path = ModelStorage().put(config.model_version, content)
    for prior in db.scalars(select(PredictiveModelVersion).where(
        PredictiveModelVersion.status == "active"
    )).all():
        prior.status = "retired"
    imputer = artifact.named_steps["imputer"]
    stage7 = metadata.get("stage7_selection_metrics") or {}
    validation_metrics = {
        "macro_f1": stage7.get("mean_macro_f1"),
        "classification_error": stage7.get("mean_classification_error"),
        "accuracy": stage7.get("mean_accuracy"),
        "balanced_accuracy": stage7.get("mean_balanced_accuracy"),
        "future_transaction_f1": stage7.get("mean_future_f1"),
        "future_transaction_recall": stage7.get("mean_future_recall"),
        "mcc": stage7.get("mean_mcc"),
    } if stage7 else (metadata.get("oop_metrics") or metadata.get("validation_report") or {})
    development_metrics = metadata.get("development_metrics") or validation_metrics or LOCKED_DEVELOPMENT_METRICS
    record = PredictiveModelVersion(
        model_version=config.model_version,
        model_family=config.model_family,
        model_parameters=PUBLIC_PARAMETERS,
        target_definition=TARGET_DEFINITION,
        primary_selection_metric="Equal-year mean outer Macro F1",
        decision_threshold=config.decision_threshold,
        status="active",
        trained_through_date=_metadata_date(metadata, "trained_through_date", "trained_through") or date(2022, 12, 31),
        selected_outcome_horizon=config.target_horizon_months,
        predictive_lookback_months=config.predictive_lookback_months,
        recent_transaction_months=config.recent_transaction_months,
        retained_features=list(FEATURE_COLUMNS),
        preprocessing_config={
            "imputation": "fitted median imputation from the locked training evidence",
            "deployment_imputation_values": {
                feature: float(value)
                for feature, value in zip(FEATURE_COLUMNS, imputer.statistics_, strict=True)
            },
            "scaling": None,
        },
        tree_hyperparameters=PUBLIC_PARAMETERS,
        random_seed=config.random_seed,
        development_metrics=development_metrics,
        oop_metrics=validation_metrics,
        last_validation_date=_metadata_date(metadata, "last_validation_date", "validation_evidence_date"),
        method_version=config.version,
        code_version=config.version,
        artifact_path=storage_path,
        artifact_hash=digest,
        review_recommended=False,
    )
    db.add(record)
    db.flush()
    if package_content is not None:
        seed_locked_predictive_evidence(db, record, package_content)
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
        result = score_frozen_artifact(
            invoice_groups,
            artifact,
            analysis_reference_date,
            eligible_accounts,
            active.model_version,
            active.artifact_hash or "",
            active.model_family or config.model_family,
        )
        return replace(result, report=dict(active.oop_metrics or {}))
    except (OSError, ValueError, EOFError, KeyError):
        active.review_recommended = True
        return unavailable_prediction(config)


def monitor_registered_predictions(
    db: Session,
    invoice_groups: list[InvoiceGroup],
    as_of_date: date,
    verified_data_complete_through: date | None = None,
) -> dict:
    rows = db.scalars(select(FutureTransactionPrediction).where(
        FutureTransactionPrediction.matured.is_(False)
    )).all()
    boundary = (
        min(as_of_date, verified_data_complete_through)
        if verified_data_complete_through else None
    )
    matured = [row for row in rows if boundary and row.future_window_end <= boundary]
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
    by_version = {
        version: [row for row in matured if row.model_version == version]
        for version in {row.model_version for row in matured}
    }
    metrics_by_version = {
        version: classification_metrics(
            [row.actual_class for row in version_rows],
            [row.predicted_class for row in version_rows],
        )
        for version, version_rows in by_version.items()
    }
    status = "evaluated" if matured else "pending"
    payload = {
        "status": status,
        "matured": len(matured),
        "pending": len(rows) - len(matured),
        "metrics": next(iter(metrics_by_version.values())) if len(metrics_by_version) == 1 else {},
        "model_metrics": metrics_by_version,
        "verified_data_complete_through": (
            verified_data_complete_through.isoformat() if verified_data_complete_through else None
        ),
        "pending_calendar": sum(row.future_window_end > as_of_date for row in rows),
        "pending_data_coverage": sum(
            row.future_window_end <= as_of_date
            and (boundary is None or row.future_window_end > boundary)
            for row in rows
        ),
        "reason": (
            "No successful run with a verified complete-through reference."
            if verified_data_complete_through is None else None
        ),
    }
    for version, version_rows in by_version.items():
        model = db.scalar(select(PredictiveModelVersion).where(
            PredictiveModelVersion.model_version == version
        ))
        if model is None:
            continue
        db.add(PredictiveMonitoringEvaluation(
            predictive_model_version_id=model.predictive_model_version_id,
            cutoff_date=min(row.cutoff_date for row in version_rows),
            status="evaluated",
            review_recommended=False,
            payload={**payload, "model_version": version, "metrics": metrics_by_version[version]},
        ))
    return payload
