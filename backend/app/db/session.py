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


def _ensure_demo_schema() -> None:
    """Apply additive compatibility columns to existing isolated SQLite databases."""
    engine = SessionLocal.kw["bind"]
    columns = {column["name"] for column in inspect(engine).get_columns("analytics_runs")}
    additions = {
        "mcs_status": "ALTER TABLE analytics_runs ADD COLUMN mcs_status VARCHAR(40)",
        "context_metrics": "ALTER TABLE analytics_runs ADD COLUMN context_metrics JSON DEFAULT '{}'",
    }
    with engine.begin() as connection:
        for name, statement in additions.items():
            if name not in columns:
                connection.execute(text(statement))

        legacy_ids = {
            "demo-administrator": "00000000-0000-4000-8000-000000000001",
            "demo-management": "00000000-0000-4000-8000-000000000002",
        }
        identity_columns = (
            ("import_batches", "uploaded_by"),
            ("account_aliases", "approved_by"),
            ("account_alias_review", "reviewed_by"),
            ("audit_log", "actor_user_id"),
        )
        schema = inspect(engine)
        for table_name, column_name in identity_columns:
            table_columns = {
                column["name"] for column in schema.get_columns(table_name)
            }
            if column_name not in table_columns:
                continue
            for legacy_id, uuid_id in legacy_ids.items():
                connection.execute(
                    text(
                        f"UPDATE {table_name} SET {column_name} = :uuid_id "
                        f"WHERE {column_name} = :legacy_id"
                    ),
                    {"uuid_id": uuid_id, "legacy_id": legacy_id},
                )

        # Older demo rows used dashed UUID text; SQLAlchemy Uuid stores SQLite values as 32 hex characters.
        for table in Base.metadata.sorted_tables:
            for column in table.columns:
                if not isinstance(column.type, Uuid):
                    continue
                connection.execute(text(
                    f'UPDATE "{table.name}" '
                    f"""SET "{column.name}" = replace("{column.name}", '-', '') """
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
