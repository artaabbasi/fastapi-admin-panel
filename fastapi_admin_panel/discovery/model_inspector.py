"""
Inspects SQLAlchemy models discovered from the user's Base class.

Returns a list of ModelSchema objects describing each table: columns, types,
primary keys, nullable flags, foreign keys, and enum choices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Type

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase


# ── Field type mapping ─────────────────────────────────────────────────────────

_SA_TYPE_MAP: dict[type, str] = {
    sa.String: "string",
    sa.Text: "text",
    sa.Integer: "integer",
    sa.BigInteger: "integer",
    sa.SmallInteger: "integer",
    sa.Float: "float",
    sa.Numeric: "float",
    sa.Boolean: "boolean",
    sa.Date: "date",
    sa.DateTime: "datetime",
    sa.Time: "time",
    sa.JSON: "json",
    sa.LargeBinary: "binary",
}


def _map_sa_type(col_type: sa.types.TypeEngine) -> str:
    for sa_type, name in _SA_TYPE_MAP.items():
        if isinstance(col_type, sa_type):
            return name
    # UUID / Uuid
    type_name = type(col_type).__name__.lower()
    if "uuid" in type_name:
        return "uuid"
    if "enum" in type_name:
        return "enum"
    return "string"


def _enum_choices(col_type: sa.types.TypeEngine) -> list[str]:
    if isinstance(col_type, sa.Enum) and col_type.enums:
        return list(col_type.enums)
    return []


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class FieldSchema:
    name: str
    field_type: str          # "string" | "integer" | "boolean" | "datetime" | …
    primary_key: bool = False
    nullable: bool = True
    default: Any = None
    foreign_key: Optional[str] = None   # "other_table.id"
    choices: list[str] = field(default_factory=list)
    max_length: Optional[int] = None


@dataclass
class ModelSchema:
    name: str                # "User"
    table_name: str          # "users"
    pk_field: str            # name of the PK column (usually "id")
    fields: list[FieldSchema] = field(default_factory=list)
    # The actual mapper class – kept for CRUD operations, NOT serialised
    model_class: Optional[Any] = field(default=None, repr=False)


# ── Inspector ─────────────────────────────────────────────────────────────────

def _get_mapped_classes(base) -> list[type]:
    """
    Works with both old-style (DeclarativeMeta) and new-style (DeclarativeBase)
    SQLAlchemy declarative bases, and also with plain MetaData objects.
    """
    classes: list[type] = []

    # New-style: DeclarativeBase subclass
    if isinstance(base, type) and issubclass(base, DeclarativeBase):
        registry = base.registry
        for mapper in registry.mappers:
            classes.append(mapper.class_)
        return classes

    # Old-style: DeclarativeMeta (classic Base = declarative_base())
    if hasattr(base, "_decl_class_registry"):
        for cls in base._decl_class_registry.values():
            if isinstance(cls, type):
                classes.append(cls)
        return classes

    # SQLAlchemy 1.4+ mapped_subclasses via __subclasses__
    if hasattr(base, "__subclasses__"):
        for cls in base.__subclasses__():
            if hasattr(cls, "__tablename__"):
                classes.append(cls)
        return classes

    return classes


def inspect_models(base) -> list[ModelSchema]:
    """
    Given a SQLAlchemy declarative Base (or any object with .metadata),
    return a ModelSchema for every mapped table.
    """
    mapped_classes = _get_mapped_classes(base)

    schemas: list[ModelSchema] = []
    for cls in mapped_classes:
        try:
            mapper = sa_inspect(cls)
        except Exception:
            continue

        table: sa.Table = mapper.local_table
        pk_cols = [c.name for c in table.primary_key.columns]
        pk_field = pk_cols[0] if pk_cols else "id"

        fields: list[FieldSchema] = []
        for col in table.columns:
            fk: Optional[str] = None
            if col.foreign_keys:
                fk_obj = next(iter(col.foreign_keys))
                fk = str(fk_obj.target_fullname)   # "other_table.col"

            max_len: Optional[int] = None
            if isinstance(col.type, sa.String) and col.type.length:
                max_len = col.type.length

            default_val = None
            if col.default and hasattr(col.default, "arg"):
                arg = col.default.arg
                if not callable(arg):
                    default_val = arg

            fields.append(FieldSchema(
                name=col.name,
                field_type=_map_sa_type(col.type),
                primary_key=col.primary_key,
                nullable=col.nullable if col.nullable is not None else True,
                default=default_val,
                foreign_key=fk,
                choices=_enum_choices(col.type),
                max_length=max_len,
            ))

        schemas.append(ModelSchema(
            name=cls.__name__,
            table_name=table.name,
            pk_field=pk_field,
            fields=fields,
            model_class=cls,
        ))

    return sorted(schemas, key=lambda s: s.name)
