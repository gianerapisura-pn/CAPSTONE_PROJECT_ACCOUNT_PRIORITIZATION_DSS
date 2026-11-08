"""Page-read performance contracts using isolated SQLite and local signing keys."""
import asyncio
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import json
from threading import Event
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric import ec
import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.orm import Session

from app.auth import dependencies as auth
from app.core.config import Settings
from app.db.models import (
    AccountContextSnapshot, AccountPriorityResult, AnalyticsRun, Base,
    BusinessBaselineRecord, DimAccount, ModelRun, RFMResult,
    RankingBacktestRecord, SensitivitySummaryRecord, SettlementResult,
)
from app.db.repository import current_account_rows, run_payload
from app import main


@pytest.fixture
def published_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        run = AnalyticsRun(status="successful", analysis_reference_date=date(2025, 12, 31),
                           completed_at=datetime.now(timezone.utc))
        account = DimAccount(standardized_account_name="Test Business", display_name="Test Business")
        db.add_all([run, account])
        db.flush()
        identity = {"analysis_run_id": run.analysis_run_id, "account_key": account.account_key}
        db.add_all([
            AccountContextSnapshot(**identity, standardized_account_name="Test Business",
                b2b_priority_eligible=True, account_status="Client-Confirmed Active", current_actionable=True),
            RFMResult(**identity, payload={"account": "Test Business", "recency_days": 12,
                "frequency": 4, "monetary": 500, "r_score": 3, "f_score": 3, "m_score": 3}),
            SettlementResult(**identity, payload={"account": "Test Business",
                "average_settlement_days": 9, "settlement_invoice_count": 4}),
            AccountPriorityResult(**identity, standardized_account_name="Test Business",
                payload={"account": "Test Business", "priority_rank": 1, "priority_group": "High"}),
            ModelRun(analysis_run_id=run.analysis_run_id, model_version="synthetic-test", status="Validated",
                payload={"predictions": {"Test Business": "With Future Sales"}, "model_version": "synthetic-test"}),
            SensitivitySummaryRecord(analysis_run_id=run.analysis_run_id, weight_range=0.1,
                payload={"min_spearman": 1.0, "max_group_movement_rate": 0.0}),
            BusinessBaselineRecord(analysis_run_id=run.analysis_run_id, year=2025,
                payload={"year": 2025, "all_recorded_sales": 500}),
            RankingBacktestRecord(analysis_run_id=run.analysis_run_id, payload={"status": "synthetic-test"}),
        ])
        db.commit()
        yield db
    engine.dispose()


@pytest.mark.parametrize("endpoint,kwargs", [
    (main.dashboard, {}), (main.native_overview, {}), (main.native_insights, {}),
    (main.native_validation, {}), (main.account_priorities, {}),
    (main.predictive, {}), (main.sensitivity, {"account_key": None}),
])
def test_page_response_matches_full_payload_with_fewer_queries(published_db, monkeypatch, endpoint, kwargs):
    db = published_db
    queries = []
    def record(*args):
        queries.append(args[2])
    event.listen(db.bind, "before_cursor_execute", record)
    viewer = auth.AuthenticatedUser("test-viewer", "management")
    optimized = endpoint(user=viewer, db=db, **kwargs)
    optimized_queries = len(queries)
    queries.clear()
    monkeypatch.setattr(main, "run_payload", lambda db, run, **_: run_payload(db, run))
    original = endpoint(user=viewer, db=db, **kwargs)
    assert optimized == original
    assert optimized_queries < len(queries)
    event.remove(db.bind, "before_cursor_execute", record)


def test_page_reads_new_successful_publication_not_failed_or_in_progress(published_db):
    db = published_db
    viewer = auth.AuthenticatedUser("test-viewer", "administrator")
    old = main.native_insights(user=viewer, db=db)["run"]["analysis_run_id"]
    later = datetime.now(timezone.utc) + timedelta(seconds=1)
    db.add_all([
        AnalyticsRun(status="failed", started_at=later),
        AnalyticsRun(status="running", started_at=later),
    ])
    db.commit()
    assert main.native_insights(user=viewer, db=db)["run"]["analysis_run_id"] == old
    new = AnalyticsRun(status="successful", started_at=later, completed_at=later,
                       analysis_reference_date=date(2027, 12, 31))
    db.add(new)
    db.commit()
    result = main.native_insights(user=viewer, db=db)
    assert result["run"]["analysis_run_id"] == new.analysis_run_id
    assert result["run"]["analysis_reference_date"] == "2027-12-31"


@pytest.mark.parametrize("missing", [SettlementResult, AccountPriorityResult, AccountContextSnapshot])
def test_account_join_preserves_missing_evidence_and_cannot_read_other_runs(published_db, missing):
    db = published_db
    run = db.scalar(select(AnalyticsRun))
    account = db.scalar(select(DimAccount))
    expected = current_account_rows(db, run)[0]
    db.execute(delete(missing).where(missing.analysis_run_id == run.analysis_run_id))
    other = AnalyticsRun(status="successful", analysis_reference_date=date(2030, 12, 31))
    db.add(other); db.flush()
    identity = {"analysis_run_id": other.analysis_run_id, "account_key": account.account_key}
    db.add_all([
        AccountContextSnapshot(**identity, standardized_account_name="Different future context",
            b2b_priority_eligible=False, account_status="Client-Confirmed Closed", current_actionable=False),
        SettlementResult(**identity, payload={"average_settlement_days": 999}),
        AccountPriorityResult(**identity, standardized_account_name="Different future context",
            payload={"priority_rank": 999, "priority_group": "Low"}),
    ])
    db.commit()
    rows = current_account_rows(db, run)
    if missing is AccountContextSnapshot:
        assert rows == []
    else:
        assert len(rows) == 1
        assert rows[0]["account"] == expected["account"]
        assert rows[0]["analysis_run_id"] == run.analysis_run_id
        assert rows[0]["current_actionable"] is True
        if missing is SettlementResult:
            assert rows[0]["average_settlement_days"] is None
            assert rows[0]["criteria_complete"] is False
        else:
            assert rows[0]["priority_rank"] is None
            assert rows[0]["is_ranked"] is False


@pytest.fixture
def signed_tokens(monkeypatch):
    settings = Settings(_env_file=None, demo_mode=False,
                        supabase_url="https://test-project.invalid")
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    auth._jwks_client.cache_clear()
    keys = [ec.generate_private_key(ec.SECP256R1()) for _ in range(2)]
    available = [0]
    requests = []
    def fetch(request, **kwargs):
        requests.append(request.full_url)
        public = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(keys[available[0]].public_key()))
        public.update(kid=str(available[0]), use="sig", alg="ES256")
        return BytesIO(json.dumps({"keys": [public]}).encode())
    monkeypatch.setattr("urllib.request.urlopen", fetch)
    def token(index=0, **overrides):
        claims = {"sub": "test-user", "aud": "authenticated", "iss": settings.jwt_issuer,
                  "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
        claims.update(overrides)
        return jwt.encode(claims, keys[index], algorithm="ES256", headers={"kid": str(index)})
    yield settings, token, available, requests
    auth._jwks_client.cache_clear()


def test_cached_public_keys_still_verify_every_token_and_refresh_on_rotation(signed_tokens):
    settings, token, available, requests = signed_tokens
    assert auth._verify_supabase_token(token())["sub"] == "test-user"
    assert auth._verify_supabase_token(token())["sub"] == "test-user"
    assert len(requests) == 1
    for overrides in (
        {"exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        {"aud": "wrong-audience"}, {"iss": "https://wrong-issuer.invalid"},
    ):
        with pytest.raises(HTTPException) as error:
            auth._verify_supabase_token(token(**overrides))
        assert error.value.status_code == 401
    # A mismatched signature with an existing key ID must also fail.
    forged = jwt.encode({"sub": "test-user", "exp": 9999999999},
                        ec.generate_private_key(ec.SECP256R1()),
                        algorithm="ES256", headers={"kid": "0"})
    with pytest.raises(HTTPException):
        auth._verify_supabase_token(forged)
    available[0] = 1
    assert auth._verify_supabase_token(token(1))["sub"] == "test-user"
    assert len(requests) == 2
    # Cache expiry must fetch the current set, even with a known key ID.
    auth._jwks_client(settings.supabase_url).jwk_set_cache.lifespan = 0
    assert auth._verify_supabase_token(token(1))["sub"] == "test-user"
    assert len(requests) == 3


def test_cached_keys_do_not_cache_profile_roles_or_access(signed_tokens):
    _, token, _, requests = signed_tokens
    profile = SimpleNamespace(is_active=True, role="management", display_name="Test")
    db = SimpleNamespace(get=lambda *_: profile)
    bearer = "Bearer " + token()
    assert asyncio.run(auth.require_user(bearer, db)).role == "management"
    profile.role = "administrator"
    assert asyncio.run(auth.require_user(bearer, db)).role == "administrator"
    profile.is_active = False
    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.require_user(bearer, db))
    assert error.value.status_code == 403
    assert len(requests) == 1


def test_auth_network_wait_does_not_block_event_loop(monkeypatch):
    started, release = Event(), Event()
    monkeypatch.setattr(auth, "get_settings", lambda: Settings(_env_file=None, demo_mode=False))
    def verify(_):
        started.set()
        assert release.wait(3), "Event loop could not release waiting token verification"
        return {"sub": "test-user"}
    monkeypatch.setattr(auth, "_verify_supabase_token", verify)
    profile = SimpleNamespace(is_active=True, role="management", display_name="Test")
    async def check():
        task = asyncio.create_task(auth.require_user("Bearer local-test", SimpleNamespace(get=lambda *_: profile)))
        try:
            assert await asyncio.wait_for(asyncio.to_thread(started.wait, 1), timeout=2)
        finally:
            release.set()
        assert (await task).role == "management"
    asyncio.run(check())
