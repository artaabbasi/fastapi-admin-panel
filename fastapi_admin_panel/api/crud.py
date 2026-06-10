"""
Generic CRUD operations that work against any SQLAlchemy mapped model.
All functions are synchronous; wrap in run_in_executor if needed.
"""

from __future__ import annotations

import datetime
import decimal
import uuid as _uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..discovery.model_inspector import FieldSchema, ModelSchema


def _pk_column(schema: ModelSchema) -> str:
    for f in schema.fields:
        if f.primary_key:
            return f.name
    return schema.pk_field


def _coerce(val: Any, field: FieldSchema) -> Any:
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
            return datetime.datetime.fromisoformat(str(val))
        if ft == "date" and not isinstance(val, datetime.date):
            return datetime.date.fromisoformat(str(val)[:10])
        if ft == "time" and not isinstance(val, datetime.time):
            return datetime.time.fromisoformat(str(val)[:8])
    except (ValueError, AttributeError, TypeError):
        pass
    return val


def _coerce_data(data: dict, schema: ModelSchema) -> dict:
    fields = {f.name: f for f in schema.fields}
    return {k: _coerce(v, fields[k]) if k in fields else v for k, v in data.items()}


# ── List ──────────────────────────────────────────────────────────────────────

def list_records(
    session: Session,
    schema: ModelSchema,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    search_field: str | None = None,
    order_by: str | None = None,
    order_dir: str = "asc",
    filters: dict[str, Any] | None = None,
) -> tuple[list[dict], int]:
    model = schema.model_class
    q = session.query(model)

    if search:
        if search_field and hasattr(model, search_field):
            col = getattr(model, search_field)
            field_info = next((f for f in schema.fields if f.name == search_field), None)
            if field_info and field_info.field_type in ("string", "text"):
                q = q.filter(col.ilike(f"%{search}%"))
            else:
                q = q.filter(sa.cast(col, sa.String).ilike(f"%{search}%"))
        else:
            string_cols = [
                f.name for f in schema.fields
                if f.field_type in ("string", "text") and not f.primary_key
            ]
            if string_cols:
                clauses = [
                    getattr(model, col).ilike(f"%{search}%")
                    for col in string_cols
                    if hasattr(model, col)
                ]
                if clauses:
                    q = q.filter(sa.or_(*clauses))

    # exact filters
    if filters:
        for col_name, val in filters.items():
            if hasattr(model, col_name) and val is not None:
                q = q.filter(getattr(model, col_name) == val)

    total = q.count()

    # ordering
    if order_by and hasattr(model, order_by):
        col = getattr(model, order_by)
        q = q.order_by(col.desc() if order_dir == "desc" else col.asc())
    else:
        pk = _pk_column(schema)
        if hasattr(model, pk):
            q = q.order_by(getattr(model, pk).asc())

    rows = q.offset(skip).limit(limit).all()
    return [_row_to_dict(row, schema) for row in rows], total


# ── Get ───────────────────────────────────────────────────────────────────────

def get_record(session: Session, schema: ModelSchema, pk_value: Any) -> dict | None:
    model = schema.model_class
    pk = _pk_column(schema)
    row = session.query(model).filter(getattr(model, pk) == pk_value).first()
    return _row_to_dict(row, schema) if row else None


# ── Create ────────────────────────────────────────────────────────────────────

def create_record(session: Session, schema: ModelSchema, data: dict) -> dict:
    model = schema.model_class
    pk = _pk_column(schema)
    coerced = _coerce_data(data, schema)
    clean = {k: v for k, v in coerced.items() if k != pk or v is not None}
    instance = model(**clean)
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return _row_to_dict(instance, schema)


# ── Update ────────────────────────────────────────────────────────────────────

def update_record(
    session: Session, schema: ModelSchema, pk_value: Any, data: dict
) -> dict | None:
    model = schema.model_class
    pk = _pk_column(schema)
    instance = session.query(model).filter(getattr(model, pk) == pk_value).first()
    if not instance:
        return None
    coerced = _coerce_data(data, schema)
    for key, val in coerced.items():
        if key != pk and hasattr(instance, key):
            setattr(instance, key, val)
    session.commit()
    session.refresh(instance)
    return _row_to_dict(instance, schema)


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_record(session: Session, schema: ModelSchema, pk_value: Any) -> bool:
    model = schema.model_class
    pk = _pk_column(schema)
    instance = session.query(model).filter(getattr(model, pk) == pk_value).first()
    if not instance:
        return False
    session.delete(instance)
    session.commit()
    return True


# ── Serialiser ────────────────────────────────────────────────────────────────

def _row_to_dict(row, schema: ModelSchema) -> dict:
    result = {}
    for f in schema.fields:
        val = getattr(row, f.name, None)
        # coerce non-serialisable types
        if val is not None:
            import datetime, decimal, uuid as _uuid
            if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
                val = val.isoformat()
            elif isinstance(val, decimal.Decimal):
                val = float(val)
            elif isinstance(val, _uuid.UUID):
                val = str(val)
        result[f.name] = val
    return result
