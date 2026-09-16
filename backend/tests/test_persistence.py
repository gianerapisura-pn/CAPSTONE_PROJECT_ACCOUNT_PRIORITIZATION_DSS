import csv
from datetime import datetime, timezone
from io import StringIO

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.models import AnalyticsRun, Base, ModelRun, RawSourceRow
from app.auth.dependencies import AuthenticatedUser, DEMO_ADMIN_USER_ID, DEMO_MANAGEMENT_USER_ID
from app.core.config import get_settings
from app.db.repository import current_account_rows, latest_successful_run, run_payload
from app.services.import_workflow import commit_source, preview_source
from fastapi import HTTPException
import pytest


def test_export_currency_classification_preserves_analytical_semantics():
    from app.main import _is_currency_column

    for column in (
        "recency_contribution",
        "frequency_contribution",
        "monetary_contribution",
        "settlement_contribution",
    ):
        assert not _is_currency_column(column)
    for column in ("monetary", "monetary_value", "si_amount"):
        assert _is_currency_column(column)


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
        user=AuthenticatedUser(DEMO_ADMIN_USER_ID,"administrator",demo=True)
        preview=preview_source(db,user,"future_valid.csv",content)
        committed=commit_source(db,user,preview["import_batch_id"])
        latest=latest_successful_run(db)
        payload=run_payload(db,latest)
        assert committed["status"]=="COMMITTED"
        assert committed["warnings"] == latest.warnings
        assert latest.cutoff_date.year==2030
        assert any(row["account"]=="New Future Account" for row in payload["rfm"])
        assert payload["priorities"]
        assert {"latest_valid_si_date", "frequency_count", "monetary_value", "average_settlement_days",
                "valid_settlement_record_count", "predicted_inactivity_risk"} <= payload["priorities"][0].keys()
        from app.schemas.api import AccountPriorityResponse
        AccountPriorityResponse.model_validate(payload["priorities"][0])
        assert payload["cart"]["status"]=="model_unavailable"
        profiles = current_account_rows(db, latest)
        future = next(row for row in profiles if row["account"] == "New Future Account")
        assert len(profiles) == len(payload["rfm"])
        assert not future["mcs_eligible"]
        assert future["priority_rank"] is None
        assert future["priority_group"] is None
        assert future["final_priority_score"] is None
        assert future["average_settlement_days"] is None
        assert future["settlement_invoice_count"] == 0
        assert "No valid Historical Settlement Duration" in future["mcs_eligibility_reason"]
        assert future["rfm_score"] is not None

        model_run = db.scalar(
            select(ModelRun).where(ModelRun.analysis_run_id == latest.analysis_run_id)
        )
        model_run.payload = {
            **model_run.payload,
            "model_version": "cart-test-current",
            "predictions": {"New Future Account": "Higher"},
        }
        db.flush()

        from app.main import account_detail, accounts, dashboard, export_dataset
        listed = accounts(
            search="New Future", priority_group=None,
            predicted_inactivity_risk="Higher", inactivity_risk=None,
            eligibility="not_ranked", page=1, page_size=25, user=user, db=db,
        )
        assert listed["total"] == 1
        assert listed["analysis_run_id"] == latest.analysis_run_id
        assert listed["analysis_cutoff"] == latest.cutoff_date.isoformat()
        assert listed["updated_at"] == latest.completed_at.isoformat()
        assert listed["items"][0]["account_key"] == future["account_key"]
        all_rows = accounts(
            search="", priority_group=None, predicted_inactivity_risk=None,
            inactivity_risk=None, eligibility=None, page=1, page_size=500,
            user=user, db=db,
        )
        published_ranks = {row["account_key"]: row["priority_rank"] for row in all_rows["items"]}
        high_rows = accounts(
            search="", priority_group="High", predicted_inactivity_risk=None,
            inactivity_risk=None, eligibility=None, page=1, page_size=500,
            user=user, db=db,
        )
        assert all(row["priority_rank"] == published_ranks[row["account_key"]] for row in high_rows["items"])
        detail = account_detail(future["account_key"], user=user, db=db)
        assert detail["rfm"]["account"] == "New Future Account"
        assert detail["priority"] is None
        assert detail["settlement"]["average_settlement_days"] is None
        assert detail["cart"]["predicted_inactivity_risk"] == "Higher"
        assert detail["sensitivity"] is None
        summary = dashboard(user=user, db=db)
        assert summary["total_standardized_accounts"] == len(payload["rfm"])
        assert sum(summary["priority_group_counts"].values()) == len(payload["priorities"])
        assert summary["risk_counts"]["Higher"] == 1
        exported = export_dataset(
            "priorities", "csv", "New Future", None, "Higher", None,
            "not_ranked", user, db,
        )
        exported_text = exported.body.decode()
        assert "New Future Account" in exported_text
        assert "Alpha Infra Corp" not in exported_text
        management = AuthenticatedUser(DEMO_MANAGEMENT_USER_ID, "management", demo=True)
        for format in ("csv", "xlsx"):
            allowed = export_dataset(
                "priorities", format, "", None, None, None, None, management, db,
            )
            assert allowed.status_code == 200
        for technical_dataset in ("cart", "sensitivity", "runs", "transactions", "rfm", "settlement"):
            with pytest.raises(HTTPException) as forbidden:
                export_dataset(
                    technical_dataset, "csv", "", None, None, None, None, management, db,
                )
            assert forbidden.value.status_code == 403
        assert export_dataset("cart", "csv", "", None, None, None, None, user, db).status_code == 200

        priority_csv = export_dataset(
            "priorities", "csv", "", None, None, None, None, management, db,
        )
        exported_rows = list(csv.DictReader(StringIO(priority_csv.body.decode())))
        source_ranked = next(row for row in profiles if row["mcs_eligible"])
        exported_ranked = next(
            row for row in exported_rows if row["account"] == source_ranked["account"]
        )
        contribution_fields = (
            "recency_contribution",
            "frequency_contribution",
            "monetary_contribution",
            "settlement_contribution",
        )
        for field in contribution_fields:
            assert float(exported_ranked[field]) == pytest.approx(source_ranked[field])
        assert any(
            exported_ranked[field] != f"{source_ranked[field]:.2f}"
            for field in contribution_fields
        )
        assert exported_ranked["monetary"] == f"{source_ranked['monetary']:.2f}"
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
        user = AuthenticatedUser(DEMO_ADMIN_USER_ID, "administrator", demo=True)
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
        user = AuthenticatedUser(DEMO_ADMIN_USER_ID, "administrator", demo=True)
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
        "warnings": ["Predictive context unavailable."],
    })
    assert response.model_dump()["prioritized_accounts"] == 0
    assert response.model_dump()["warnings"] == ["Predictive context unavailable."]
