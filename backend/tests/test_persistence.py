from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.models import AnalyticsRun, Base, RawSourceRow
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
        assert any(row["account"]=="New Future Account" for row in payload["rfm"])
        assert payload["priorities"]
        assert {"latest_valid_si_date", "frequency_count", "monetary_value", "average_settlement_days",
                "valid_settlement_record_count", "predicted_inactivity_risk"} <= payload["priorities"][0].keys()
        from app.schemas.api import AccountPriorityResponse
        AccountPriorityResponse.model_validate(payload["priorities"][0])
        assert payload["cart"]["status"]=="model_unavailable"
        duplicate=preview_source(db,user,"future_valid.csv",content)
        assert duplicate["duplicate_committed_file"] and not duplicate["can_commit"]
        with pytest.raises(HTTPException) as blocked:
            commit_source(db,user,duplicate["import_batch_id"])
        assert blocked.value.status_code==409
    get_settings.cache_clear()


def test_raw_collection_blanks_are_preserved_through_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_STORAGE_PATH", str(tmp_path / "source"))
    get_settings.cache_clear()
    content = (
        "ACCOUNT NAMES,SI NO.,SI DATE,SI AMOUNT,CR NO.,CR DATE,CR AMOUNT,EWT,PAYMENT MODE,PAYMENT STATUS\n"
        "Blank EWT,1,2030-01-01,100,CR-1,2030-01-01,100,,Bank,Fully Paid\n"
        "Recorded Zero,2,2030-01-01,100,CR-2,2030-01-01,100,0.00,Bank,Fully Paid\n"
    ).encode()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = AuthenticatedUser("demo-administrator", "administrator", demo=True)
        preview = preview_source(db, user, "collection-values.csv", content)
        commit_source(db, user, preview["import_batch_id"])
        raw_rows = db.scalars(select(RawSourceRow).order_by(RawSourceRow.source_row_number)).all()
        assert raw_rows[0].ewt_raw == ""
        assert raw_rows[1].ewt_raw == "0.00"
        assert raw_rows[0].canonical_payload["EWT"] == ""
        assert raw_rows[1].canonical_payload["EWT"] == "0.00"
    get_settings.cache_clear()


def test_preview_counts_unique_rows_by_sheet_not_issue_objects(tmp_path, monkeypatch):
    from io import BytesIO
    import pandas as pd
    from app.db.models import ImportBatch

    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_STORAGE_PATH", str(tmp_path / "source"))
    get_settings.cache_clear()
    base = {
        "ACCOUNT NAMES": "A", "SI NO.": "1", "SI DATE": "2035-01-01",
        "SI AMOUNT": "100", "CR NO.": "1", "CR DATE": "2035-01-02",
        "CR AMOUNT": "100", "EWT": "0", "PAYMENT MODE": "Bank",
        "PAYMENT STATUS": "Needs Review",
    }
    first = pd.DataFrame([base])
    second = pd.DataFrame([{**base, "ACCOUNT NAMES": "", "SI DATE": "bad"}])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        first.to_excel(writer, sheet_name="A", index=False)
        second.to_excel(writer, sheet_name="B", index=False)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = AuthenticatedUser("demo-administrator", "administrator", demo=True)
        preview = preview_source(db, user, "rows.xlsx", output.getvalue())
        batch = db.get(ImportBatch, preview["import_batch_id"])
        assert batch.rows_discovered == 2
        assert batch.rows_flagged == 2
        assert batch.rows_excluded == 1
        assert batch.rows_accepted == 1
    get_settings.cache_clear()


def test_import_commit_response_preserves_prioritized_account_count():
    from app.schemas.api import ImportCommitResponse

    response = ImportCommitResponse.model_validate({
        "status": "COMMITTED",
        "import_batch_id": "batch",
        "analysis_run_id": "run",
        "prioritized_accounts": 0,
        "cutoff_date": None,
    })
    assert response.model_dump()["prioritized_accounts"] == 0
