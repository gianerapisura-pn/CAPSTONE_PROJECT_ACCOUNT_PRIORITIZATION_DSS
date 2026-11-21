from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.db.session import make_engine


@pytest.mark.parametrize("host,port,vercel,expected_port,unpooled,prepare", [
    ("aws-0-ap-southeast-1.pooler.supabase.com", 5432, "1", 6543, True, True),
    ("aws-0-ap-southeast-1.pooler.supabase.com", 6543, "1", 6543, True, True),
    ("db.example.supabase.co", 5432, "1", 5432, True, False),
    ("other-postgres.example", 5432, "1", 5432, True, False),
    ("aws-0-ap-southeast-1.pooler.supabase.com", 5432, "0", 5432, False, False),
])
def test_hosted_pooler_connection_configuration(monkeypatch, host, port, vercel,
                                              expected_port, unpooled, prepare):
    monkeypatch.setenv("VERCEL", vercel)
    url = f"postgresql+psycopg://fixture:fixture@{host}:{port}/postgres?sslmode=require"
    with patch("app.db.session.get_settings", return_value=SimpleNamespace(database_url=url)), \
            patch("app.db.session.create_engine") as build:
        make_engine()
    args, kwargs = build.call_args
    original, actual = make_url(url), make_url(args[0])
    assert actual == original.set(port=expected_port)
    assert kwargs.get("poolclass") is (NullPool if unpooled else None)
    assert kwargs.get("connect_args") == ({"prepare_threshold": None} if prepare else None)
    assert kwargs["pool_pre_ping"] is True


def test_vercel_does_not_change_isolated_sqlite(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    with patch("app.db.session.get_settings", return_value=SimpleNamespace(database_url="sqlite:///:memory:")):
        engine = make_engine()
    try:
        with engine.connect() as conn:
            assert conn.scalar(text("select 1")) == 1
        assert not isinstance(engine.pool, NullPool)
    finally:
        engine.dispose()


def test_request_sessions_release_connections_and_preserve_transactions(tmp_path, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    # Exercise the actual selected pool with a local DBAPI; no production writes.
    url = "postgresql+psycopg://fixture:fixture@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
    captured = {}
    def local_engine(_url, **kwargs):
        captured.update(kwargs)
        return create_engine("sqlite:///" + str(tmp_path / "transactions.sqlite3"),
                             poolclass=kwargs["poolclass"])
    with patch("app.db.session.get_settings", return_value=SimpleNamespace(database_url=url)), \
            patch("app.db.session.create_engine", side_effect=local_engine):
        engine = make_engine()
    opened, closed = [], []
    event.listen(engine, "connect", lambda conn, record: opened.append(record))
    event.listen(engine, "close", lambda conn, record: closed.append(record))
    try:
        with engine.begin() as conn:
            conn.execute(text("create table published (id integer primary key, value text)"))
            conn.execute(text("insert into published values (1, 'retained')"))
        for _ in range(2):
            def read(_index):
                with Session(engine) as db:
                    assert db.scalar(text("select value from published where id=1")) == "retained"
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(read, range(24)))
            assert len(opened) == len(closed)
        with pytest.raises(RuntimeError):
            with Session(engine) as db, db.begin():
                db.execute(text("update published set value='failed' where id=1"))
                raise RuntimeError("failed publication")
        with Session(engine) as db:
            assert db.scalar(text("select value from published where id=1")) == "retained"
        assert len(opened) == len(closed)
        assert captured["connect_args"] == {"prepare_threshold": None}
    finally:
        engine.dispose()
