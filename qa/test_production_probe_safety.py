"""Prove exact production probe payloads cannot mutate even with Admin access."""
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.models import Base
from app.db.session import get_db
from app.main import app


def test_exact_production_probe_bodies_never_reach_valid_mutation_handlers():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            app.dependency_overrides[get_db] = lambda: db
            app.dependency_overrides[require_user] = lambda: AuthenticatedUser(
                "00000000-0000-4000-8000-000000000001", "administrator")
            client = TestClient(app)
            def state():
                return {table.name: db.connection().exec_driver_sql(
                    f'SELECT count(*) FROM "{table.name}"').scalar_one()
                    for table in Base.metadata.sorted_tables}
            before = state()
            for method, path, expected in json.loads(
                Path(__file__).with_name("production_denial_probes.json").read_text()
            ):
                response = client.request(method, path, json={})
                assert response.status_code == expected, (method, path, response.status_code)
                assert state() == before, (method, path)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
