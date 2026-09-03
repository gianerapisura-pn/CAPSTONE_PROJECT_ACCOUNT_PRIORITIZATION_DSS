import asyncio

import pytest
from fastapi import HTTPException

from app.auth.dependencies import AuthenticatedUser, require_admin, require_user
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
        "/analytics/rfm",
        "/analytics/settlement",
        "/analytics/cart",
        "/analytics/sensitivity",
        "/analytics/runs",
        "/analytics/runs/{run_id}",
        "/models/current",
    }
    dependencies = {
        route.path: {dependency.call for dependency in route.dependant.dependencies}
        for route in app.routes
        if isinstance(route, APIRoute) and route.path in protected_paths
    }
    assert set(dependencies) == protected_paths
    assert all(require_admin in calls for calls in dependencies.values())
