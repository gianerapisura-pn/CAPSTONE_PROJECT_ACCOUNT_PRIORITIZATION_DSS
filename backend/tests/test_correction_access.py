"""HTTP boundary checks for the relocated, unchanged correction workflow."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.auth.dependencies import AuthenticatedUser, require_user
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import get_db
from app.main import app

@pytest.mark.parametrize("method,path", [
    ("get", "/collection-corrections?status=all"),
    ("post", "/collection-corrections/nonexistent/resolve"),
])
@pytest.mark.parametrize("role,expected", [("management",403),(None,401)])
def test_correction_http_permissions(monkeypatch, method, path, role, expected):
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    old=app.dependency_overrides.copy()
    monkeypatch.setenv("DEMO_MODE","false");get_settings.cache_clear()
    try:
        with Session(engine) as db:
            app.dependency_overrides[get_db]=lambda:db
            if role:
                app.dependency_overrides[require_user]=lambda:AuthenticatedUser("qa",role)
            else:
                app.dependency_overrides.pop(require_user,None)
            kwargs={"json":{"selected_raw_source_row_id":"row-1","reason":"Verified receipt."}} if method=="post" else {}
            response=getattr(TestClient(app),method)(path,**kwargs)
            assert response.status_code==expected
    finally:
        app.dependency_overrides.clear();app.dependency_overrides.update(old)
        get_settings.cache_clear();engine.dispose()
