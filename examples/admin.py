"""
admin.py — Dedicated admin-panel module.

Put this file alongside your main.py.  It owns all admin-related setup
(engine, config, panel instance) so main.py stays clean.

Usage
-----
Sync engine (PostgreSQL/MySQL/SQLite via psycopg2, pymysql, …):

    # main.py
    from fastapi import FastAPI
    from admin import init_admin

    app = FastAPI()
    init_admin(app)         # registers routes + creates table immediately

Async engine (asyncpg, aiosqlite, …):

    # main.py
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from admin import panel, init_admin

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_admin(app)          # register routes first
        await panel.bootstrap()  # then run async DB setup
        yield

    app = FastAPI(lifespan=lifespan)
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
# from sqlalchemy.ext.asyncio import create_async_engine  # ← use for async

from fastapi_admin_panel import AdminPanel, AdminConfig
from fastapi_admin_panel import admin_metadata  # noqa: F401 — only needed for Way 3 (Alembic)

# ── Import your models so SQLAlchemy registers them ───────────────────────────
# from myapp.database import Base
# from myapp import models  # noqa: F401

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    os.environ.get("DATABASE_URL", "sqlite:///./dev.db"),
    # For async replace with:
    # engine = create_async_engine(os.environ["DATABASE_URL"])
)

# ── Config ────────────────────────────────────────────────────────────────────
config = AdminConfig(
    # Required — generate a stable key with: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key=os.environ.get("ADMIN_SECRET_KEY", "CHANGE-ME"),

    # UI
    title="My Project Admin",
    prefix="/admin",

    # Pagination
    page_size=50,

    # Permissions
    allow_delete=True,
    models_exclude=["AlembicVersion"],   # hide internal Alembic table

    # Auth
    token_expire_hours=8,
    initial_admin_username="admin",
    initial_admin_password=os.environ.get("ADMIN_PASSWORD", "changeme"),

    # Discovery — directory that contains alembic.ini
    project_root=Path(__file__).parent,
)

# ── Panel singleton ───────────────────────────────────────────────────────────
# Populated by init_admin(); import this from lifespan for async bootstrap.
panel: AdminPanel | None = None


def init_admin(app) -> AdminPanel:
    """
    Register all admin routes on *app* and (for sync engines) run the DB
    bootstrap immediately.  Call once, at startup.

    For async engines call ``await panel.bootstrap()`` right after this,
    inside your lifespan function.
    """
    global panel
    panel = AdminPanel(
        app,
        engine,
        config=config,
        # base=Base,   # ← uncomment if you are not using Alembic auto-discovery
    )
    return panel
