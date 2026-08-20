import asyncio

import pytest
from fastapi import HTTPException

from app.auth.dependencies import AuthenticatedUser, require_admin, require_user
from app.core.config import get_settings


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
