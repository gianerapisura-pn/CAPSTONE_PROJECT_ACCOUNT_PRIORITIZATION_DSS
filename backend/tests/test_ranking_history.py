import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.models import Base, PrescriptiveValidationEvidence
from app.db.session import get_db
from app.main import app
from app.core.config import get_settings
from app.services.additional_validation_evidence import seed_additional_validation_evidence
from app.services.ranking_history import EVIDENCE_VERSION, seed_ranking_history


@pytest.fixture
def history_db():
    package = os.environ.get("PESLC_FINAL_QA_PACKAGE_PATH")
    if not package or not Path(package).is_file():
        pytest.skip("Private verified study package required.")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_additional_validation_evidence(db, package)
        db.commit()
        before = [(r.prescriptive_validation_evidence_id, r.payload) for r in db.scalars(select(PrescriptiveValidationEvidence))]
        assert seed_ranking_history(db, package) == 539
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        yield db, package, before
        app.dependency_overrides.clear()
    engine.dispose()


def client(role="management"):
    app.dependency_overrides[require_user] = lambda: AuthenticatedUser("test", role)
    return TestClient(app)


def test_idempotent_registration_preserves_existing_evidence(history_db):
    db, package, before = history_db
    ids = [r.prescriptive_validation_evidence_id for r in db.scalars(select(PrescriptiveValidationEvidence).where(PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION))]
    assert seed_ranking_history(db, package) == 539
    db.flush()
    assert ids == [r.prescriptive_validation_evidence_id for r in db.scalars(select(PrescriptiveValidationEvidence).where(PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION))]
    for identity, payload in before:
        assert db.get(PrescriptiveValidationEvidence, identity).payload == payload


def test_roles_defaults_pagination_and_no_write(history_db, monkeypatch):
    admin = client("administrator").get("/reports/native/ranking-history").json()
    assert admin == client().get("/reports/native/ranking-history").json()
    assert admin["year"] == 2025 and admin["total"] == 83 and len(admin["items"]) == 10
    assert all(r["outcome_status"] == "pending" and r["subsequent_si_value"] is None for r in admin["items"])
    second = client().get("/reports/native/ranking-history?page=2").json()
    assert not {r["account_key"] for r in admin["items"]} & {r["account_key"] for r in second["items"]}
    assert client().post("/reports/native/ranking-history").status_code == 405
    assert client("viewer").get("/reports/native/ranking-history").status_code == 403
    app.dependency_overrides.pop(require_user)
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    assert TestClient(app).get("/reports/native/ranking-history").status_code == 401


@pytest.mark.parametrize("year,count", [(2018,49),(2019,57),(2020,62),(2021,66),(2022,68),(2023,76),(2024,78),(2025,83)])
def test_every_year_and_previous_year_comparisons(history_db, year, count):
    result = client().get(f"/reports/native/ranking-history?year={year}&page_size=100").json()
    assert result["population"] == result["total"] == count
    for row in result["items"]:
        assert row["year"] == year
        if year == 2018:
            assert row["previous"] is None
        if row["previous"]:
            assert row["previous"]["year"] == year-1
            assert row["previous"]["positions"] == row["previous"]["rank"]-row["rank"]
    if year < 2025:
        assert all(r["outcome_status"] == "observed" for r in result["items"])


@pytest.mark.parametrize("query", ["year=1900", "year=oops", "page=0", "page_size=101", "page_size=0"])
def test_invalid_parameters(history_db, query):
    assert client().get("/reports/native/ranking-history?"+query).status_code == 422


def test_search_preserves_rank_and_treats_search_as_literal(history_db):
    c = client()
    row = c.get("/reports/native/ranking-history?page=3").json()["items"][0]
    result = c.get("/reports/native/ranking-history", params={"search":row["account_name"]}).json()
    assert result["items"] == [row]
    for search in ["UNMATCHED_TEST_ACCOUNT", "' OR 1=1 --", "%_"]:
        empty = c.get("/reports/native/ranking-history",params={"search":search}).json()
        assert empty["total"] == 0 and empty["items"] == [] and empty["population"] == 83


def test_unavailable_mismatch_and_duplicate_evidence_fail_closed(history_db):
    db, package, _ = history_db
    records = list(db.scalars(select(PrescriptiveValidationEvidence).where(PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION)))
    first = records[0]
    first.source_package_hash = "0"*64
    db.commit()
    assert client().get("/reports/native/ranking-history").status_code == 503
    with pytest.raises(ValueError): seed_ranking_history(db, package)
    for r in records: db.delete(r)
    db.commit()
    assert client().get("/reports/native/ranking-history").status_code == 503
    assert seed_ranking_history(db, package) == 539
    db.commit()
    first = db.scalar(select(PrescriptiveValidationEvidence).where(PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION))
    db.add(PrescriptiveValidationEvidence(evidence_version=EVIDENCE_VERSION,evidence_scope=first.evidence_scope,comparator=first.comparator,payload=first.payload,source_package_hash=first.source_package_hash))
    db.commit()
    assert client().get("/reports/native/ranking-history").status_code == 503


def test_package_mismatch_rejected(history_db, tmp_path):
    db, _, _ = history_db
    invalid = tmp_path/"invalid.zip"
    invalid.write_bytes(b"not the approved package")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        seed_ranking_history(db, invalid)
