from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.models import AnalyticsRun, Base
from app.auth.dependencies import AuthenticatedUser
from app.core.config import get_settings
from app.db.repository import latest_successful_run, run_payload
from app.services.import_workflow import commit_source, preview_source
from fastapi import HTTPException
import pytest


def test_latest_successful_run_ignores_newer_failed_run():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        successful=AnalyticsRun(status="successful",completed_at=datetime(2030,1,1,tzinfo=timezone.utc))
        failed=AnalyticsRun(status="failed",completed_at=datetime(2031,1,1,tzinfo=timezone.utc))
        db.add_all([successful,failed]);db.commit()
        assert latest_successful_run(db).analysis_run_id==successful.analysis_run_id


def test_future_file_persists_through_latest_api_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_STORAGE_PATH", str(tmp_path / "source"))
    get_settings.cache_clear()
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    content=Path("../sample_data/test_fixtures/future_valid.csv").read_bytes()
    with Session(engine) as db:
        user=AuthenticatedUser("demo-administrator","administrator",demo=True)
        preview=preview_source(db,user,"future_valid.csv",content)
        committed=commit_source(db,user,preview["import_batch_id"])
        latest=latest_successful_run(db)
        payload=run_payload(db,latest)
        assert committed["status"]=="COMMITTED"
        assert latest.cutoff_date.year==2030
        assert any(row["account"]=="NEW FUTURE ACCOUNT" for row in payload["priorities"])
        assert payload["cart"]["status"]=="Predictive Context Unavailable / Insufficient Data"
        duplicate=preview_source(db,user,"future_valid.csv",content)
        assert duplicate["duplicate_committed_file"] and not duplicate["can_commit"]
        with pytest.raises(HTTPException) as blocked:
            commit_source(db,user,duplicate["import_batch_id"])
        assert blocked.value.status_code==409
    get_settings.cache_clear()
