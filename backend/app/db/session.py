from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
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
