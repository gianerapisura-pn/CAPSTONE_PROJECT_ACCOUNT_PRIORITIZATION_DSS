from datetime import date, datetime, timedelta, timezone

import httpx
from fastapi import BackgroundTasks
from fastapi.routing import APIRoute
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.dependencies import AuthenticatedUser, require_admin
from app.core.config import Settings
from app.db.models import AnalyticsRun, Base, PowerBIRefresh
from app.main import app, commit_import, run_analytics
from app.services import power_bi_refresh as refresh

RUN_ID = "00000000-0000-4000-8000-000000000101"
REQUEST_ID = "00000000-0000-4000-8000-000000000102"


def settings(enabled=True, demo=False):
    return Settings(
        demo_mode=demo,
        power_bi_auto_refresh_enabled=enabled,
        power_bi_tenant_id="00000000-0000-4000-8000-000000000201",
        power_bi_client_id="00000000-0000-4000-8000-000000000202",
        power_bi_client_secret="test-only-secret",
        power_bi_workspace_id="00000000-0000-4000-8000-000000000203",
        power_bi_dataset_id="00000000-0000-4000-8000-000000000204",
    )


def response(method, url, status, *, json=None, headers=None):
    return httpx.Response(
        status, json=json, headers=headers, request=httpx.Request(method, url)
    )


def database(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(refresh, "SessionLocal", factory)
    with factory() as db:
        db.add(AnalyticsRun(
            analysis_run_id=RUN_ID, status="successful",
            analysis_reference_date=date(2030, 6, 1),
        ))
        db.commit()
    return factory


def test_unconfigured_and_demo_never_contact_microsoft(monkeypatch):
    factory = database(monkeypatch)
    monkeypatch.setattr(refresh, "get_settings", lambda: settings(demo=True))
    assert not refresh.configured()
    with factory() as db:
        refresh.enqueue_refresh(db, RUN_ID)
        db.commit()
    monkeypatch.setattr(refresh.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("No Microsoft request is allowed in demo mode.")
    ))
    refresh.request_refresh(RUN_ID)
    with factory() as db:
        assert db.get(PowerBIRefresh, RUN_ID).status == "not_configured"
        assert refresh.public_status(db.get(PowerBIRefresh, RUN_ID), RUN_ID)["configured"] is False


def test_accepted_refresh_is_once_per_run_and_completion_is_verified(monkeypatch):
    factory = database(monkeypatch)
    config = settings()
    monkeypatch.setattr(refresh, "get_settings", lambda: config)
    with factory() as db:
        refresh.enqueue_refresh(db, RUN_ID)
        db.commit()
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        if "login.microsoftonline.com" in url:
            assert kwargs["data"]["scope"].endswith("/.default")
            return response("POST", url, 200, json={"access_token": "token"})
        assert kwargs["headers"]["Authorization"] == "Bearer token"
        assert "test-only-secret" not in str(kwargs["headers"])
        return response("POST", url, 202, headers={"x-ms-request-id": REQUEST_ID})

    monkeypatch.setattr(refresh.httpx, "post", post)
    refresh.request_refresh(RUN_ID)
    refresh.request_refresh(RUN_ID)
    assert len([url for url in calls if "api.powerbi.com" in url]) == 1
    with factory() as db:
        row = db.get(PowerBIRefresh, RUN_ID)
        assert row.status == "requested"
        assert row.attempt_count == 1
        assert row.refresh_request_id == REQUEST_ID

    monkeypatch.setattr(refresh.httpx, "get", lambda url, **kw: response(
        "GET", url, 202, json={"status": "Unknown"}
    ))
    refresh.reconcile_active_refreshes()
    with factory() as db:
        assert db.get(PowerBIRefresh, RUN_ID).status == "refreshing"
    monkeypatch.setattr(refresh.httpx, "get", lambda url, **kw: response(
        "GET", url, 200, json={"status": "Completed"}
    ))
    refresh.reconcile_active_refreshes()
    with factory() as db:
        row = db.get(PowerBIRefresh, RUN_ID)
        assert row.status == "completed"
        assert row.completed_at is not None
        assert db.get(AnalyticsRun, RUN_ID).status == "successful"


def test_refresh_failure_does_not_change_publication_and_admin_can_retry(monkeypatch):
    factory = database(monkeypatch)
    monkeypatch.setattr(refresh, "get_settings", settings)
    with factory() as db:
        refresh.enqueue_refresh(db, RUN_ID)
        db.commit()

    def failed_post(url, **kwargs):
        return response("POST", url, 401)

    monkeypatch.setattr(refresh.httpx, "post", failed_post)
    refresh.request_refresh(RUN_ID)
    with factory() as db:
        row = db.get(PowerBIRefresh, RUN_ID)
        assert row.status == "failed"
        assert row.error_code == "power_bi_http_401"
        assert db.get(AnalyticsRun, RUN_ID).status == "successful"
        assert refresh.retry_refresh(db, RUN_ID)
        assert not refresh.retry_refresh(db, RUN_ID)
        assert db.get(PowerBIRefresh, RUN_ID).status == "pending"


def test_restart_recovers_pending_but_not_ambiguous_in_flight_request(monkeypatch):
    factory = database(monkeypatch)
    monkeypatch.setattr(refresh, "get_settings", settings)
    with factory() as db:
        refresh.enqueue_refresh(db, RUN_ID)
        db.commit()
    dispatched = []
    monkeypatch.setattr(refresh, "request_refresh", dispatched.append)
    refresh.recover_pending_refreshes()
    assert dispatched == [RUN_ID]

    with factory() as db:
        row = db.get(PowerBIRefresh, RUN_ID)
        row.status = "requesting"
        row.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()
    dispatched.clear()
    refresh.recover_pending_refreshes()
    with factory() as db:
        row = db.get(PowerBIRefresh, RUN_ID)
        assert row.status == "failed"
        assert row.error_code == "request_outcome_unknown_verify_before_retry"
    assert dispatched == []


def test_import_commit_schedules_after_success_and_retry_requires_admin(monkeypatch):
    from app.main import CommitRequest

    monkeypatch.setattr("app.main.commit_source", lambda *args: {
        "status": "COMMITTED", "analysis_run_id": RUN_ID,
    })
    tasks = BackgroundTasks()
    result = commit_import(
        "batch-id", CommitRequest(analysis_reference_date=date(2030, 6, 1)),
        tasks, AuthenticatedUser("admin", "administrator"), None,
    )
    assert result["status"] == "COMMITTED"
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func is refresh.request_refresh
    assert tasks.tasks[0].args == (RUN_ID,)
    route = next(route for route in app.routes if isinstance(route, APIRoute)
                 and route.path == "/reports/power-bi-refresh/retry")
    assert require_admin in {item.call for item in route.dependant.dependencies}


def test_explicit_successful_analytics_run_queues_refresh(monkeypatch):
    from app.main import RunRequest
    from app import main

    factory = database(monkeypatch)
    monkeypatch.setattr(refresh, "get_settings", lambda: settings(demo=True))
    monkeypatch.setattr(main, "load_invoice_groups", lambda db: [object()])
    monkeypatch.setattr(main, "validate_analysis_reference", lambda *args: None)
    monkeypatch.setattr(main, "b2b_analytical_accounts", lambda db: set())
    monkeypatch.setattr(main, "current_actionable_accounts", lambda db: set())
    monkeypatch.setattr(main, "future_transaction_for_current_run", lambda *args: None)
    monkeypatch.setattr(main, "run_account_prioritization", lambda *args, **kwargs: object())
    monkeypatch.setattr(main, "asdict", lambda result: {"status": "successful"})
    monkeypatch.setattr(main, "persist_run_output", lambda db, run, result: setattr(
        run, "status", "successful"
    ))
    monkeypatch.setattr(main, "audit", lambda *args: None)
    tasks = BackgroundTasks()

    with factory() as db:
        result = run_analytics(
            RunRequest(analysis_reference_date=date(2030, 6, 1)),
            tasks, AuthenticatedUser("admin", "administrator"), db,
        )
        assert result["status"] == "successful"
        assert db.get(PowerBIRefresh, result["analysis_run_id"]).status == "not_configured"
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].args == (result["analysis_run_id"],)
