from __future__ import annotations
from sqlalchemy import Uuid, create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.db.models import Base


def make_engine():
    url = get_settings().database_url
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=make_engine())


DEMO_ADDITIONS = {
    "import_batches": {
        "analysis_reference_date": "DATE",
    },
    "dim_account": {
        "entity_type": "VARCHAR(80)",
        "business_category": "VARCHAR(160)",
        "primary_business_type": "VARCHAR(160)",
        "b2b_priority_eligible": "BOOLEAN NOT NULL DEFAULT 0",
        "account_status": "VARCHAR(80)",
        "last_verified": "DATE",
    },
    "analytics_runs": {
        "analysis_reference_date": "DATE",
        "latest_valid_si_date": "DATE",
        "latest_final_cr_date": "DATE",
        "methodology_version": "VARCHAR(80)",
        "mcs_status": "VARCHAR(40)",
        "context_metrics": "JSON DEFAULT '{}'",
    },
    "predictive_model_versions": {
        "model_family": "VARCHAR(120)",
        "model_parameters": "JSON DEFAULT '{}'",
        "target_definition": "TEXT",
        "primary_selection_metric": "VARCHAR(120)",
        "decision_threshold": "FLOAT",
    },
}


def _ensure_demo_schema() -> None:
    """Apply additive compatibility columns to an existing isolated SQLite database."""
    engine = SessionLocal.kw["bind"]
    with engine.begin() as connection:
        schema = inspect(engine)
        tables = set(schema.get_table_names())
        for table_name, additions in DEMO_ADDITIONS.items():
            if table_name not in tables:
                continue
            columns = {column["name"] for column in schema.get_columns(table_name)}
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(text(
                        f'ALTER TABLE "{table_name}" ADD COLUMN "{name}" {sql_type}'
                    ))

        legacy_ids = {
            "demo-administrator": "00000000-0000-4000-8000-000000000001",
            "demo-management": "00000000-0000-4000-8000-000000000002",
        }
        for table_name, column_name in (
            ("import_batches", "uploaded_by"), ("account_aliases", "approved_by"),
            ("account_alias_review", "reviewed_by"), ("audit_log", "actor_user_id"),
        ):
            if table_name not in tables:
                continue
            columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
            if column_name not in columns:
                continue
            for legacy_id, uuid_id in legacy_ids.items():
                connection.execute(text(
                    f'UPDATE "{table_name}" SET "{column_name}" = :uuid_id '
                    f'WHERE "{column_name}" = :legacy_id'
                ), {"uuid_id": uuid_id, "legacy_id": legacy_id})

        for table in Base.metadata.sorted_tables:
            if table.name not in tables:
                continue
            for column in table.columns:
                if isinstance(column.type, Uuid):
                    connection.execute(text(
                        f'UPDATE "{table.name}" SET "{column.name}" = '
                        f'replace("{column.name}", \'-\', \'\') '
                        f'WHERE length("{column.name}") = 36'
                    ))


def init_database() -> None:
    settings = get_settings()
    if settings.demo_mode or settings.app_env == "test":
        Base.metadata.create_all(bind=SessionLocal.kw["bind"])
        _ensure_demo_schema()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
