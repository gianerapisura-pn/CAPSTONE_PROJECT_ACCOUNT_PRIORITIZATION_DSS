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
    assert result == {"status": "pending", "matured": 0, "pending": 1, "metrics": {}}