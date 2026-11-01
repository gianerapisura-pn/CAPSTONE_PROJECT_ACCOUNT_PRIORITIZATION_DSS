from copy import deepcopy
from datetime import date, datetime, timezone
from importlib import import_module
from io import BytesIO
from uuid import UUID

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.models import AnalyticsRun, Base, DimAccount
from app.db.session import get_db


@pytest.fixture
def drilldown(monkeypatch):
    main = import_module("app.main")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        run = AnalyticsRun(status="successful", analysis_reference_date=date(2030, 12, 31), completed_at=datetime(2031, 1, 1, tzinfo=timezone.utc))
        db.add(run)
        db.flush()
        rows = []
        for i in range(6):
            name, key = f"ACCOUNT {i}", str(UUID(int=i + 1))
            db.add(DimAccount(account_key=key, standardized_account_name=name, display_name=name))
            rows.append({"account_key": key, "account": name, "display_name": name,
                         "b2b_priority_eligible": True, "current_actionable": i != 4,
                         "criteria_complete": True, "analysis_run_id": run.analysis_run_id,
                         "analysis_reference_date": "2030-12-31", "recency_days": i + 1,
                         "frequency": 2, "monetary": 1000, "r_score": 3, "f_score": 3,
                         "m_score": 3, "rfm_code": "333", "rfm_mean_score": 3,
                         "settlement_invoice_count": 1, "valid_settlement_record_count": 1,
                         "mcs_eligible": i != 4, "is_ranked": i != 4,
                         "ranking_status": "ranked" if i != 4 else "not_ranked",
                         "priority_rank": i + 1 if i != 4 else None,
                         "priority_group": "High" if i != 4 else None,
                         "final_priority_score": .9 - i / 10 if i != 4 else None,
                         "predicted_future_transaction_class": "With No Future Sales" if i < 2 else "With Future Sales"})
        db.commit()
        study = {"status": "Validated", "forecast_origin": "2025-12-31",
                 "model_version": "frozen-study-model", "predictions": {
                     row["account"]: "With Future Sales" if i < 2 else "With No Future Sales"
                     for i, row in enumerate(rows[:5])}}
        monkeypatch.setattr(main, "current_account_rows", lambda *_: deepcopy(rows))
        monkeypatch.setattr(main, "final_study_prediction_payload", lambda *_: deepcopy(study))
        monkeypatch.setattr(main, "run_payload", lambda *_: {"accounts": deepcopy(rows), "rfm": [], "settlement": [], "sensitivity": [], "predictive": {}})
        main.app.dependency_overrides[get_db] = lambda: db
        main.app.dependency_overrides[require_user] = lambda: AuthenticatedUser("test-admin", "administrator")
        try:
            yield TestClient(main.app), rows, study
        finally:
            main.app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.parametrize("label,count", [("With Future Sales", 2), ("With No Future Sales", 3)])
def test_study_classes_match_source_across_pages_exports_and_details(drilldown, label, count):
    client, originals, study = drilldown
    before = deepcopy(originals)
    params = {"prediction_scope": "study", "predicted_future_transaction_class": label, "eligibility": "all"}
    expected = [row for row in originals if study["predictions"].get(row["account"]) == label]
    seen = []
    for page in range(1, (count + 1) // 2 + 1):
        response = client.get("/accounts", params={**params, "page": page, "page_size": 2})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == count
        assert body["prediction_scope"] == "study"
        assert body["prediction_reference_date"] == "2025-12-31"
        seen.extend(body["items"])
    assert [row["account"] for row in seen] == [row["account"] for row in expected]
    for row, original in zip(seen, expected, strict=True):
        for field in ["priority_rank", "priority_group", "final_priority_score", "is_ranked"]:
            assert row[field] == original[field]
        assert row["predicted_future_transaction_class"] == label
    for format in ["csv", "xlsx"]:
        response = client.get(f"/exports/priorities.{format}", params=params)
        assert response.status_code == 200, response.text
        frame = pd.read_csv(BytesIO(response.content)) if format == "csv" else pd.read_excel(BytesIO(response.content))
        assert frame.account.tolist() == [row["account"] for row in expected]
        assert set(frame.predicted_future_transaction_class) == {label}
        assert set(frame.prediction_scope) == {"study"}
    detail = client.get("/accounts/" + expected[0]["account_key"], params=params)
    assert detail.status_code == 200, detail.text
    assert detail.json()["navigation"]["total"] == count
    assert originals == before
    ordinary = client.get("/accounts", params={"eligibility": "all", "predicted_future_transaction_class": label})
    assert ordinary.status_code == 200
    ordinary_expected = sorted(
        [row for row in originals if row["predicted_future_transaction_class"] == label],
        key=lambda row: (row["priority_rank"] is None, row["priority_rank"] or 0, row["account"]))
    assert [row["account"] for row in ordinary.json()["items"]] == [row["account"] for row in ordinary_expected]


def test_study_scope_fails_closed_when_evidence_or_snapshot_is_incomplete(drilldown):
    client, rows, study = drilldown
    assert client.get("/accounts", params={"prediction_scope": "invalid"}).status_code == 422
    study["status"] = "unavailable"
    assert client.get("/accounts", params={"prediction_scope": "study"}).status_code == 409
    study["status"] = "Validated"
    study["predictions"]["MISSING FROM CURRENT SNAPSHOT"] = "With Future Sales"
    assert client.get("/accounts", params={"prediction_scope": "study"}).status_code == 409
