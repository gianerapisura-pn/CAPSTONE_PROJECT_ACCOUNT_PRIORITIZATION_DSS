from datetime import date
from decimal import Decimal
from hashlib import sha256
import joblib
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.analytics.predictive.future_transaction import FEATURE_COLUMNS, NO_FUTURE_TRANSACTION
from app.core.analytics_config import AnalyticsConfig, DEFAULT_ANALYTICS_CONFIG
from app.db.models import Base, DimAccount, FutureTransactionPrediction, PredictiveModelVersion
from app.etl.invoices import InvoiceGroup
from app.services import model_lifecycle


class DummyModel:
    def predict(self, frame):
        return [0] * len(frame)


def group():
    return InvoiceGroup(
        invoice_group_id="g", standardized_account_name="A", si_no="1",
        si_date=pd.Timestamp("2020-01-01"), si_amount=Decimal("100"),
        payment_status="Fully Paid", final_cr_date=pd.Timestamp("2020-01-10"),
        total_cr_amount=Decimal("100"), reconciliation_amount=Decimal("100"),
        reconciliation_difference=Decimal("0"), reconciled=True)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_wrong_artifact_hash_is_rejected_before_storage(db, tmp_path):
    path = tmp_path / "wrong.joblib"
    joblib.dump({"model": DummyModel(), "feature_columns": list(FEATURE_COLUMNS)}, path)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        model_lifecycle.register_frozen_model(db, path)


def test_registration_validates_exact_hash_version_and_metadata(db, tmp_path, monkeypatch):
    path = tmp_path / "model.joblib"
    joblib.dump({
        "model": DummyModel(), "feature_columns": list(FEATURE_COLUMNS),
        "model_version": "extra_trees_stage8",
        "model_family": "Extra Trees Classifier",
        "validation_report": {"macro_f1": .8},
    }, path)
    digest = sha256(path.read_bytes()).hexdigest()
    config = AnalyticsConfig(model_sha256=digest)
    monkeypatch.setattr(model_lifecycle.sklearn, "__version__", "1.8.0")
    monkeypatch.setattr(model_lifecycle.ModelStorage, "put",
                        lambda self, version, content: "private/model.joblib")
    record = model_lifecycle.register_frozen_model(db, path, config)
    assert record.model_version == "extra_trees_stage8"
    assert record.model_family == "Extra Trees Classifier"
    assert record.artifact_hash == digest
    assert record.retained_features == list(FEATURE_COLUMNS)
    assert record.decision_threshold == .5


def test_current_scoring_does_not_train(db, monkeypatch):
    db.add(PredictiveModelVersion(
        model_version=DEFAULT_ANALYTICS_CONFIG.model_version,
        model_family=DEFAULT_ANALYTICS_CONFIG.model_family,
        status="active", artifact_hash=DEFAULT_ANALYTICS_CONFIG.model_sha256))
    db.commit()
    monkeypatch.setattr(model_lifecycle, "_load_artifact",
                        lambda record, config: {
                            "model": DummyModel(),
                            "feature_columns": list(FEATURE_COLUMNS)})
    result = model_lifecycle.future_transaction_for_current_run(
        db, [group()], pd.Timestamp("2020-12-31"), {"A"})
    assert result.predictions == {"A": NO_FUTURE_TRANSACTION}


def test_monitoring_stays_pending_until_window_matures(db):
    account = DimAccount(standardized_account_name="A", display_name="A",
                         b2b_priority_eligible=True)
    db.add(account); db.flush()
    db.add(FutureTransactionPrediction(
        analysis_run_id="00000000-0000-4000-8000-000000000010",
        account_key=account.account_key, model_version="extra_trees_stage8",
        cutoff_date=date(2026, 9, 21), future_window_end=date(2027, 9, 21),
        predicted_class=NO_FUTURE_TRANSACTION))
    db.commit()
    result = model_lifecycle.monitor_registered_predictions(
        db, [group()], date(2027, 9, 20))
    assert result == {"status": "pending", "matured": 0, "pending": 1, "metrics": {}}
