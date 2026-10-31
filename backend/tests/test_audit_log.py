from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.models import AuditLog, Base
from app.db.session import get_db
from app.main import app


def test_audit_log_is_admin_only_paginated_and_excludes_sensitive_details():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([AuditLog(action='import_preview', entity_type='import_batch', details={'private': 'must-not-appear'}) for _ in range(12)])
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        try:
            app.dependency_overrides[require_user] = lambda: AuthenticatedUser('operator', 'management')
            client = TestClient(app)
            assert client.get('/audit-log').status_code == 403
            app.dependency_overrides[require_user] = lambda: AuthenticatedUser('operator', 'administrator')
            first = client.get('/audit-log').json()
            assert first['total'] == 12 and len(first['items']) == 10
            assert first['total_pages'] == 2
            assert len(client.get('/audit-log?page=2').json()['items']) == 2
            assert client.get('/audit-log?page=999').json()['page'] == 2
            assert client.get('/audit-log?page=0').status_code == 422
            assert 'must-not-appear' not in str(first)
        finally:
            app.dependency_overrides.clear()
    engine.dispose()
