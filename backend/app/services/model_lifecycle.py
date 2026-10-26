from __future__ import annotations

from dataclasses import replace
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from math import isclose, isfinite
from pathlib import Path
import re
from zipfile import ZipFile

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
    AnalyticsRun,
    AuditLog,
    DimAccount,
    FutureTransactionPrediction,
    PredictiveBenchmarkRecord,
    PredictiveHorizonEvaluation,
    PredictiveModelVersion,
    PredictiveMonitoringEvaluation,
    PredictiveOOPEvaluation,
    PredictiveStudyPrediction,
)
from app.db.repository import audit
from app.etl.invoices import InvoiceGroup
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256,
    PRIOR_ACTIVE_PACKAGE_SHA256,
    STUDY_PREDECESSOR_PACKAGE_SHA256,
    read_package_csv,
    read_package_json,
    read_package_member,
    verified_package,
)
from app.services.storage import ModelStorage
from app.services.prescriptive_evidence import (
    seed_prescriptive_validation_evidence, unchanged_prescriptive_evidence,
)
from app.services.study_predictions import (
    MODEL_VERSION, REVISION_AUDIT_ACTION, final_study_prediction_payload, seed_final_study_predictions,
    study_snapshot_digest, validate_study_prediction_package,
)

TARGET_DEFINITION = (
    "With Future Sales means at least one valid logical Sales Invoice after the cutoff "
    "and on or before the end of the next 12 months."
)
MONITOR_MIN_OUTCOMES = 30
MONITOR_MACRO_F1_DROP_FOR_REVIEW = 0.10


def _performance_review_signal(
    model: PredictiveModelVersion, metrics: dict | None, outcome_count: int,
) -> tuple[float | None, bool, bool]:
    baseline_raw = (model.oop_metrics or {}).get("macro_f1")
    try:
        baseline = float(baseline_raw) if baseline_raw is not None else None
    except (TypeError, ValueError):
        baseline = None
    if baseline is not None and not isfinite(baseline):
        baseline = None
    enough_evidence = bool(
        metrics and outcome_count >= MONITOR_MIN_OUTCOMES
        and metrics["macro_f1"] is not None and baseline is not None
    )
    review = bool(
        enough_evidence
        and metrics["macro_f1"] < baseline - MONITOR_MACRO_F1_DROP_FOR_REVIEW
    )
    return baseline, enough_evidence, review


def operational_performance_summary(db: Session, model: PredictiveModelVersion) -> dict:
    """Compare the earliest published prediction per account/cutoff with matured SI outcomes."""
    rows = db.scalars(select(FutureTransactionPrediction).where(
        FutureTransactionPrediction.model_version == model.model_version,
        FutureTransactionPrediction.matured.is_(True),
    )).all()
    runs = {run.analysis_run_id: run for run in db.scalars(select(AnalyticsRun).where(
        AnalyticsRun.analysis_run_id.in_({row.analysis_run_id for row in rows}),
    )).all()} if rows else {}
    earliest = {}
    for row in sorted(rows, key=lambda item: (
        str(runs[item.analysis_run_id].started_at) if item.analysis_run_id in runs else "",
        item.future_transaction_prediction_id,
    )):
        if row.actual_class in (FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION) and row.predicted_class in (
            FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION,
        ):
            earliest.setdefault((row.account_key, row.cutoff_date), row)
    evaluated = list(earliest.values())
    metrics = classification_metrics(
        [row.actual_class for row in evaluated],
        [row.predicted_class for row in evaluated],
    ) if evaluated else None
    baseline, enough_evidence, review = _performance_review_signal(
        model, metrics, len(evaluated),
    )
    return {
        "status": "evaluated" if enough_evidence else "insufficient_evidence",
        "evaluated_account_cutoffs": len(evaluated),
        "forecast_cutoffs": len({row.cutoff_date for row in evaluated}),
        "metrics": metrics,
        "historical_macro_f1": baseline,
        "review_recommended": review,
        "minimum_outcomes_for_review": MONITOR_MIN_OUTCOMES,
        "macro_f1_drop_for_review": MONITOR_MACRO_F1_DROP_FOR_REVIEW,
    }
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
LATER_MEMBER = "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_summary.csv"
LATER_EXPECTED = {
    "2023-12-31": {
        "future_window_end": "2024-12-31", "observations": 77,
        "cm_future_future": 6, "cm_future_no_future": 3,
        "cm_no_future_future": 5, "cm_no_future_no_future": 63,
        "macro_f1": 0.7701492537313432,
    },
    "2024-12-31": {
        "future_window_end": "2025-12-31", "observations": 79,
        "cm_future_future": 4, "cm_future_no_future": 1,
        "cm_no_future_future": 5, "cm_no_future_no_future": 69,
        "macro_f1": 0.7648809523809523,
    },
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


OPTIONAL_VALIDATION_MEMBERS = (
    ("development_class_profile.csv", "01_DATA/05_PREDICTIVE/04_DEVELOPMENT/development_class_profile.csv", 5),
    ("lookback_summary.csv", "05_QA/final_design_tests/lookback_summary.csv", 5),
    ("lookback_folds.csv", "05_QA/final_design_tests/lookback_folds.csv", 15),
    ("model_folds.csv", "01_DATA/05_PREDICTIVE/05_BENCHMARK/model_folds.csv", 3),
)


def _additional_validation_rows(content: bytes) -> list[dict]:
    with ZipFile(BytesIO(content)) as archive:
        names = set(archive.namelist())
    rows = []
    for label, member, expected_count in OPTIONAL_VALIDATION_MEMBERS:
        if not any(name.endswith("/" + member) for name in names):
            continue
        frame = read_package_csv(content, member)
        if label == "model_folds.csv":
            frame = frame.loc[frame["family"] == "CatBoost"]
        if len(frame) != expected_count:
            raise ValueError(f"Locked {label} has an unexpected row count.")
        rows.extend({"source_member": label, **source} for source in _rows(frame))
    return rows


def _find_column(frame: pd.DataFrame, candidates: set[str]) -> str | None:
    for column in frame.columns:
        normalized = re.sub(r"[^a-z0-9]+", "_", str(column).strip().casefold()).strip("_")
        if normalized in candidates:
            return str(column)
    return None


def validated_later_checks(package_content: bytes) -> list[dict]:
    later = read_package_csv(package_content, LATER_MEMBER)
    predictions = read_package_csv(
        package_content, "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_predictions.csv"
    )
    matrices = read_package_csv(
        package_content, "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_confusion_matrices.csv"
    )
    features = read_package_csv(
        package_content, "01_DATA/05_PREDICTIVE/07_LATER_CHECKS/later_period_features.csv"
    )
    required = {
        "period", "role", "cutoff_date", "future_window_end", "observations",
        "eligible_accounts", "actual_future_transaction", "actual_no_future_transaction",
        "predicted_future_transaction", "predicted_no_future_transaction",
        "cm_future_future", "cm_future_no_future", "cm_no_future_future",
        "cm_no_future_no_future", "accuracy", "classification_error", "macro_f1",
        "balanced_accuracy", "future_precision", "future_recall", "future_f1", "mcc",
    }
    if len(later) != 2 or not required.issubset(later.columns):
        raise ValueError("Locked later-period summary must contain exactly two complete periods.")
    if not {"period", "cutoff_date", "future_window_end", "account_key", "actual_target", "predicted_target"}.issubset(predictions.columns):
        raise ValueError("Later-period account predictions are incomplete.")
    if not {"period", "actual_class", "predicted_future_transaction", "predicted_no_future_transaction"}.issubset(matrices.columns):
        raise ValueError("Later-period confusion matrices are incomplete.")
    if not {"period", "account_key", "cutoff_date", *FEATURE_COLUMNS}.issubset(features.columns):
        raise ValueError("Later-period feature evidence is incomplete.")
    sources = _rows(later)
    if {str(row["cutoff_date"]) for row in sources} != set(LATER_EXPECTED):
        raise ValueError("Later-period main confirmations must use 2023 and December 2024 cutoffs.")
    if len({str(row["period"]) for row in sources}) != 2:
        raise ValueError("Later-period confirmations have duplicate period names.")
    for row in sources:
        cutoff = str(row["cutoff_date"])
        expected = LATER_EXPECTED[cutoff]
        year = cutoff[:4]
        if (row["period"] != f"{year} confirmation" or
                row["role"] != "Later-period confirmation" or
                str(row["future_window_end"]) != expected["future_window_end"]):
            raise ValueError("Later-period confirmation identity or outcome window is invalid.")
        counts = {key: int(row[key]) for key in (
            "observations", "eligible_accounts", "actual_future_transaction",
            "actual_no_future_transaction", "predicted_future_transaction",
            "predicted_no_future_transaction", "cm_future_future",
            "cm_future_no_future", "cm_no_future_future", "cm_no_future_no_future",
        )}
        if any(counts[key] != value for key, value in expected.items() if key in counts):
            raise ValueError("Later-period confusion counts differ from approved evidence.")
        n = counts["observations"]
        ff, fn = counts["cm_future_future"], counts["cm_future_no_future"]
        nf, nn = counts["cm_no_future_future"], counts["cm_no_future_no_future"]
        if (counts["eligible_accounts"] != n or ff + fn + nf + nn != n or
                counts["actual_future_transaction"] != ff + fn or
                counts["actual_no_future_transaction"] != nf + nn or
                counts["predicted_future_transaction"] != ff + nf or
                counts["predicted_no_future_transaction"] != fn + nn):
            raise ValueError("Later-period class totals do not reconcile.")
        metrics = {
            "accuracy": (ff + nn) / n,
            "classification_error": (fn + nf) / n,
            "macro_f1": expected["macro_f1"],
            "balanced_accuracy": (ff / (ff + fn) + nn / (nf + nn)) / 2,
            "future_precision": ff / (ff + nf),
            "future_recall": ff / (ff + fn),
            "future_f1": 2 * ff / (2 * ff + fn + nf),
            "mcc": (ff * nn - fn * nf) / (((ff + nf) * (ff + fn) * (nn + nf) * (nn + fn)) ** 0.5),
        }
        if any(not isclose(float(row[key]), value, rel_tol=0, abs_tol=1e-12)
               for key, value in metrics.items()):
            raise ValueError("Later-period classification metrics do not reconcile.")
        period_rows = predictions.loc[predictions["period"] == row["period"]]
        feature_rows = features.loc[features["period"] == row["period"]]
        if (len(period_rows) != n or period_rows["account_key"].nunique() != n or
                set(period_rows["cutoff_date"]) != {cutoff} or
                set(period_rows["future_window_end"]) != {expected["future_window_end"]}):
            raise ValueError("Later-period account prediction window or population is invalid.")
        if (len(feature_rows) != n or set(feature_rows["account_key"]) != set(period_rows["account_key"]) or
                set(feature_rows["cutoff_date"]) != {cutoff}):
            raise ValueError("Later-period feature evidence disagrees with the predictions.")
        for actual, predicted, count in (
            ("With Future Sales", "With Future Sales", ff),
            ("With Future Sales", "With No Future Sales", fn),
            ("With No Future Sales", "With Future Sales", nf),
            ("With No Future Sales", "With No Future Sales", nn),
        ):
            if len(period_rows.loc[
                (period_rows["actual_target"] == actual) &
                (period_rows["predicted_target"] == predicted)
            ]) != count:
                raise ValueError("Later-period account predictions disagree with the summary.")
        matrix = matrices.loc[matrices["period"] == row["period"]]
        if len(matrix) != 2 or set(matrix["actual_class"]) != {
            "With Future Sales", "With No Future Sales"
        }:
            raise ValueError("Later-period confusion matrix is incomplete.")
        for actual, future, no_future in (
            ("With Future Sales", ff, fn), ("With No Future Sales", nf, nn)
        ):
            item = matrix.loc[matrix["actual_class"] == actual].iloc[0]
            if (int(item["predicted_future_transaction"]) != future or
                    int(item["predicted_no_future_transaction"]) != no_future):
                raise ValueError("Later-period confusion matrix disagrees with the summary.")
    if (len(predictions) != sum(item["observations"] for item in sources) or
            len(features) != len(predictions) or len(matrices) != 4):
        raise ValueError("Later-period evidence includes unexpected extra observations.")
    return sources


def seed_locked_predictive_evidence(
    db: Session,
    record: PredictiveModelVersion,
    package_content: bytes,
) -> dict:
    later = validated_later_checks(package_content)
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
            or set(selected_confusion["actual_class"]) != {"With Future Sales", "With No Future Sales"}
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

    for source in _additional_validation_rows(package_content):
        db.add(PredictiveBenchmarkRecord(
            predictive_model_version_id=record.predictive_model_version_id,
            benchmark_scope="supplemental_validation_context",
            model_name=f"{source['source_member']}:{source.get('cutoff_year', source.get('lookback_months'))}:{source.get('outer_year', '')}",
            payload=source,
        ))

    for source in later:
        db.add(PredictiveOOPEvaluation(
            predictive_model_version_id=record.predictive_model_version_id,
            oop_cutoff=date.fromisoformat(source["cutoff_date"]),
            payload={"source_member": LATER_MEMBER,
                     "source_package_sha256": FINAL_PACKAGE_SHA256, **source},
        ))
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
    if package_content is not None:
        validated_later_checks(package_content)
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


def _unchanged_development_evidence(db: Session, record: PredictiveModelVersion,
                                    content: bytes) -> bool:
    horizons = db.scalars(select(PredictiveHorizonEvaluation).where(
        PredictiveHorizonEvaluation.predictive_model_version_id == record.predictive_model_version_id
    )).all()
    benchmarks = db.scalars(select(PredictiveBenchmarkRecord).where(
        PredictiveBenchmarkRecord.predictive_model_version_id == record.predictive_model_version_id
    )).all()
    if not horizons and not benchmarks:
        return False
    expected_horizons = [
        {"source_member": "horizon_summary.csv", **row}
        for row in _rows(read_package_csv(content, "01_DATA/05_PREDICTIVE/02_HORIZON/horizon_summary.csv"))
    ]
    benchmark_sources = (
        ("model_benchmark.csv", "01_DATA/05_PREDICTIVE/05_BENCHMARK/model_benchmark.csv", None),
        ("confusion_matrices.csv", "01_DATA/05_PREDICTIVE/05_BENCHMARK/confusion_matrices.csv", "CatBoost"),
        ("supplemental_model_benchmark.csv", "01_DATA/05_PREDICTIVE/08_EXTENDED_AUDIT/supplemental_model_benchmark.csv", None),
    )
    expected_benchmarks = []
    for label, member, family in benchmark_sources:
        frame = read_package_csv(content, member)
        if family:
            frame = frame.loc[frame["family"] == family]
        expected_benchmarks.extend({"source_member": label, **row} for row in _rows(frame))
    additional = _additional_validation_rows(content)
    actual_benchmarks = [
        {key: value for key, value in row.payload.items() if key != "source_package_sha256"}
        for row in benchmarks
    ]
    core_unchanged = sorted(actual_benchmarks, key=str) == sorted(expected_benchmarks, key=str)
    complete_unchanged = sorted(actual_benchmarks, key=str) == sorted(
        expected_benchmarks + additional, key=str
    )
    if (len(horizons) != 3 or not (core_unchanged or complete_unchanged) or
            sorted([row.payload for row in horizons], key=str) != sorted(expected_horizons, key=str) or
            any(row.payload.get("source_package_sha256") not in (
                FINAL_PACKAGE_SHA256, PRIOR_ACTIVE_PACKAGE_SHA256, STUDY_PREDECESSOR_PACKAGE_SHA256
            ) for row in benchmarks if row.payload.get("source_member") == "confusion_matrices.csv")):
        raise ValueError("Existing development evidence differs from the revised package.")
    return True


def _append_missing_validation_context(db: Session, record: PredictiveModelVersion,
                                       content: bytes) -> None:
    existing = db.scalars(select(PredictiveBenchmarkRecord).where(
        PredictiveBenchmarkRecord.predictive_model_version_id == record.predictive_model_version_id
    )).all()
    if any(row.benchmark_scope == "supplemental_validation_context" for row in existing):
        return
    for source in _additional_validation_rows(content):
        db.add(PredictiveBenchmarkRecord(
            predictive_model_version_id=record.predictive_model_version_id,
            benchmark_scope="supplemental_validation_context",
            model_name=f"{source['source_member']}:{source.get('cutoff_year', source.get('lookback_months'))}:{source.get('outer_year', '')}",
            payload=source,
        ))


def sync_revised_package_evidence(db: Session, package_path: str | Path,
                                  actor: str | None = None) -> dict:
    _, content = verified_package(package_path, FINAL_PACKAGE_SHA256)
    if sha256(read_package_member(content, "03_MODEL/catboost.joblib")).hexdigest() != DEFAULT_ANALYTICS_CONFIG.model_sha256:
        raise ValueError("Revised package contains a different frozen model artifact.")
    record = db.scalar(select(PredictiveModelVersion).where(
        PredictiveModelVersion.model_version == MODEL_VERSION
    ))
    if (record is None or record.status != "active" or
            record.artifact_hash != DEFAULT_ANALYTICS_CONFIG.model_sha256):
        raise ValueError("The approved active CatBoost model must already be registered.")
    _load_artifact(record)
    validate_study_prediction_package(content)
    later = validated_later_checks(content)
    development_exists = _unchanged_development_evidence(db, record, content)
    prescriptive_exists = unchanged_prescriptive_evidence(db, content)
    study = seed_final_study_predictions(db, package_path)
    old_rows = db.scalars(select(PredictiveOOPEvaluation).where(
        PredictiveOOPEvaluation.predictive_model_version_id == record.predictive_model_version_id
    )).all()
    current = len(old_rows) == 2 and {
        (row.payload.get("cutoff_date"), row.payload.get("source_package_sha256"))
        for row in old_rows
    } == {(source["cutoff_date"], FINAL_PACKAGE_SHA256) for source in later}
    if current and any(
        row.payload != {"source_member": LATER_MEMBER,
                        "source_package_sha256": FINAL_PACKAGE_SHA256,
                        **next(source for source in later if source["cutoff_date"] == row.payload["cutoff_date"])}
        for row in old_rows
    ):
        raise ValueError("Persisted current later-period evidence differs from the verified package.")
    if old_rows and not current:
        by_cutoff = {row.payload.get("cutoff_date"): row.payload for row in old_rows}
        if (len(old_rows) != 2 or set(by_cutoff) != {"2023-12-31", "2024-08-13"} or
                by_cutoff["2023-12-31"].get("macro_f1") != LATER_EXPECTED["2023-12-31"]["macro_f1"] or
                by_cutoff["2024-08-13"].get("period") != "2024-08-13 confirmation" or
                by_cutoff["2024-08-13"].get("observations") != 79 or
                not isclose(float(by_cutoff["2024-08-13"].get("macro_f1", -1)),
                            0.7710144927536231, rel_tol=0, abs_tol=1e-12)):
            raise ValueError("Existing later-period evidence is not the recognized predecessor.")
    if not development_exists:
        seed_locked_predictive_evidence(db, record, content)
    else:
        _append_missing_validation_context(db, record, content)
    if development_exists and not current:
        db.execute(delete(PredictiveOOPEvaluation).where(
            PredictiveOOPEvaluation.predictive_model_version_id == record.predictive_model_version_id
        ))
        for source in later:
            db.add(PredictiveOOPEvaluation(
                predictive_model_version_id=record.predictive_model_version_id,
                oop_cutoff=date.fromisoformat(source["cutoff_date"]),
                payload={"source_member": LATER_MEMBER,
                         "source_package_sha256": FINAL_PACKAGE_SHA256, **source},
            ))
    if not prescriptive_exists:
        seed_prescriptive_validation_evidence(db, package_path)
    study_rows = db.scalars(select(PredictiveStudyPrediction).where(
        PredictiveStudyPrediction.model_version == MODEL_VERSION,
        PredictiveStudyPrediction.forecast_origin == date(2025, 12, 31),
    )).all()
    proofs = db.scalars(select(AuditLog).where(
        AuditLog.action == REVISION_AUDIT_ACTION,
        AuditLog.entity_type == "predictive_model",
        AuditLog.entity_id == MODEL_VERSION,
    )).all()
    digest = study_snapshot_digest(study_rows)
    if not any(item.details.get("package_sha256") == FINAL_PACKAGE_SHA256 and
               item.details.get("study_snapshot_sha256") == digest for item in proofs):
        audit(db, actor, REVISION_AUDIT_ACTION, "predictive_model", MODEL_VERSION, {
            "package_sha256": FINAL_PACKAGE_SHA256,
            "study_predecessor_sha256": STUDY_PREDECESSOR_PACKAGE_SHA256,
            "study_snapshot_sha256": digest,
            "later_member": LATER_MEMBER,
            "supplementary_member": "05_QA/final_design_tests/later_period_design_check.csv",
            "prescriptive_evidence_unchanged": prescriptive_exists,
        })
    return {"model_version": MODEL_VERSION, "study": study,
            "later_checks": 2, "prescriptive_evidence_unchanged": prescriptive_exists}


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


def _monitor_final_study_outcomes(
    db: Session,
    valid_groups: list[InvoiceGroup],
    as_of_date: date,
    verified_data_complete_through: date | None,
    source_run_id: str | None,
) -> str:
    study = final_study_prediction_payload(db)
    if study["status"] != "Validated" or len(study["predictions"]) != 83:
        return "unavailable"
    window_end = date.fromisoformat(study["future_window_end"])
    if (as_of_date < window_end or verified_data_complete_through is None
            or verified_data_complete_through < window_end or source_run_id is None):
        return "pending"
    run = db.get(AnalyticsRun, source_run_id)
    if (run is None or run.status != "successful" or run.analysis_reference_date is None
            or run.analysis_reference_date < window_end):
        return "pending"
    model = db.scalar(select(PredictiveModelVersion).where(
        PredictiveModelVersion.model_version == study["model_version"],
    ))
    if model is None or model.artifact_hash != study["artifact_hash"]:
        return "unavailable"
    origin = date.fromisoformat(study["forecast_origin"])
    existing = db.scalars(select(PredictiveMonitoringEvaluation).where(
        PredictiveMonitoringEvaluation.predictive_model_version_id == model.predictive_model_version_id,
        PredictiveMonitoringEvaluation.cutoff_date == origin,
    )).all()
    if any(row.payload.get("scope") == "final_study_forecast" for row in existing):
        return "evaluated"
    start = pd.Timestamp(study["future_window_start"])
    end = pd.Timestamp(window_end)
    observed = {
        group.standardized_account_name for group in valid_groups
        if start <= group.si_date <= end
    }
    predictions = study["predictions"]
    accounts = sorted(predictions)
    actual = [FUTURE_TRANSACTION if account in observed else NO_FUTURE_TRANSACTION
              for account in accounts]
    predicted = [predictions[account] for account in accounts]
    metrics = classification_metrics(actual, predicted)
    baseline, enough_evidence, review = _performance_review_signal(model, metrics, len(accounts))
    if review:
        model.review_recommended = True
    db.add(PredictiveMonitoringEvaluation(
        predictive_model_version_id=model.predictive_model_version_id,
        cutoff_date=origin,
        status="evaluated",
        review_recommended=review,
        payload={
            "scope": "final_study_forecast",
            "source_analysis_run_id": source_run_id,
            "source_package_hash": study["source_package_hash"],
            "verified_complete_through": verified_data_complete_through.isoformat(),
            "forecast_origin": study["forecast_origin"],
            "future_window_start": study["future_window_start"],
            "future_window_end": study["future_window_end"],
            "account_count": len(accounts),
            "metrics": metrics,
            "historical_macro_f1": baseline,
            "comparison_status": "evaluated" if enough_evidence else "insufficient_evidence",
            "review_recommended": review,
        },
    ))
    return "evaluated"


def monitor_registered_predictions(
    db: Session,
    invoice_groups: list[InvoiceGroup],
    as_of_date: date,
    verified_data_complete_through: date | None = None,
    source_run_id: str | None = None,
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
    study_outcome_status = _monitor_final_study_outcomes(
        db, valid, as_of_date, verified_data_complete_through, source_run_id,
    )
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
    db.flush()
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
    active = active_model_version(db)
    versions = set(by_version)
    if active is not None:
        versions.add(active.model_version)
    performance_by_version = {}
    for version in versions:
        model = active if active is not None and active.model_version == version else db.scalar(
            select(PredictiveModelVersion).where(PredictiveModelVersion.model_version == version)
        )
        if model is None:
            continue
        summary = operational_performance_summary(db, model)
        performance_by_version[version] = summary
        if summary["review_recommended"]:
            model.review_recommended = True
    status = "evaluated" if matured or study_outcome_status == "evaluated" else "pending"
    payload = {
        "status": status,
        "matured": len(matured),
        "pending": len(rows) - len(matured),
        "metrics": next(iter(metrics_by_version.values())) if len(metrics_by_version) == 1 else {},
        "model_metrics": metrics_by_version,
        "performance_by_version": performance_by_version,
        "active_model_performance": performance_by_version.get(active.model_version) if active else None,
        "review_recommended": bool(active and active.review_recommended),
        "study_outcome_status": study_outcome_status,
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
