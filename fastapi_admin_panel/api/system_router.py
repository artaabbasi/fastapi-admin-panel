"""
System endpoints — admin user management.
All routes require a valid admin JWT token.

  GET    /system/users           → list admin users
  POST   /system/users           → create admin user
  PUT    /system/users/{id}      → update username / active flag
  POST   /system/users/{id}/password → change password
  DELETE /system/users/{id}      → delete admin user
"""

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from ..auth.models import AdminUser
from ..auth.utils import hash_password, verify_password

try:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    _ASYNC_AVAILABLE = True
except ImportError:
    _ASYNC_AVAILABLE = False
    AsyncEngine = None  # type: ignore[assignment,misc]


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_active: bool = True


class UpdateUserRequest(BaseModel):
    username: str | None = None
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    new_password: str


def build_system_router(engine, require_admin: Callable) -> APIRouter:
    router = APIRouter(prefix="/system", dependencies=[Depends(require_admin)])
    is_async = _ASYNC_AVAILABLE and isinstance(engine, AsyncEngine)

    if is_async:
        _add_async_routes(router, engine)
    else:
        _add_sync_routes(router, engine)

    return router


# ── helpers ───────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    return {
        "id": row.id,
        "username": row.username,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ── Async routes (asyncpg) ────────────────────────────────────────────────────

def _add_async_routes(router: APIRouter, engine) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    async def get_session():
        async with AsyncSession(engine) as session:
            yield session

    @router.get("/users")
    async def list_users(session: AsyncSession = Depends(get_session)):
        result = await session.execute(select(AdminUser).order_by(AdminUser.c.id))
        return [_row_to_dict(r) for r in result.fetchall()]

    @router.post("/users", status_code=201)
    async def create_user(body: CreateUserRequest, session: AsyncSession = Depends(get_session)):
        exists = (await session.execute(
            select(AdminUser).where(AdminUser.c.username == body.username)
        )).first()
        if exists:
            raise HTTPException(status_code=409, detail="Username already exists")
        await session.execute(AdminUser.insert().values(
            username=body.username,
            hashed_password=hash_password(body.password),
            is_active=body.is_active,
        ))
        await session.commit()
        row = (await session.execute(
            select(AdminUser).where(AdminUser.c.username == body.username)
        )).first()
        return _row_to_dict(row)

    @router.put("/users/{user_id}")
    async def update_user(user_id: int, body: UpdateUserRequest, session: AsyncSession = Depends(get_session)):
        row = (await session.execute(
            select(AdminUser).where(AdminUser.c.id == user_id)
        )).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        updates: dict = {}
        if body.username is not None:
            updates["username"] = body.username
        if body.is_active is not None:
            updates["is_active"] = body.is_active
        if updates:
            await session.execute(AdminUser.update().where(AdminUser.c.id == user_id).values(**updates))
            await session.commit()
        row = (await session.execute(select(AdminUser).where(AdminUser.c.id == user_id))).first()
        return _row_to_dict(row)

    @router.post("/users/{user_id}/password", status_code=200)
    async def change_password(user_id: int, body: ChangePasswordRequest, session: AsyncSession = Depends(get_session)):
        row = (await session.execute(select(AdminUser).where(AdminUser.c.id == user_id))).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        await session.execute(
            AdminUser.update().where(AdminUser.c.id == user_id)
            .values(hashed_password=hash_password(body.new_password))
        )
        await session.commit()
        return {"detail": "Password updated"}

    @router.delete("/users/{user_id}", status_code=204)
    async def delete_user(user_id: int, session: AsyncSession = Depends(get_session)):
        row = (await session.execute(select(AdminUser).where(AdminUser.c.id == user_id))).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        await session.execute(AdminUser.delete().where(AdminUser.c.id == user_id))
        await session.commit()


# ── Sync routes ───────────────────────────────────────────────────────────────

def _add_sync_routes(router: APIRouter, engine) -> None:
    from sqlalchemy.orm import Session

    def get_session():
        with Session(engine) as session:
            yield session

    @router.get("/users")
    def list_users(session: Session = Depends(get_session)):
        result = session.execute(select(AdminUser).order_by(AdminUser.c.id))
        return [_row_to_dict(r) for r in result.fetchall()]

    @router.post("/users", status_code=201)
    def create_user(body: CreateUserRequest, session: Session = Depends(get_session)):
        exists = session.execute(select(AdminUser).where(AdminUser.c.username == body.username)).first()
        if exists:
            raise HTTPException(status_code=409, detail="Username already exists")
        session.execute(AdminUser.insert().values(
            username=body.username,
            hashed_password=hash_password(body.password),
            is_active=body.is_active,
        ))
        session.commit()
        row = session.execute(select(AdminUser).where(AdminUser.c.username == body.username)).first()
        return _row_to_dict(row)

    @router.put("/users/{user_id}")
    def update_user(user_id: int, body: UpdateUserRequest, session: Session = Depends(get_session)):
        row = session.execute(select(AdminUser).where(AdminUser.c.id == user_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        updates: dict = {}
        if body.username is not None:
            updates["username"] = body.username
        if body.is_active is not None:
            updates["is_active"] = body.is_active
        if updates:
            session.execute(AdminUser.update().where(AdminUser.c.id == user_id).values(**updates))
            session.commit()
        row = session.execute(select(AdminUser).where(AdminUser.c.id == user_id)).first()
        return _row_to_dict(row)

    @router.post("/users/{user_id}/password", status_code=200)
    def change_password(user_id: int, body: ChangePasswordRequest, session: Session = Depends(get_session)):
        row = session.execute(select(AdminUser).where(AdminUser.c.id == user_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        session.execute(
            AdminUser.update().where(AdminUser.c.id == user_id)
            .values(hashed_password=hash_password(body.new_password))
        )
        session.commit()
        return {"detail": "Password updated"}

    @router.delete("/users/{user_id}", status_code=204)
    def delete_user(user_id: int, session: Session = Depends(get_session)):
        row = session.execute(select(AdminUser).where(AdminUser.c.id == user_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        session.execute(AdminUser.delete().where(AdminUser.c.id == user_id))
        session.commit()
