from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    role: str


async def require_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    """Production hook for Supabase JWT validation.

    Demo mode accepts a missing token as an administrator so the prototype runs locally.
    Production deployments should validate the Supabase JWT and load `user_profiles.role`.
    """
    settings = get_settings()
    if settings.demo_mode:
        return AuthenticatedUser(user_id="demo-user", role="administrator")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return AuthenticatedUser(user_id="supabase-user", role="management")


async def require_admin(user: AuthenticatedUser = Depends(require_user)) -> AuthenticatedUser:
    if user.role != "administrator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required.")
    return user
