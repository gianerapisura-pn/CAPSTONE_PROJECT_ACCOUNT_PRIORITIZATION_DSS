import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.models import AnalyticsRun, Base, PrescriptiveValidationEvidence, UserProfile
from app.db.session import get_db
from app.main import app
from app.services.additional_validation_evidence import (
    EVIDENCE_VERSION, seed_additional_validation_evidence,
)
from app.services.study_predictions import MODEL_ARTIFACT_SHA256, MODEL_VERSION


@pytest.fixture
def controlled_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(AnalyticsRun(status="successful", analysis_reference_date=date(2025, 12, 31)))
    db.add_all([
        UserProfile(user_id="00000000-0000-4000-8000-000000000011", role="administrator", is_active=True),
        UserProfile(user_id="00000000-0000-4000-8000-000000000012", role="management", is_active=True),
    ])
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.pop(require_user, None)
    app.dependency_overrides.pop(get_db, None)
    db.close()
    engine.dispose()


def _as(role):
    identity = "00000000-0000-4000-8000-000000000011" if role == "administrator" else "00000000-0000-4000-8000-000000000012"
    app.dependency_overrides[require_user] = lambda: AuthenticatedUser(identity, role, f"{role}@example.test", role)
    return TestClient(app)


def test_shared_read_only_results_are_role_identical(controlled_db):
    paths = ("/dashboard", "/accounts", "/reports/native/overview", "/reports/native/insights",
             "/reports/native/validation", "/analytics/rfm", "/analytics/settlement",
             "/analytics/predictive", "/analytics/sensitivity")
    admin = {path: _as("administrator").get(path).json() for path in paths}
    manager = {path: _as("management").get(path).json() for path in paths}
    assert admin == manager
    assert all("detail" not in result for result in admin.values())
    assert _as("management").post("/analytics/run", json={"analysis_reference_date": "2025-12-31"}).status_code == 403
    assert _as("management").get("/imports").status_code == 403


def test_own_profile_update_cannot_change_role_or_other_user(controlled_db):
    client = _as("management")
    assert client.patch("/profile", json={"display_name": "Manager", "role": "administrator"}).status_code == 422
    assert client.patch("/profile", json={"display_name": "Manager"}).status_code == 200
    assert client.get("/profile").json()["display_name"] == "Manager"
    assert controlled_db.get(UserProfile, "00000000-0000-4000-8000-000000000011").display_name is None


def test_verified_part52_seed_is_idempotent_and_visible_to_both_roles(controlled_db, monkeypatch):
    package = os.getenv("PESLC_FINAL_QA_PACKAGE_PATH")
    if not package or not Path(package).is_file():
        pytest.skip("Set PESLC_FINAL_QA_PACKAGE_PATH to the private final QA ZIP.")
    counts = seed_additional_validation_evidence(controlled_db, package)
    controlled_db.commit()
    assert counts == {"study_backtest_summary": 7, "annual_rank_stability": 7, "annual_rank_changes": 455,
                      "group_yearly_outcomes": 21, "group_pooled_outcomes": 3,
                      "fps_future_relationship": 7, "recency_only_benchmark": 7,
                      "feature_ablation_summary": 10, "feature_ablation_folds": 30,
                      "ranking_bootstrap": 2}
    ids = {row.prescriptive_validation_evidence_id for row in controlled_db.scalars(select(
        PrescriptiveValidationEvidence).where(PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION)).all()}
    assert seed_additional_validation_evidence(controlled_db, package) == counts
    controlled_db.flush()
    assert ids == {row.prescriptive_validation_evidence_id for row in controlled_db.scalars(select(
        PrescriptiveValidationEvidence).where(PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION)).all()}
    monkeypatch.setattr("app.main.active_model_version", lambda _db: SimpleNamespace(
        model_version=MODEL_VERSION, artifact_hash=MODEL_ARTIFACT_SHA256,
        predictive_model_version_id="00000000-0000-4000-8000-000000000013"))
    admin = _as("administrator").get("/reports/native/validation")
    manager = _as("management").get("/reports/native/validation")
    assert admin.status_code == manager.status_code == 200
    assert admin.json() == manager.json()
    assert len(admin.json()["additional_evidence"]["annual_rank_stability"]) == 7
    assert len(admin.json()["additional_evidence"]["group_pooled_outcomes"]) == 3
    assert sum(row["lift_over_expected_random"] for row in admin.json()["additional_evidence"]["study_backtest_summary"]) / 7 == pytest.approx(4.385871044679672)
