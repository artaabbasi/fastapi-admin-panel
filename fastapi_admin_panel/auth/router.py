"""
Auth endpoints — works with both sync Engine and AsyncEngine (asyncpg).

  POST /admin/api/auth/login   → {access_token, token_type, username}
  GET  /admin/api/auth/me      → {id, username}
  POST /admin/api/auth/logout  → 200
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from .deps import make_require_admin
from .models import AdminUser
from .utils import create_token, verify_password

try:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    _ASYNC_AVAILABLE = True
except ImportError:
    _ASYNC_AVAILABLE = False
    AsyncEngine = None  # type: ignore[assignment,misc]


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


def build_auth_router(engine, secret_key: str, expire_hours: int) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])
    require_admin = make_require_admin(secret_key)

    is_async = _ASYNC_AVAILABLE and isinstance(engine, AsyncEngine)

    if is_async:
        _add_async_routes(router, engine, secret_key, expire_hours, require_admin)
    else:
        _add_sync_routes(router, engine, secret_key, expire_hours, require_admin)

    return router


# ── Sync routes ───────────────────────────────────────────────────────────────

def _add_sync_routes(router, engine, secret_key, expire_hours, require_admin):
    from sqlalchemy.orm import Session

    @router.post("/login", response_model=TokenResponse)
    def login(body: LoginRequest):
        with Session(engine) as session:
            row = session.execute(
                select(AdminUser).where(AdminUser.c.username == body.username)
            ).first()

        if row is None or not row.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not verify_password(body.password, row.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = create_token(row.id, row.username, secret_key, expire_hours)
        return TokenResponse(access_token=token, username=row.username)

    @router.get("/me")
    def me(payload: dict = Depends(require_admin)):
        return {"id": payload["sub"], "username": payload["username"]}

    @router.post("/logout", status_code=200)
    def logout():
        return {"detail": "Logged out"}


# ── Async routes ──────────────────────────────────────────────────────────────

def _add_async_routes(router, engine, secret_key, expire_hours, require_admin):
    from sqlalchemy.ext.asyncio import AsyncSession

    @router.post("/login", response_model=TokenResponse)
    async def login(body: LoginRequest):
        async with AsyncSession(engine) as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.c.username == body.username)
            )
            row = result.first()

        if row is None or not row.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not verify_password(body.password, row.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = create_token(row.id, row.username, secret_key, expire_hours)
        return TokenResponse(access_token=token, username=row.username)

    @router.get("/me")
    async def me(payload: dict = Depends(require_admin)):
        return {"id": payload["sub"], "username": payload["username"]}

    @router.post("/logout", status_code=200)
    async def logout():
        return {"detail": "Logged out"}
