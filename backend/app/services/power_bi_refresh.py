from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import PowerBIRefresh
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
API_ROOT = "https://api.powerbi.com/v1.0/myorg"


def configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if not settings.power_bi_auto_refresh_enabled or settings.demo_mode:
        return False
    identifiers = (
        settings.power_bi_tenant_id, settings.power_bi_client_id,
        settings.power_bi_workspace_id, settings.power_bi_dataset_id,
    )
    try:
        return bool(settings.power_bi_client_secret) and all(
            UUID(value) for value in identifiers
        )
    except (ValueError, TypeError):
        return False


def enqueue_refresh(db: Session, run_id: str) -> None:
    db.add(PowerBIRefresh(
        analysis_run_id=run_id,
        status="pending" if configured() else "not_configured",
    ))


def public_status(row: PowerBIRefresh | None, run_id: str | None) -> dict:
    return {
        "analysis_run_id": run_id,
        "configured": configured(),
        "status": row.status if row else "not_requested",
        "attempt_count": row.attempt_count if row else 0,
        "requested_at": row.requested_at.isoformat() if row and row.requested_at else None,
        "completed_at": row.completed_at.isoformat() if row and row.completed_at else None,
        "error_code": row.error_code if row else None,
    }


def _access_token(settings: Settings) -> str:
    response = httpx.post(
        f"https://login.microsoftonline.com/{settings.power_bi_tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": settings.power_bi_client_id,
            "client_secret": settings.power_bi_client_secret,
            "scope": "https://analysis.windows.net/powerbi/api/.default",
            "grant_type": "client_credentials",
        },
        timeout=10.0,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise ValueError("Microsoft token response did not contain an access token.")
    return token


def _refresh_url(settings: Settings) -> str:
    return (
        f"{API_ROOT}/groups/{settings.power_bi_workspace_id}"
        f"/datasets/{settings.power_bi_dataset_id}/refreshes"
    )


def _error_code(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"power_bi_http_{exc.response.status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "power_bi_timeout"
    if isinstance(exc, httpx.RequestError):
        return "power_bi_connection_error"
    return "power_bi_invalid_response"


def request_refresh(run_id: str) -> None:
    settings = get_settings()
    if not configured(settings):
        return
    with SessionLocal() as db:
        claimed = db.execute(
            update(PowerBIRefresh)
            .where(PowerBIRefresh.analysis_run_id == run_id, PowerBIRefresh.status == "pending")
            .values(
                status="requesting", updated_at=datetime.now(timezone.utc),
                requested_at=datetime.now(timezone.utc),
                attempt_count=PowerBIRefresh.attempt_count + 1, error_code=None,
            )
        ).rowcount
        db.commit()
        if not claimed:
            return
    try:
        token = _access_token(settings)
        response = httpx.post(
            _refresh_url(settings),
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        response.raise_for_status()
        if response.status_code != 202:
            raise ValueError("Power BI did not accept the refresh request.")
        request_id = response.headers.get("x-ms-request-id")
        try:
            request_id = str(UUID(request_id)) if request_id else None
        except ValueError:
            request_id = None
        with SessionLocal() as db:
            row = db.get(PowerBIRefresh, run_id)
            row.status = "requested"
            row.refresh_request_id = request_id
            row.requested_at = datetime.now(timezone.utc)
            row.updated_at = row.requested_at
            row.error_code = None if request_id else "request_id_unavailable"
            db.commit()
    except Exception as exc:
        logger.warning("Power BI refresh request failed for run %s: %s", run_id, _error_code(exc))
        with SessionLocal() as db:
            row = db.get(PowerBIRefresh, run_id)
            row.status = "failed"
            row.error_code = _error_code(exc)
            row.updated_at = datetime.now(timezone.utc)
            db.commit()


def sync_refresh_status(db: Session, row: PowerBIRefresh | None) -> None:
    if not row or row.status not in {"requested", "refreshing"} or not row.refresh_request_id:
        return
    if not configured():
        return
    settings = get_settings()
    try:
        token = _access_token(settings)
        response = httpx.get(
            f"{_refresh_url(settings)}/{row.refresh_request_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        response.raise_for_status()
        result = response.json()
        state = result.get("status")
        if state == "Completed":
            row.status = "completed"
            row.completed_at = datetime.now(timezone.utc)
            row.error_code = None
        elif state == "Failed":
            row.status = "failed"
            row.error_code = "power_bi_refresh_failed"
        elif state == "Unknown" or response.status_code == 202:
            row.status = "refreshing"
        else:
            return
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        logger.warning("Power BI refresh status check failed: %s", _error_code(exc))
        db.rollback()


def retry_refresh(db: Session, run_id: str) -> bool:
    if not configured():
        return False
    row = db.get(PowerBIRefresh, run_id)
    if row is None:
        db.add(PowerBIRefresh(analysis_run_id=run_id, status="pending"))
        db.commit()
        return True
    changed = db.execute(
        update(PowerBIRefresh)
        .where(
            PowerBIRefresh.analysis_run_id == run_id,
            PowerBIRefresh.status.in_(("failed", "not_configured")),
        )
        .values(
            status="pending", refresh_request_id=None, error_code=None,
            requested_at=None, completed_at=None, updated_at=datetime.now(timezone.utc),
        )
    ).rowcount
    db.commit()
    return bool(changed)


def recover_pending_refreshes() -> None:
    if not configured():
        return
    with SessionLocal() as db:
        # A crashed process may have sent a request without saving its ID. Never
        # auto-retry that ambiguous attempt; require administrator verification.
        db.execute(
            update(PowerBIRefresh)
            .where(
                PowerBIRefresh.status == "requesting",
                PowerBIRefresh.updated_at < datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            .values(
                status="failed", error_code="request_outcome_unknown_verify_before_retry",
                updated_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        run_ids = db.scalars(select(PowerBIRefresh.analysis_run_id).where(
            PowerBIRefresh.status == "pending"
        )).all()
    for run_id in run_ids:
        request_refresh(run_id)


def reconcile_active_refreshes() -> None:
    if not configured():
        return
    with SessionLocal() as db:
        rows = db.scalars(select(PowerBIRefresh).where(
            PowerBIRefresh.status.in_(("requested", "refreshing")),
            PowerBIRefresh.refresh_request_id.is_not(None),
        )).all()
        for row in rows:
            sync_refresh_status(db, row)


async def supervise_refreshes() -> None:
    while True:
        try:
            await asyncio.to_thread(recover_pending_refreshes)
            await asyncio.to_thread(reconcile_active_refreshes)
        except Exception:
            logger.exception("Power BI refresh supervisor could not check queued requests.")
        await asyncio.sleep(30)
