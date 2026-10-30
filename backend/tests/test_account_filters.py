from datetime import date
from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.models import AnalyticsRun, Base
from app.db.session import get_db
from app.main import app
from app.db.repository import filter_current_account_rows


@pytest.fixture
def account_client(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        run = AnalyticsRun(status="successful", analysis_reference_date=date(2030, 12, 31))
        db.add(run); db.commit()
        rows = [dict(account="Alpha", account_key="a", priority_rank=12, is_ranked=True,
                     priority_group="High", final_priority_score=.75, business_category="Construction",
                     primary_business_type="Engineering", account_status="Client-Confirmed Active",
                     predicted_future_transaction_class="With Future Sales", r_score=5, f_score=4,
                     m_score=3, average_settlement_days=29),
                dict(account="Beta", account_key="b", priority_rank=25, is_ranked=True,
                     priority_group="Medium", final_priority_score=.5, business_category="Property",
                     primary_business_type="Developer", account_status="Client-Confirmed Active",
                     predicted_future_transaction_class="With No Future Sales", r_score=3, f_score=5,
                     m_score=4, average_settlement_days=30),
                dict(account="=1+1", account_key="c", priority_rank=None, is_ranked=False,
                     priority_group=None, final_priority_score=None, business_category="Construction",
                     primary_business_type="Engineering", account_status="Client-Confirmed Closed",
                     predicted_future_transaction_class=None, r_score=1, f_score=2, m_score=1,
                     average_settlement_days=None)]
        for row in rows:
            row.update(display_name=row["account"], b2b_priority_eligible=True,
                       current_actionable=row["is_ranked"], criteria_complete=row["is_ranked"],
                       analysis_run_id=run.analysis_run_id, recency_days=10,
                       frequency=2, monetary=1000, rfm_code="543", rfm_mean_score=4,
                       settlement_invoice_count=1, valid_settlement_record_count=1,
                       mcs_eligible=row["is_ranked"], ranking_status="ranked" if row["is_ranked"] else "not_ranked")
        monkeypatch.setattr("app.main.current_account_rows", lambda *_: rows)
        monkeypatch.setattr("app.main.run_payload", lambda *_: dict(accounts=rows, rfm=[], settlement=[], sensitivity=[], predictive={}))
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_user] = lambda: AuthenticatedUser("test", "management")
        yield TestClient(app), rows
        app.dependency_overrides.clear()
    engine.dispose()


def test_filters_sort_and_exports_use_the_same_full_population(account_client):
    client, rows = account_client
    query = dict(business_category="Construction", primary_business_type="Engineering",
                 priority_group="High", account_status="Client-Confirmed Active", eligibility="ranked",
                 rfm_component="Recency", rfm_score=5, settlement_range="Below 30",
                 predicted_future_transaction_class="With Future Sales")
    response = client.get("/accounts", params={**query, "page_size": 1})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["priority_rank"] == 12
    assert response.json()["filter_options"]["business_category"] == ["Construction", "Property"]
    for format in ("csv", "xlsx"):
        export = client.get("/exports/priorities", params={**query, "format": format})
        assert export.status_code == 200
        frame = pd.read_csv(BytesIO(export.content)) if format == "csv" else pd.read_excel(BytesIO(export.content))
        assert frame.account.tolist() == ["Alpha"]
        assert frame.priority_rank.tolist() == [12]
    assert rows[0]["final_priority_score"] == .75
    assert client.get("/accounts", params={"eligibility": "ranked", "sort_by": "score", "sort_direction": "desc"}).json()["items"][0]["account"] == "Alpha"
    assert client.get("/accounts", params={"page": 2, "page_size": 1}).json()["items"][0]["account"] == "Beta"
    assert client.get("/accounts", params={"eligibility": "not_ranked"}).json()["items"][0]["final_priority_score"] is None


@pytest.mark.parametrize("params", [{"business_category": "Invented"}, {"primary_business_type": "Invented"},
    {"account_status": "Invented"}, {"priority_group": "Invented"}, {"rfm_score": "6"},
    {"settlement_range": "Invented"}, {"unknown_filter": "ignored"}, {"sort_by": "Invented"}])
def test_unknown_or_invalid_filters_are_rejected_for_list_and_export(account_client, params):
    client, _ = account_client
    assert client.get("/accounts", params=params).status_code == 422
    assert client.get("/exports/priorities", params=params).status_code == 422


def test_export_formula_strings_are_text_and_missing_settlement_is_not_zero(account_client):
    client, rows = account_client
    assert [row["account"] for row in filter_current_account_rows(rows, settlement_range="30-<60")] == ["Beta"]
    for format in ("csv", "xlsx"):
        result = client.get("/exports/priorities", params={"eligibility": "not_ranked", "format": format})
        frame = pd.read_csv(BytesIO(result.content)) if format == "csv" else pd.read_excel(BytesIO(result.content))
        assert frame.account.tolist() == ["'=1+1"]


def test_duplicate_filters_fail_closed_for_list_and_export(account_client):
    client, _ = account_client
    duplicate = [("priority_group", "High"), ("priority_group", "Low")]
    for endpoint in ("/accounts", "/exports/priorities"):
        assert client.get(endpoint, params=duplicate).status_code == 422


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 501}])
def test_invalid_pagination_is_rejected(account_client, params):
    client, _ = account_client
    assert client.get("/accounts", params=params).status_code == 422


def test_page_clamping_and_empty_exports_remain_consistent(account_client):
    client, _ = account_client
    last = client.get("/accounts", params={"page": 999, "page_size": 1}).json()
    assert last["page"] == 3 and last["total"] == 3
    empty = client.get("/accounts", params={"search": "no matching customer", "page": 999}).json()
    assert empty["page"] == 1 and empty["total"] == 0 and empty["items"] == []
    for format in ("csv", "xlsx"):
        response = client.get("/exports/priorities", params={"search": "no matching customer", "format": format})
        assert response.status_code == 200
        frame = pd.read_csv(BytesIO(response.content)) if format == "csv" else pd.read_excel(BytesIO(response.content))
        assert frame.empty
        assert {"analysis_run_id", "analysis_reference_date"}.issubset(frame.columns)


def test_settlement_boundaries_never_overlap_or_include_missing_values():
    days = [0, 29.999, 30, 59.999, 60, 89.999, 90, 119.999, 120, None]
    rows = [dict(account=str(index), priority_rank=index + 1, average_settlement_days=value)
            for index, value in enumerate(days)]
    ranges = ["Below 30", "30-<60", "60-<90", "90-<120", "120+"]
    memberships = [filter_current_account_rows(rows, settlement_range=band) for band in ranges]
    assert [len(members) for members in memberships] == [2, 2, 2, 2, 1]
    identities = [row["account"] for members in memberships for row in members]
    assert len(identities) == len(set(identities)) == 9
    assert all(row["average_settlement_days"] is not None for members in memberships for row in members)


def test_missing_scores_and_ranks_stay_last_in_both_sort_directions(account_client):
    _, rows = account_client
    for field in ("rank", "score"):
        for direction in ("asc", "desc"):
            result = filter_current_account_rows(rows, sort_by=field, sort_direction=direction)
            assert result[-1]["account_key"] == "c"
            assert {row["account_key"]: row["priority_rank"] for row in result} == {"a": 12, "b": 25, "c": None}
