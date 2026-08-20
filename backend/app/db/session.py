from __future__ import annotations

from sqlalchemy import create_engine
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


def init_database() -> None:
    settings = get_settings()
    if settings.demo_mode or settings.app_env == "test":
        Base.metadata.create_all(bind=SessionLocal.kw["bind"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
