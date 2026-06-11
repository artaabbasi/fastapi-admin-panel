"""
main_async.py — FastAPI app using the dedicated admin module with an async engine.

Copy/adapt this as your main.py.  The admin module (admin.py) lives alongside
this file and owns all admin config, engine, and panel construction.

Run with:
    uvicorn examples.main_async:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

# Import the admin module — engine + config live there
from admin import init_admin, panel as _panel_ref


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 1. Register admin routes ─────────────────────────────────────────────
    #    This calls AdminPanel(app, engine, config=config) which mounts
    #    all CRUD / auth / system routes onto *app* immediately.
    init_admin(app)

    # ── 2. Run async DB bootstrap ────────────────────────────────────────────
    #    Creates admin_panel_users table and seeds the first admin user.
    #    Must happen inside the running event loop — hence inside lifespan.
    if _panel_ref is not None:
        await _panel_ref.bootstrap()

    # ── 3. Your own startup logic ────────────────────────────────────────────
    # e.g. await db_pool.start(), await cache.connect(), …

    yield

    # ── 4. Cleanup ───────────────────────────────────────────────────────────
    # e.g. await db_pool.close(), await cache.disconnect(), …


app = FastAPI(
    title="My API",
    lifespan=lifespan,
)


# ── Your normal routes ────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok"}
