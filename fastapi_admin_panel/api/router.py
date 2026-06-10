"""
Builds a FastAPI router with dynamic CRUD endpoints for every discovered model.

Detects whether the passed engine is sync (Engine) or async (AsyncEngine) and
builds the appropriate endpoints automatically — no change needed in user code.

Endpoints (all require Bearer token):
  GET    /models          → list all model schemas
  GET    /{model}/        → list records (pagination, search, sort)
  POST   /{model}/        → create record
  GET    /{model}/{pk}    → get one record
  PUT    /{model}/{pk}    → update record
  DELETE /{model}/{pk}    → delete record (if allow_delete=True)
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from ..discovery.model_inspector import ModelSchema
from . import crud

# AsyncEngine is an optional import — only present when sqlalchemy[asyncio] installed
try:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    _ASYNC_AVAILABLE = True
except ImportError:
    _ASYNC_AVAILABLE = False
    AsyncEngine = None  # type: ignore[assignment,misc]


def _is_async_engine(engine) -> bool:
    return _ASYNC_AVAILABLE and isinstance(engine, AsyncEngine)


def _schema_to_dict(schema: ModelSchema) -> dict:
    d = asdict(schema)
    d.pop("model_class", None)
    return d


def _coerce_pk(raw: str, schema: ModelSchema):
    pk_field = next((f for f in schema.fields if f.primary_key), None)
    if pk_field is None:
        return raw
    try:
        if pk_field.field_type == "integer":
            return int(raw)
        if pk_field.field_type == "float":
            return float(raw)
        if pk_field.field_type == "uuid":
            import uuid
            return uuid.UUID(raw)
    except (ValueError, AttributeError):
        pass
    return raw


def _get_schema(model_name: str, schema_map: dict[str, ModelSchema]) -> ModelSchema:
    schema = schema_map.get(model_name.lower())
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    return schema


# ── Public entry point ────────────────────────────────────────────────────────

def build_router(
    schemas: list[ModelSchema],
    engine,
    *,
    require_admin: Callable,
    allow_delete: bool = True,
    default_page_size: int = 50,
) -> APIRouter:
    if _is_async_engine(engine):
        return _build_async_router(schemas, engine, require_admin, allow_delete, default_page_size)
    return _build_sync_router(schemas, engine, require_admin, allow_delete, default_page_size)


# ── Sync router (Engine / psycopg2 / etc.) ───────────────────────────────────

def _build_sync_router(
    schemas: list[ModelSchema],
    engine: Engine,
    require_admin: Callable,
    allow_delete: bool,
    default_page_size: int,
) -> APIRouter:
    router = APIRouter(dependencies=[Depends(require_admin)])
    schema_map = {s.name.lower(): s for s in schemas}

    def get_session():
        with Session(engine) as session:
            yield session

    @router.get("/models")
    def list_models():
        return [_schema_to_dict(s) for s in schemas]

    @router.get("/{model}/")
    def list_records(
        model: str,
        skip: int = Query(0, ge=0),
        limit: int = Query(default_page_size, ge=1, le=500),
        search: str | None = Query(None),
        search_field: str | None = Query(None),
        order_by: str | None = Query(None),
        order_dir: str = Query("asc", pattern="^(asc|desc)$"),
        session: Session = Depends(get_session),
    ):
        s = _get_schema(model, schema_map)
        rows, total = crud.list_records(
            session, s, skip=skip, limit=limit,
            search=search, search_field=search_field,
            order_by=order_by, order_dir=order_dir,
        )
        return {"total": total, "skip": skip, "limit": limit, "data": rows}

    @router.post("/{model}/", status_code=201)
    def create_record(model: str, data: dict[str, Any], session: Session = Depends(get_session)):
        s = _get_schema(model, schema_map)
        try:
            return crud.create_record(session, s, data)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @router.get("/{model}/{pk}")
    def get_record(model: str, pk: str, session: Session = Depends(get_session)):
        s = _get_schema(model, schema_map)
        record = crud.get_record(session, s, _coerce_pk(pk, s))
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return record

    @router.put("/{model}/{pk}")
    def update_record(model: str, pk: str, data: dict[str, Any], session: Session = Depends(get_session)):
        s = _get_schema(model, schema_map)
        record = crud.update_record(session, s, _coerce_pk(pk, s), data)
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return record

    @router.delete("/{model}/{pk}", status_code=204)
    def delete_record(model: str, pk: str, session: Session = Depends(get_session)):
        if not allow_delete:
            raise HTTPException(status_code=403, detail="Delete is disabled")
        s = _get_schema(model, schema_map)
        if not crud.delete_record(session, s, _coerce_pk(pk, s)):
            raise HTTPException(status_code=404, detail="Record not found")

    return router


# ── Async router (AsyncEngine / asyncpg / aiosqlite / etc.) ──────────────────

def _build_async_router(
    schemas: list[ModelSchema],
    engine,   # AsyncEngine
    require_admin: Callable,
    allow_delete: bool,
    default_page_size: int,
) -> APIRouter:
    from sqlalchemy.ext.asyncio import AsyncSession
    from . import crud_async as acrud

    router = APIRouter(dependencies=[Depends(require_admin)])
    schema_map = {s.name.lower(): s for s in schemas}

    async def get_session():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    @router.get("/models")
    async def list_models():
        return [_schema_to_dict(s) for s in schemas]

    @router.get("/{model}/")
    async def list_records(
        model: str,
        skip: int = Query(0, ge=0),
        limit: int = Query(default_page_size, ge=1, le=500),
        search: str | None = Query(None),
        search_field: str | None = Query(None),
        order_by: str | None = Query(None),
        order_dir: str = Query("asc", pattern="^(asc|desc)$"),
        session: AsyncSession = Depends(get_session),
    ):
        s = _get_schema(model, schema_map)
        rows, total = await acrud.list_records(
            session, s, skip=skip, limit=limit,
            search=search, search_field=search_field,
            order_by=order_by, order_dir=order_dir,
        )
        return {"total": total, "skip": skip, "limit": limit, "data": rows}

    @router.post("/{model}/", status_code=201)
    async def create_record(
        model: str, data: dict[str, Any], session: AsyncSession = Depends(get_session)
    ):
        s = _get_schema(model, schema_map)
        try:
            return await acrud.create_record(session, s, data)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @router.get("/{model}/{pk}")
    async def get_record(
        model: str, pk: str, session: AsyncSession = Depends(get_session)
    ):
        s = _get_schema(model, schema_map)
        record = await acrud.get_record(session, s, _coerce_pk(pk, s))
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return record

    @router.put("/{model}/{pk}")
    async def update_record(
        model: str, pk: str, data: dict[str, Any], session: AsyncSession = Depends(get_session)
    ):
        s = _get_schema(model, schema_map)
        record = await acrud.update_record(session, s, _coerce_pk(pk, s), data)
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return record

    @router.delete("/{model}/{pk}", status_code=204)
    async def delete_record(
        model: str, pk: str, session: AsyncSession = Depends(get_session)
    ):
        if not allow_delete:
            raise HTTPException(status_code=403, detail="Delete is disabled")
        s = _get_schema(model, schema_map)
        if not await acrud.delete_record(session, s, _coerce_pk(pk, s)):
            raise HTTPException(status_code=404, detail="Record not found")

    return router
