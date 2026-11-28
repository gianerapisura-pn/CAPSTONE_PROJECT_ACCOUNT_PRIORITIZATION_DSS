"""Release isolated test database resources before garbage collection."""

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def close_test_database_resources(monkeypatch):
    # Keep strong references until teardown so Python's SQLite resource checks
    # cannot run against a pooled connection belonging to an earlier test.
    engines = []
    sessions = []
    engine_init = Engine.__init__
    session_init = Session.__init__

    def track_engine(self, *args, **kwargs):
        engine_init(self, *args, **kwargs)
        engines.append(self)

    def track_session(self, *args, **kwargs):
        session_init(self, *args, **kwargs)
        sessions.append(self)

    monkeypatch.setattr(Engine, "__init__", track_engine)
    monkeypatch.setattr(Session, "__init__", track_session)
    try:
        yield
    finally:
        for session in reversed(sessions):
            session.close()
        for engine in reversed(engines):
            engine.dispose()
