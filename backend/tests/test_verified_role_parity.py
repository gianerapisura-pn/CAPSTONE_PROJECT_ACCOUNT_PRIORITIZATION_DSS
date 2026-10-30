"""Read the isolated review database without modifying its published results."""
import os
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.session import get_db
from app.main import app


def test_both_roles_read_identical_verified_study_and_management_cannot_mutate():
    configured = os.getenv("PESLC_QA_REVIEW_DATABASE_PATH")
    if not configured or not Path(configured).is_file():
        pytest.skip("Configure the isolated review SQLite database for read-only role parity.")
    path = Path(configured).resolve().as_posix()
    engine = create_engine("sqlite://", creator=lambda: sqlite3.connect(
        f"file:{path}?mode=ro", uri=True, check_same_thread=False), poolclass=StaticPool)
    paths = ("/dashboard", "/accounts?eligibility=ranked&page_size=500", "/reports/native/overview",
             "/reports/native/insights", "/reports/native/validation", "/analytics/rfm",
             "/analytics/settlement", "/analytics/predictive", "/analytics/sensitivity")
    try:
        with Session(engine) as db:
            app.dependency_overrides[get_db] = lambda: db
            def read(role):
                app.dependency_overrides[require_user] = lambda: AuthenticatedUser("review-role", role)
                client = TestClient(app)
                responses = [client.get(path) for path in paths]
                assert all(response.status_code == 200 for response in responses)
                return [response.json() for response in responses]
            admin = read("administrator")
            management = read("management")
            assert admin == management
            assert management[1]["items"]
            assert management[4]["additional_evidence"]
            key = management[1]["items"][0]["account_key"]
            assert TestClient(app).get(f"/accounts/{key}?eligibility=ranked").status_code == 200
            assert TestClient(app).post("/analytics/run", json={"analysis_reference_date": "2030-12-31"}).status_code == 403
            assert TestClient(app).get("/imports").status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
