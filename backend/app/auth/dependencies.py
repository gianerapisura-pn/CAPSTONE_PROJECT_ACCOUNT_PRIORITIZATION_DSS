from __future__ import annotations

from dataclasses import dataclass

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import UserProfile
from app.db.session import get_db


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    role: str
    email: str | None = None
    display_name: str | None = None
    demo: bool = False


def _verify_supabase_token(token: str) -> dict:
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") == "HS256":
            response = httpx.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_service_role_key},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        jwks = PyJWKClient(f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")
        key = jwks.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub"]},
        )
    except (jwt.PyJWTError, httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired authentication token.") from exc


async def require_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    settings = get_settings()
    if settings.demo_mode:
        return AuthenticatedUser("demo-administrator", "administrator", "demo@local.invalid", "Demo Administrator", True)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    claims = _verify_supabase_token(authorization.split(" ", 1)[1].strip())
    user_id = str(claims.get("sub") or claims.get("id") or "")
    profile = db.get(UserProfile, user_id)
    if not profile or profile.role not in {"administrator", "management"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="An approved DSS role is required.")
    metadata = claims.get("user_metadata") or {}
    return AuthenticatedUser(user_id, profile.role, claims.get("email"), profile.display_name or metadata.get("full_name"), False)


async def require_admin(user: AuthenticatedUser = Depends(require_user)) -> AuthenticatedUser:
    if user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required.")
    return user
