import asyncio
from datetime import date

import pytest
from fastapi import HTTPException

from app.auth.dependencies import AuthenticatedUser, require_admin, require_analytical_reader, require_user
from app.core.config import Settings, get_settings, validate_runtime_configuration


def test_production_missing_token_is_blocked(monkeypatch):
    monkeypatch.setenv("DEMO_MODE","false");get_settings.cache_clear()
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_user(None,None))
    assert error.value.status_code==401
    get_settings.cache_clear()


def test_management_cannot_use_administrator_dependency():
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_admin(AuthenticatedUser("u","management")))
    assert error.value.status_code==403


def test_production_configuration_fails_closed():
    unsafe = Settings(app_env="production", demo_mode=True)
    with pytest.raises(RuntimeError, match="Production configuration is incomplete"):
        validate_runtime_configuration(unsafe)

    safe = Settings(
        app_env="production",
        demo_mode=False,
        database_url="postgresql+psycopg://example.invalid/peslc",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="test-only-placeholder",
    )
    validate_runtime_configuration(safe)


def test_administrator_detail_routes_enforce_admin_dependency():
    from fastapi.routing import APIRoute
    from app.main import app

    protected_paths = {
        "/analytics/latest",
        "/analytics/runs",
        "/analytics/runs/{run_id}",
        "/analytics/run",
        "/imports/preview",
        "/imports/{batch_id}/commit",
        "/models/monitor",
        "/si-coverage",
        "/models/current",
    }
    dependencies = {
        route.path: {dependency.call for dependency in route.dependant.dependencies}
        for route in app.routes
        if isinstance(route, APIRoute) and route.path in protected_paths
    }
    assert set(dependencies) == protected_paths
    assert all(require_admin in calls for calls in dependencies.values())

    shared_paths = {"/analytics/rfm", "/analytics/settlement",
                    "/analytics/predictive", "/analytics/sensitivity"}
    shared = {
        route.path: {dependency.call for dependency in route.dependant.dependencies}
        for route in app.routes
        if isinstance(route, APIRoute) and route.path in shared_paths
    }
    assert set(shared) == shared_paths
    assert all(require_analytical_reader in calls and require_admin not in calls
               for calls in shared.values())


def test_management_can_fetch_read_only_native_validation_but_not_model_governance():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.models import AnalyticsRun, Base
    from app.db.session import get_db
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add(AnalyticsRun(status="successful", analysis_reference_date=date(2025, 12, 31)))
    db.commit()
    app.dependency_overrides[require_user] = lambda: AuthenticatedUser("test-user", "management")
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        response = client.get("/reports/native/validation")
        assert response.status_code == 200
        assert response.json()["study"]["status"] == "unavailable"
        assert client.get("/models/current").status_code == 403
    finally:
        app.dependency_overrides.pop(require_user, None)
        app.dependency_overrides.pop(get_db, None)
        db.close()
        engine.dispose()
