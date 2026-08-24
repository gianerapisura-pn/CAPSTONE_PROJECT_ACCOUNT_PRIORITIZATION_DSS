from decimal import Decimal
from hashlib import sha256
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.analytics.predictive.cart import CartResult
from app.db.models import Base, PredictiveModelVersion, PredictiveMonitoringEvaluation
from app.etl.invoices import SourceRow, group_invoices
from app.services import model_lifecycle


def invoice_groups():
    return group_invoices([SourceRow(
        customer_name_raw="A", standardized_account_name="A", si_no="SI-1",
        si_date=pd.Timestamp("2030-01-01"), si_amount=Decimal("100"),
        cr_no="CR-1", cr_date=pd.Timestamp("2030-01-02"),
        cr_amount=Decimal("100"), ewt=Decimal("0"), payment_mode="Bank",
        payment_status_raw="Fully Paid", payment_status="Fully Paid",
        is_cancelled=False,
    )])


def active_record():
    return PredictiveModelVersion(
        model_version="cart-frozen-1", status="active", retained_features=["recency_days"],
        preprocessing_config={}, tree_hyperparameters={}, development_metrics={},
        oop_metrics={}, artifact_path="private/model.joblib", artifact_hash="hash",
    )


def test_active_artifact_hash_mismatch_is_rejected(monkeypatch):
    record = active_record()
    record.artifact_hash = sha256(b"expected artifact").hexdigest()
    monkeypatch.setattr(
        model_lifecycle,
        "ModelStorage",
        lambda: SimpleNamespace(get=lambda _: b"tampered artifact"),
    )
    with pytest.raises(ValueError, match="hash verification failed"):
        model_lifecycle._load_artifact(record)


def test_current_scoring_uses_active_model_without_retraining(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    expected = CartResult("Validated", 6, ["recency_days"], {}, {"A": "Lower"}, model_version="cart-frozen-1")
    with Session(engine) as db:
        db.add(active_record())
        db.commit()
        monkeypatch.setattr(model_lifecycle, "_load_artifact", lambda _: {"frozen": True})
        monkeypatch.setattr(model_lifecycle, "score_cart_artifact", lambda groups, artifact: expected)
        monkeypatch.setattr(
            model_lifecycle, "train_and_persist_model",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected retraining")),
        )
        assert model_lifecycle.cart_for_current_run(db, invoice_groups()) == expected


def test_artifact_failure_flags_review_without_automatic_retraining(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        record = active_record()
        db.add(record)
        db.commit()
        monkeypatch.setattr(model_lifecycle, "_load_artifact", lambda _: (_ for _ in ()).throw(ValueError("bad artifact")))
        monkeypatch.setattr(
            model_lifecycle, "train_and_persist_model",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected retraining")),
        )
        result = model_lifecycle.cart_for_current_run(db, invoice_groups())
        assert result.status == "model_unavailable"
        assert record.review_recommended


def test_incomplete_monitoring_window_is_persisted_without_retraining(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        record = active_record()
        record.trained_through_date = pd.Timestamp("2030-01-01").date()
        record.selected_outcome_horizon = 12
        db.add(record)
        db.commit()
        monkeypatch.setattr(
            model_lifecycle, "train_and_persist_model",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected retraining")),
        )
        result = model_lifecycle.monitor_active_model(db, invoice_groups())
        db.flush()
        assert result["status"] == "insufficient_outcome_coverage"
        assert db.query(PredictiveMonitoringEvaluation).count() == 1
        assert not record.review_recommended


def test_no_active_model_returns_unavailable_without_training(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        monkeypatch.setattr(
            model_lifecycle, "train_and_persist_model",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected training")),
        )
        result = model_lifecycle.cart_for_current_run(db, invoice_groups())
        assert result.status == "model_unavailable"
        assert result.predictions == {}
