from datetime import date
from decimal import Decimal
from hashlib import sha256
import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.analytics.predictive.future_transaction import FEATURE_COLUMNS, NO_FUTURE_TRANSACTION
from app.core.analytics_config import AnalyticsConfig, DEFAULT_ANALYTICS_CONFIG
from app.db.models import Base, DimAccount, FutureTransactionPrediction, PredictiveModelVersion
from app.etl.invoices import InvoiceGroup
from app.services import model_lifecycle


def locked_pipeline() -> Pipeline:
    medians = list(model_lifecycle.LOCKED_IMPUTER_MEDIANS)
    frame = pd.DataFrame([medians, medians], columns=FEATURE_COLUMNS)
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", ExtraTreesClassifier(**model_lifecycle.LOCKED_PARAMETERS)),
    ])
    pipeline.fit(frame, [0, 1])
    return pipeline


def group():
    return InvoiceGroup(
        invoice_group_id="g", standardized_account_name="A", si_no="1",
        si_date=pd.Timestamp("2020-01-01"), si_amount=Decimal("100"),
        payment_status="Fully Paid", final_cr_date=pd.Timestamp("2020-01-10"),
        total_cr_amount=Decimal("100"), reconciliation_amount=Decimal("100"),
        reconciliation_difference=Decimal("0"), reconciled=True,
    )


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def exact_runtime(monkeypatch):
    monkeypatch.setattr(model_lifecycle.sklearn, "__version__", "1.8.0")


def test_wrong_artifact_hash_is_rejected_before_storage(db, tmp_path):
    path = tmp_path / "wrong.joblib"
    metadata = tmp_path / "model_metadata.json"
    joblib.dump(locked_pipeline(), path)
    metadata.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        model_lifecycle.register_frozen_model(db, path, metadata)


def test_raw_pipeline_registration_validates_hash_and_separate_metadata(db, tmp_path, monkeypatch):
    path = tmp_path / "extra_trees.joblib"
    metadata = tmp_path / "model_metadata.json"
    joblib.dump(locked_pipeline(), path)
    metadata.write_text(json.dumps({
        "development_metrics": {"macro_f1": 0.8015103929068558},
        "validation_report": {"balanced_accuracy": 0.817073754789272},
    }), encoding="utf-8")
    digest = sha256(path.read_bytes()).hexdigest()
    config = AnalyticsConfig(model_sha256=digest)
    monkeypatch.setattr(model_lifecycle.ModelStorage, "put",
                        lambda self, version, content: "private/model.joblib")
    record = model_lifecycle.register_frozen_model(db, path, metadata, config=config)
    assert record.model_version == "extra_trees_stage8"
    assert record.artifact_hash == digest
    assert record.retained_features == list(FEATURE_COLUMNS)
    assert record.preprocessing_config["deployment_imputation_values"]["recency_days"] == 750.5
    assert record.last_validation_date is None


def test_pipeline_contract_rejects_wrappers_runtime_features_parameters_medians_and_classes(monkeypatch):
    pipeline = locked_pipeline()
    assert model_lifecycle._validate_artifact(pipeline, DEFAULT_ANALYTICS_CONFIG) is pipeline
    with pytest.raises(ValueError, match="raw fitted"):
        model_lifecycle._validate_artifact({"pipeline": pipeline}, DEFAULT_ANALYTICS_CONFIG)
    monkeypatch.setattr(model_lifecycle.sklearn, "__version__", "1.7.1")
    with pytest.raises(ValueError, match="requires scikit-learn 1.8.0"):
        model_lifecycle._validate_artifact(pipeline, DEFAULT_ANALYTICS_CONFIG)
    monkeypatch.setattr(model_lifecycle.sklearn, "__version__", "1.8.0")
    wrong_order = locked_pipeline()
    wrong_order.named_steps["imputer"].feature_names_in_ = np.asarray(
        list(reversed(FEATURE_COLUMNS)), dtype=object
    )
    with pytest.raises(ValueError, match="predictors in order"):
        model_lifecycle._validate_artifact(wrong_order, DEFAULT_ANALYTICS_CONFIG)
    wrong_parameter = locked_pipeline()
    wrong_parameter.named_steps["model"].min_samples_leaf = 1
    with pytest.raises(ValueError, match="parameters"):
        model_lifecycle._validate_artifact(wrong_parameter, DEFAULT_ANALYTICS_CONFIG)
    wrong_medians = locked_pipeline()
    wrong_medians.named_steps["imputer"].statistics_[0] = 751.0
    with pytest.raises(ValueError, match="medians"):
        model_lifecycle._validate_artifact(wrong_medians, DEFAULT_ANALYTICS_CONFIG)
    wrong_classes = locked_pipeline()
    wrong_classes.named_steps["model"].classes_ = np.asarray([1, 2])
    with pytest.raises(ValueError, match="classes"):
        model_lifecycle._validate_artifact(wrong_classes, DEFAULT_ANALYTICS_CONFIG)


def test_current_scoring_does_not_train(db, monkeypatch):
    db.add(PredictiveModelVersion(
        model_version=DEFAULT_ANALYTICS_CONFIG.model_version,
        model_family=DEFAULT_ANALYTICS_CONFIG.model_family,
        status="active", artifact_hash=DEFAULT_ANALYTICS_CONFIG.model_sha256,
        oop_metrics={"macro_f1": 0.8},
    ))
    db.commit()
    pipeline = locked_pipeline()
    pipeline.predict = lambda frame: np.ones(len(frame), dtype=int)
    monkeypatch.setattr(model_lifecycle, "_load_artifact", lambda record, config: pipeline)
    result = model_lifecycle.future_transaction_for_current_run(
        db, [group()], pd.Timestamp("2020-12-31"), {"A"})
    assert result.predictions == {"A": NO_FUTURE_TRANSACTION}
    assert result.report == {"macro_f1": 0.8}


def test_monitoring_stays_pending_until_window_matures(db):
    account = DimAccount(standardized_account_name="A", display_name="A",
                         b2b_priority_eligible=True)
    db.add(account)
    db.flush()
    db.add(FutureTransactionPrediction(
        analysis_run_id="00000000-0000-4000-8000-000000000010",
        account_key=account.account_key, model_version="extra_trees_stage8",
        cutoff_date=date(2026, 9, 21), future_window_end=date(2027, 9, 21),
        predicted_class=NO_FUTURE_TRANSACTION,
    ))
    db.commit()
    result = model_lifecycle.monitor_registered_predictions(
        db, [group()], date(2027, 9, 20))
    assert result["status"] == "pending"
    assert result["matured"] == 0
    assert result["pending_calendar"] == 1
    assert result["pending_data_coverage"] == 0

@pytest.mark.parametrize(
    "as_of, coverage, expected_status, calendar, data_gap",
    [
        (date(2027, 9, 20), date(2027, 12, 31), "pending", 1, 0),
        (date(2027, 10, 1), date(2027, 9, 20), "pending", 0, 1),
        (date(2027, 10, 1), None, "pending", 0, 1),
        (date(2027, 10, 1), date(2027, 9, 21), "evaluated", 0, 0),
    ],
)
def test_monitoring_requires_calendar_and_verified_si_coverage(
    db, as_of, coverage, expected_status, calendar, data_gap,
):
    account = DimAccount(standardized_account_name="A", display_name="A")
    db.add(account)
    db.add(PredictiveModelVersion(
        model_version="extra_trees_stage8", status="active",
        artifact_hash=DEFAULT_ANALYTICS_CONFIG.model_sha256,
    ))
    db.flush()
    prediction = FutureTransactionPrediction(
        analysis_run_id="00000000-0000-4000-8000-000000000010",
        account_key=account.account_key, model_version="extra_trees_stage8",
        cutoff_date=date(2026, 9, 21), future_window_end=date(2027, 9, 21),
        predicted_class=NO_FUTURE_TRANSACTION,
    )
    db.add(prediction)
    db.flush()

    result = model_lifecycle.monitor_registered_predictions(
        db, [group()], as_of, coverage,
    )

    assert result["status"] == expected_status
    assert result["pending_calendar"] == calendar
    assert result["pending_data_coverage"] == data_gap
    assert prediction.matured is (expected_status == "evaluated")
    assert prediction.actual_class == (
        NO_FUTURE_TRANSACTION if expected_status == "evaluated" else None
    )


@pytest.mark.parametrize("future_si", [False, True])
def test_monitoring_uses_succeeding_si_not_late_cr(db, future_si):
    from dataclasses import replace

    account = DimAccount(standardized_account_name="A", display_name="A")
    db.add(account)
    db.add(PredictiveModelVersion(
        model_version="extra_trees_stage8", status="active",
        artifact_hash=DEFAULT_ANALYTICS_CONFIG.model_sha256,
    ))
    db.flush()
    prediction = FutureTransactionPrediction(
        analysis_run_id="00000000-0000-4000-8000-000000000010",
        account_key=account.account_key, model_version="extra_trees_stage8",
        cutoff_date=date(2025, 12, 31), future_window_end=date(2026, 12, 31),
        predicted_class=NO_FUTURE_TRANSACTION,
    )
    db.add(prediction)
    historic = replace(group(), final_cr_date=pd.Timestamp("2026-02-01"))
    groups = [historic]
    if future_si:
        groups.append(replace(
            group(), invoice_group_id="future", si_no="2",
            si_date=pd.Timestamp("2026-06-01"),
            final_cr_date=pd.Timestamp("2026-06-10"),
        ))
    db.flush()

    result = model_lifecycle.monitor_registered_predictions(
        db, groups, date(2027, 1, 15), date(2026, 12, 31),
    )

    assert result["matured"] == 1
    assert prediction.actual_class == (
        "Future Transaction" if future_si else NO_FUTURE_TRANSACTION
    )


def test_monitor_endpoint_without_successful_run_keeps_outcomes_pending(db):
    from app.auth.dependencies import AuthenticatedUser
    from app.main import monitor, MonitorRequest

    account = DimAccount(standardized_account_name="A", display_name="A")
    db.add(account)
    db.flush()
    prediction = FutureTransactionPrediction(
        analysis_run_id="00000000-0000-4000-8000-000000000010",
        account_key=account.account_key, model_version="extra_trees_stage8",
        cutoff_date=date(2025, 12, 31), future_window_end=date(2026, 12, 31),
        predicted_class=NO_FUTURE_TRANSACTION,
    )
    db.add(prediction)
    db.flush()

    result = monitor(
        MonitorRequest(as_of_date=date(2027, 1, 15)),
        AuthenticatedUser("00000000-0000-4000-8000-000000000001", "administrator"),
        db,
    )

    assert result["status"] == "pending"
    assert result["pending_data_coverage"] == 1
    assert result["reason"] == "No successful run with a verified complete-through reference."
    assert prediction.actual_class is None


def test_monitoring_records_original_prediction_model_version(db):
    from sqlalchemy import select
    from app.db.models import PredictiveMonitoringEvaluation

    account = DimAccount(standardized_account_name="A", display_name="A")
    db.add(account)
    old = PredictiveModelVersion(
        model_version="older_version", status="inactive", artifact_hash="a" * 64,
    )
    active = PredictiveModelVersion(
        model_version="extra_trees_stage8", status="active",
        artifact_hash=DEFAULT_ANALYTICS_CONFIG.model_sha256,
    )
    db.add_all([old, active])
    db.flush()
    second_account = DimAccount(standardized_account_name="B", display_name="B")
    db.add(second_account)
    db.flush()
    db.add_all([
        FutureTransactionPrediction(
            analysis_run_id="00000000-0000-4000-8000-000000000010",
            account_key=account.account_key, model_version="older_version",
            cutoff_date=date(2025, 12, 31), future_window_end=date(2026, 12, 31),
            predicted_class=NO_FUTURE_TRANSACTION,
        ),
        FutureTransactionPrediction(
            analysis_run_id="00000000-0000-4000-8000-000000000010",
            account_key=second_account.account_key, model_version="extra_trees_stage8",
            cutoff_date=date(2025, 12, 31), future_window_end=date(2026, 12, 31),
            predicted_class=NO_FUTURE_TRANSACTION,
        ),
    ])
    db.flush()

    result = model_lifecycle.monitor_registered_predictions(
        db, [group()], date(2027, 1, 15), date(2026, 12, 31),
    )

    records = db.scalars(select(PredictiveMonitoringEvaluation)).all()
    assert result["metrics"] == {}
    assert set(result["model_metrics"]) == {"older_version", "extra_trees_stage8"}
    assert {
        record.payload["model_version"]: record.predictive_model_version_id
        for record in records
    } == {
        "older_version": old.predictive_model_version_id,
        "extra_trees_stage8": active.predictive_model_version_id,
    }
