"""PESLC isolated role authorization regression, no production connection.

Copy to backend/tests/ in the development branch and run pytest locally.
Uses an in-memory SQLite database plus a mocked authenticated *management*
profile; never supplies a service-role key and never calls production APIs.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.models import AnalyticsRun, AuditLog, Base, ImportBatch
from app.db.session import get_db
from app.main import app


@dataclass(frozen=True)
class Attempt:
    method: str
    path: str
    body: dict | None = None
    upload: bool = False


# Each route exists in the development branch's app/main.py as of SHA 64490dd.
# Both identifiers and payloads below are purely synthetic, deliberately invalid
# business targets. Real authorization must be evaluated before any mutation.
DENIED_MUTATIONS = [
    Attempt('POST', '/account-aliases/review/synthetic-review', {'status': 'rejected', 'reason': 'isolated authorization test'}),
    Attempt('POST', '/collection-corrections/synthetic-review/resolve', {'selected_raw_source_row_id': 'synthetic-row', 'reason': 'isolated authorization test'}),
    Attempt('PATCH', '/account-context/synthetic-account', {'entity_type': 'Company', 'business_category': 'Synthetic', 'primary_business_type': 'Synthetic', 'b2b_priority_eligible': False}),
    Attempt('POST', '/imports/preview', upload=True),
    Attempt('POST', '/imports/synthetic-batch/commit', {'analysis_reference_date': '2030-12-31'}),
    Attempt('POST', '/si-coverage', {'complete_through': '2030-12-31', 'evidence_type': 'Synthetic', 'evidence_reference': 'No external evidence', 'evidence_basis': 'Isolated auth test', 'confirmed_on': '2030-12-31'}),
    Attempt('POST', '/analytics/run', {'analysis_reference_date': '2030-12-31'}),
    Attempt('POST', '/reports/power-bi-refresh/retry'),
    Attempt('POST', '/models/monitor', {'as_of_date': '2030-12-31'}),
]


@pytest.mark.parametrize('attempt', DENIED_MUTATIONS, ids=lambda a: f'{a.method}_{a.path}')
def test_management_is_denied_every_admin_write_route(attempt):
    # Engine is in-memory, with no production DB URL, network access, or user credentials.
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            app.dependency_overrides[require_user] = lambda: AuthenticatedUser(
                user_id='00000000-0000-4000-8000-000000000002', role='management',
                email='management@local.invalid', demo=False)
            app.dependency_overrides[get_db] = lambda: db
            before = tuple(db.scalar(select(func.count()).select_from(t)) for t in (AnalyticsRun, ImportBatch, AuditLog))
            client = TestClient(app)  # Avoid FastAPI lifespan; it initializes the configured production DB.
            if attempt.upload:
                response = client.request(attempt.method, attempt.path, files={
                    'file': ('synthetic.csv', b'ACCOUNT NAMES,SI NO.\nSYNTHETIC,SI-TEST\n', 'text/csv')
                })
            else:
                response = client.request(attempt.method, attempt.path, json=attempt.body)
            assert response.status_code == 403, (
                f'{attempt.method} {attempt.path}: expected 403, got {response.status_code}; '
                'investigate locally before any production test'
            )
            after = tuple(db.scalar(select(func.count()).select_from(t)) for t in (AnalyticsRun, ImportBatch, AuditLog))
            assert after == before, 'An isolated unauthorized request mutated a local persisted table'
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
