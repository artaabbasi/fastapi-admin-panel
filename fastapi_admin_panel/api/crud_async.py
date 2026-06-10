"""
Async CRUD — used when the user passes an AsyncEngine (asyncpg, etc.).
Uses SQLAlchemy 2.0 select() style throughout.
"""

from __future__ import annotations

import datetime
import decimal
import uuid as _uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..discovery.model_inspector import FieldSchema, ModelSchema


def _pk_column(schema: ModelSchema) -> str:
    for f in schema.fields:
        if f.primary_key:
            return f.name
    return schema.pk_field


def _field_map(schema: ModelSchema) -> dict[str, FieldSchema]:
    return {f.name: f for f in schema.fields}


# ── Type coercion (string → Python type) ─────────────────────────────────────

def _coerce(val: Any, field: FieldSchema) -> Any:
    """
    The frontend sends everything as JSON (strings for dates/UUIDs, numbers
    for int/float).  Coerce them to the correct Python type so SQLAlchemy /
    asyncpg doesn't reject the value.
    """
    if val is None or val == "":
        return None

    ft = field.field_type
    try:
        if ft == "integer" and not isinstance(val, int):
            return int(val)
        if ft == "float" and not isinstance(val, float):
            return float(val)
        if ft == "boolean" and not isinstance(val, bool):
            return str(val).lower() in ("true", "1", "yes")
        if ft == "uuid" and not isinstance(val, _uuid.UUID):
            return _uuid.UUID(str(val))
        if ft == "datetime" and not isinstance(val, datetime.datetime):
            # "2024-01-15T10:30" or "2024-01-15T10:30:00"
            return datetime.datetime.fromisoformat(str(val))
        if ft == "date" and not isinstance(val, datetime.date):
            return datetime.date.fromisoformat(str(val)[:10])
        if ft == "time" and not isinstance(val, datetime.time):
            return datetime.time.fromisoformat(str(val)[:8])
    except (ValueError, AttributeError, TypeError):
        pass  # let the DB driver report the type error
    return val


def _coerce_data(data: dict, schema: ModelSchema) -> dict:
    fields = _field_map(schema)
    return {
        k: _coerce(v, fields[k]) if k in fields else v
        for k, v in data.items()
    }


# ── Serialiser ────────────────────────────────────────────────────────────────

def _row_to_dict(row, schema: ModelSchema) -> dict:
    result = {}
    for f in schema.fields:
        val = getattr(row, f.name, None)
        if val is not None:
            if isinstance(val, datetime.datetime):
                val = val.isoformat()
            elif isinstance(val, datetime.date):
                val = val.isoformat()
            elif isinstance(val, datetime.time):
                val = val.isoformat()
            elif isinstance(val, decimal.Decimal):
                val = float(val)
            elif isinstance(val, _uuid.UUID):
                val = str(val)
        result[f.name] = val
    return result


# ── List ──────────────────────────────────────────────────────────────────────

async def list_records(
    session: AsyncSession,
    schema: ModelSchema,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    search_field: str | None = None,
    order_by: str | None = None,
    order_dir: str = "asc",
) -> tuple[list[dict], int]:
    import sqlalchemy as sa

    model = schema.model_class
    stmt = select(model)

    if search:
        if search_field and hasattr(model, search_field):
            col = getattr(model, search_field)
            field_info = next((f for f in schema.fields if f.name == search_field), None)
            if field_info and field_info.field_type in ("string", "text"):
                stmt = stmt.where(col.ilike(f"%{search}%"))
            else:
                stmt = stmt.where(sa.cast(col, sa.String).ilike(f"%{search}%"))
        else:
            string_cols = [
                f.name for f in schema.fields
                if f.field_type in ("string", "text") and not f.primary_key
            ]
            clauses = [
                getattr(model, col).ilike(f"%{search}%")
                for col in string_cols
                if hasattr(model, col)
            ]
            if clauses:
                stmt = stmt.where(or_(*clauses))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await session.execute(count_stmt)).scalar_one()

    if order_by and hasattr(model, order_by):
        col = getattr(model, order_by)
        stmt = stmt.order_by(col.desc() if order_dir == "desc" else col.asc())
    else:
        pk = _pk_column(schema)
        if hasattr(model, pk):
            stmt = stmt.order_by(getattr(model, pk).asc())

    rows = (await session.execute(stmt.offset(skip).limit(limit))).scalars().all()
    return [_row_to_dict(r, schema) for r in rows], total


# ── Get ───────────────────────────────────────────────────────────────────────

async def get_record(
    session: AsyncSession, schema: ModelSchema, pk_value: Any
) -> dict | None:
    model = schema.model_class
    pk = _pk_column(schema)
    stmt = select(model).where(getattr(model, pk) == pk_value)
    row = (await session.execute(stmt)).scalars().first()
    return _row_to_dict(row, schema) if row else None


# ── Create ────────────────────────────────────────────────────────────────────

async def create_record(
    session: AsyncSession, schema: ModelSchema, data: dict
) -> dict:
    model = schema.model_class
    pk = _pk_column(schema)
    coerced = _coerce_data(data, schema)
    clean = {k: v for k, v in coerced.items() if k != pk or v is not None}
    instance = model(**clean)
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return _row_to_dict(instance, schema)


# ── Update ────────────────────────────────────────────────────────────────────

async def update_record(
    session: AsyncSession, schema: ModelSchema, pk_value: Any, data: dict
) -> dict | None:
    model = schema.model_class
    pk = _pk_column(schema)
    stmt = select(model).where(getattr(model, pk) == pk_value)
    instance = (await session.execute(stmt)).scalars().first()
    if not instance:
        return None
    coerced = _coerce_data(data, schema)
    for key, val in coerced.items():
        if key != pk and hasattr(instance, key):
            setattr(instance, key, val)
    await session.commit()
    await session.refresh(instance)
    return _row_to_dict(instance, schema)


# ── Delete ────────────────────────────────────────────────────────────────────

async def delete_record(
    session: AsyncSession, schema: ModelSchema, pk_value: Any
) -> bool:
    model = schema.model_class
    pk = _pk_column(schema)
    stmt = select(model).where(getattr(model, pk) == pk_value)
    instance = (await session.execute(stmt)).scalars().first()
    if not instance:
        return False
    await session.delete(instance)
    await session.commit()
    return True
