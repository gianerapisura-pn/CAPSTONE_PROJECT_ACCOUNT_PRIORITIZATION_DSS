from datetime import date, datetime, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.analytics.predictive.future_transaction import FEATURE_COLUMNS, TARGET_COLUMN, FUTURE_TRANSACTION, NO_FUTURE_TRANSACTION
from app.db.models import (
    AccountContextSnapshot, AnalyticsRun, Base, DimAccount, PredictiveModelVersion,
    PredictiveMonitoringEvaluation, PredictiveStudyPrediction, SICoverageConfirmation,
)
from app.etl.invoices import InvoiceGroup
from app.services import model_review as review


@pytest.fixture
def published(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        model = PredictiveModelVersion(model_version="catboost_stage8", model_family="CatBoost Classifier",
                                       status="active", artifact_hash="a" * 64)
        run = AnalyticsRun(status="successful", analysis_reference_date=date(2028, 12, 31),
                           completed_at=datetime.now(timezone.utc))
        db.add_all([model, run])
        db.flush()
        accounts = []
        groups = []
        for index in range(40):
            account = DimAccount(standardized_account_name=f"Business {index}", display_name=f"Business {index}",
                                 b2b_priority_eligible=False)  # Mutable context must not override the publication.
            db.add(account)
            db.flush()
            accounts.append(account)
            db.add(AccountContextSnapshot(analysis_run_id=run.analysis_run_id, account_key=account.account_key,
                standardized_account_name=account.standardized_account_name,
                b2b_priority_eligible=True, current_actionable=False))
            for year in [2017, 2019, 2021, 2023, 2025, 2027, 2028]:
                if year in (2027, 2028) and index >= 20:
                    continue
                groups.append(InvoiceGroup(
                    invoice_group_id=f"{index}-{year}", standardized_account_name=account.standardized_account_name,
                    si_no=f"SI-{index}-{year}", si_date=pd.Timestamp(date(year, 6, 1)),
                    si_amount=Decimal("100"), payment_status="Fully Paid",
                ))
        db.add(PredictiveStudyPrediction(model_version=model.model_version, account_key=accounts[0].account_key,
            forecast_origin=date(2025, 12, 31), future_window_start=date(2026, 1, 1),
            future_window_end=date(2026, 12, 31), predicted_class=FUTURE_TRANSACTION,
            source_package_hash="b" * 64, source_package_member="synthetic"))
        db.add(SICoverageConfirmation(complete_through=date(2028, 12, 31), evidence_type="test",
            evidence_reference="isolated synthetic", evidence_basis="test only", source_package_hash="b" * 64,
            recorded_by="00000000-0000-4000-8000-000000000001"))
        db.commit()
        monkeypatch.setattr(review, "load_invoice_groups", lambda _: groups)
        yield db, model, run, groups


def test_review_requires_calendar_coverage_and_published_reference(published):
    db, _, run, _ = published
    waiting, folds = review.prepare_review(db, date(2026, 11, 19))
    assert waiting["status"] == "waiting_for_data" and not folds
    assert waiting["next_outcome_end"] == "2027-12-31"
    ready, folds = review.prepare_review(db, date(2029, 1, 1))
    assert ready["status"] == "ready_for_comparison" and len(folds) == 2
    run.analysis_reference_date = date(2026, 12, 31)
    db.commit()
    assert review.prepare_review(db, date(2029, 1, 1))[0]["eligible_windows"] == 0


def test_folds_reserve_original_confirmations_and_purge_unfinished_training(published):
    db, _, _, _ = published
    _, folds = review.prepare_review(db, date(2029, 1, 1))
    for fold in folds:
        training_cutoffs = set(fold["train"]["cutoff_date"])
        assert not {pd.Timestamp(f"{year}-12-31") for year in (2023, 2024, 2025)} & training_cutoffs
        assert (fold["train"]["cutoff_date"] + pd.DateOffset(months=12)).max() <= fold["cutoff"]
        assert set(fold["test"]["cutoff_date"]) == {fold["cutoff"]}
        assert fold["cutoff"].year > 2025
        assert fold["test"][TARGET_COLUMN].nunique() == 2


def test_single_class_sparse_and_unverified_population_never_ready(published):
    db, _, _, groups = published
    groups[:] = [group for group in groups if int(group.standardized_account_name.split()[-1]) < 20]
    summary, folds = review.prepare_review(db, date(2029, 1, 1))
    assert summary["status"] == "waiting_for_data" and folds == []
    for row in db.query(AccountContextSnapshot):
        row.b2b_priority_eligible = False
    db.commit()
    assert review.prepare_review(db, date(2029, 1, 1))[1] == []


def test_missing_coverage_fails_closed(published):
    db, _, _, _ = published
    db.query(SICoverageConfirmation).delete()
    db.commit()
    assert review.prepare_review(db)[0]["evidence_fingerprint"] is None
    with pytest.raises(ValueError, match="verified SI coverage"):
        review.compare_models(db)


def test_fingerprint_detects_changed_features_and_artifact(published):
    db, model, _, groups = published
    first = review.prepare_review(db, date(2029, 1, 1))[0]["evidence_fingerprint"]
    groups[-1].si_amount = Decimal("123")
    second = review.prepare_review(db, date(2029, 1, 1))[0]["evidence_fingerprint"]
    assert second != first
    model.artifact_hash = "c" * 64
    assert review.prepare_review(db, date(2029, 1, 1))[0]["evidence_fingerprint"] != second


def test_comparison_uses_real_candidates_without_changing_active_model(published, monkeypatch):
    db, model, run, _ = published
    prepare = review.prepare_review
    monkeypatch.setattr(review, "prepare_review", lambda session: prepare(session, date(2029, 1, 1)))
    class Active:
        def predict(self, frame):
            return np.ones(len(frame), dtype=int)
    monkeypatch.setattr(review, "_load_artifact", lambda _: Active())
    before = (model.status, model.artifact_hash, run.critic_weights, db.query(PredictiveMonitoringEvaluation).count())
    report = review.compare_models(db)
    assert len(report["results"]) == 3
    assert all(len(result["folds"]) == 2 for result in report["results"])
    assert report["activation_performed"] is False
    assert "Business" not in __import__("json").dumps(report)
    assert before == (model.status, model.artifact_hash, run.critic_weights, db.query(PredictiveMonitoringEvaluation).count())
    db.add(PredictiveMonitoringEvaluation(predictive_model_version_id=model.predictive_model_version_id,
        status="evaluated", payload=report))
    db.commit()
    assert review.review_status(db)["status"] == "comparison_completed"
    model.artifact_hash = "d" * 64
    assert review.review_status(db)["comparison"] is None


def test_review_endpoint_requires_admin():
    from app.main import app
    from app.auth.dependencies import require_admin
    route = next(route for route in app.routes if getattr(route, "path", None) == "/models/review")
    assert require_admin in {dependency.call for dependency in route.dependant.dependencies}


def test_rejected_readiness_never_loads_or_trains(published, monkeypatch):
    db, _, run, _ = published
    run.analysis_reference_date = date(2025, 12, 31)
    db.commit()
    monkeypatch.setattr(review, "_load_artifact", lambda _: pytest.fail("must not load artifact"))
    monkeypatch.setattr(review, "_estimators", lambda: pytest.fail("must not initialize candidates"))
    monkeypatch.setattr(review, "load_invoice_groups", lambda _: pytest.fail("no feature reconstruction before outcome maturity"))
    with pytest.raises(ValueError, match="No fresh annual review window"):
        review.compare_models(db)


def test_post_cutoff_collection_cannot_change_predictive_features(published):
    db, _, _, groups = published
    groups[0].reconciled = True
    groups[0].final_cr_date = pd.Timestamp("2035-01-01")
    before = review.prepare_review(db, date(2029, 1, 1))[0]["evidence_fingerprint"]
    groups[0].final_cr_date = pd.Timestamp("2036-01-01")
    assert review.prepare_review(db, date(2029, 1, 1))[0]["evidence_fingerprint"] == before


@pytest.mark.parametrize("f1,precision,recall,expected", [
    ([0.83, 0.84], 0.80, 0.80, True),
    ([0.81, 0.81], 0.80, 0.80, False),  # Too little improvement.
    ([0.79, 0.90], 0.80, 0.80, False),  # Average hides a worse year.
    ([0.85, 0.85], 0.80, 0.70, False),  # Improved F1 hides lower Future recall.
    ([0.85, 0.85], 0.70, 0.80, False),  # Improved F1 hides lower Future precision.
])
def test_candidate_recommendation_preserves_class_performance(f1, precision, recall, expected):
    def result(name, scores, p, r):
        return {"model": name, "mean_macro_f1": sum(scores) / len(scores),
            "folds": [{"metrics": {"macro_f1": value,
                "per_class": {FUTURE_TRANSACTION: {"precision": p, "recall": r}}}} for value in scores]}
    baseline = result("Current", [0.80, 0.80], 0.80, 0.80)
    candidate = result("Candidate", f1, precision, recall)
    assert (review.select_candidate([baseline, candidate]) is not None) == expected
