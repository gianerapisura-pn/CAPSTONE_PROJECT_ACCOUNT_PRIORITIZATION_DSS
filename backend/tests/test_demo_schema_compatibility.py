from datetime import date

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db import session as db_session
from app.db.models import (
    AnalyticsRun, Base, ImportBatch, ImportRowIssue, InvoiceGroupRecord, RawSourceRow,
)


def test_local_demo_accepts_both_browser_hostnames():
    origins = Settings.model_fields["cors_allowed_origins"].default.split(",")
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


def test_legacy_demo_schema_is_upgraded_without_losing_rows(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with Session(engine) as db:
        batch = ImportBatch(file_name="legacy.csv", file_hash="legacy", status="committed")
        run = AnalyticsRun(status="successful", analysis_reference_date=date(2030, 6, 1))
        db.add_all([batch, run])
        db.flush()
        run_id = run.analysis_run_id
        db.add_all([
            RawSourceRow(
                import_batch_id=batch.import_batch_id, source_sheet="CSV", source_row_number=2,
                canonical_payload={
                    "CUSTOMER NAME": "LEGACY ACCOUNT", "SI NO.": "SI-1",
                    "SI DATE": "2030-01-01", "SI AMOUNT": "100",
                    "CR NO.": "CR-1", "CR DATE": "2030-01-11",
                    "CR AMOUNT": "100", "EWT": "0",
                    "PAYMENT MODE": "Bank", "PAYMENT STATUS": "Fully Paid",
                },
            ),
            ImportRowIssue(
                import_batch_id=batch.import_batch_id, severity="warning",
                message="Legacy issue",
            ),
            InvoiceGroupRecord(
                invoice_group_id="legacy-invoice", import_batch_id=batch.import_batch_id,
                standardized_account_name="LEGACY ACCOUNT", si_no="SI-1",
                si_date=date(2030, 1, 1), si_amount=100,
                payment_status="Fully Paid", final_cr_date=date(2030, 1, 11),
                total_cr_amount=100, total_ewt=0, reconciliation_amount=100,
                reconciliation_difference=0, reconciled=True, is_cancelled=False,
            ),
        ])
        db.commit()

    dropped = {
        "analytics_runs": (
            "row_counts", "eligible_account_counts", "model_version", "predictive_status",
        ),
        "import_row_issues": ("issue_type",),
        "invoice_groups": (
            "conflicting_invoice", "rfm_eligible", "settlement_eligible", "settlement_days",
        ),
        "raw_source_rows": tuple(db_session.RAW_SOURCE_KEYS),
    }
    with engine.begin() as connection:
        for table, columns in dropped.items():
            for column in columns:
                connection.execute(text(f'ALTER TABLE "{table}" DROP COLUMN "{column}"'))
        assert "CUSTOMER NAME" in connection.execute(text(
            "SELECT canonical_payload FROM raw_source_rows"
        )).scalar()

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    monkeypatch.setattr(db_session, "get_settings", lambda: Settings(
        demo_mode=True, app_env="test"
    ))
    db_session.init_database()
    db_session.init_database()

    schema = inspect(engine)
    for table, columns in dropped.items():
        present = {column["name"] for column in schema.get_columns(table)}
        assert set(columns) <= present
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM analytics_runs")).scalar() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM raw_source_rows")).scalar() == 1
        raw = connection.execute(text(
            "SELECT raw_source_row_id, canonical_payload, customer_name_raw FROM raw_source_rows"
        )).one()
        assert raw.customer_name_raw == "LEGACY ACCOUNT", raw
        assert connection.execute(text(
            "SELECT issue_type FROM import_row_issues"
        )).scalar() == "validation"
        assert connection.execute(text(
            "SELECT rfm_eligible, settlement_eligible, settlement_days FROM invoice_groups"
        )).one() == (1, 1, 10)
    with factory() as db:
        assert db.get(AnalyticsRun, run_id).row_counts == {}
