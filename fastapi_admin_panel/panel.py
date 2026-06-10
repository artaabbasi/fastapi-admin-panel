"""
AdminPanel — the single public class users add to their FastAPI app.

Minimal usage
-------------
    from fastapi_admin_panel import AdminPanel, AdminConfig

    config = AdminConfig(secret_key="your-secret-key")
    panel = AdminPanel(app, engine, config=config)

With lifespan manager (recommended for async engines)
------------------------------------------------------
    @asynccontextmanager
    async def manager(app):
        await panel.bootstrap()   # ← add this line
        yield

    app = FastAPI(lifespan=manager)
    panel = AdminPanel(app, engine, config=config)

    NOTE: AdminPanel must be created AFTER the FastAPI instance.
          Call panel.bootstrap() at the START of your lifespan.

Discovery order
---------------
  1. base= argument (if provided)
  2. config.project_root / alembic.ini / env.py
  3. cwd / alembic.ini / env.py
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from .api.router import build_router
from .api.system_router import build_system_router
from .auth.deps import make_require_admin
from .auth.models import AdminUser, admin_metadata
from .auth.router import build_auth_router
from .auth.utils import hash_password
from .config import AdminConfig
from .discovery.alembic_parser import find_base_from_alembic
from .discovery.model_inspector import ModelSchema, inspect_models

try:
    from sqlalchemy.ext.asyncio import AsyncEngine as _AsyncEngine
    _ASYNC_AVAILABLE = True
except ImportError:
    _ASYNC_AVAILABLE = False
    _AsyncEngine = None  # type: ignore[assignment,misc]

_STATIC_DIR = Path(__file__).parent / "static"


class AdminPanel:
    def __init__(
        self,
        app: FastAPI,
        engine,   # Engine or AsyncEngine — detected automatically
        *,
        config: AdminConfig | None = None,
        base=None,
    ):
        self.config = config or AdminConfig()
        self.engine = engine
        self._is_async = _ASYNC_AVAILABLE and isinstance(engine, _AsyncEngine)
        prefix = self.config.prefix.rstrip("/")

        # ── Discover models ───────────────────────────────────────────────────
        resolved_base = base
        if resolved_base is None:
            root = self.config.project_root or Path(sys.argv[0]).parent
            resolved_base = find_base_from_alembic(root)

        if resolved_base is None:
            raise RuntimeError(
                "AdminPanel could not discover your SQLAlchemy models.\n"
                "Either pass base=YourBase explicitly, or make sure alembic.ini "
                "and alembic/env.py exist in your project root.\n"
                "You can also set config.project_root to the directory "
                "containing alembic.ini."
            )

        all_schemas = inspect_models(resolved_base)
        self.schemas: list[ModelSchema] = [
            s for s in all_schemas
            if s.name not in self.config.models_exclude
        ]

        if not self.schemas:
            raise RuntimeError(
                "AdminPanel found the Base class but discovered 0 mapped models.\n"
                "Make sure your model modules are imported before AdminPanel is "
                "instantiated so SQLAlchemy can register them."
            )

        # ── Bootstrap ─────────────────────────────────────────────────────────
        # For sync engines: run bootstrap immediately (safe at module load time).
        # For async engines (asyncpg etc.): bootstrap() must be called inside
        # the running event loop — either from your lifespan or on_startup.
        if not self._is_async:
            self._sync_engine = engine
            self._bootstrap_sync()
        else:
            # Wrap whatever lifespan is already on the app so bootstrap
            # always runs first, even when lifespan=manager is set.
            self._wrap_lifespan(app)

        # ── Build auth dependency ─────────────────────────────────────────────
        require_admin = make_require_admin(self.config.secret_key)

        # ── Mount API routers ─────────────────────────────────────────────────
        auth_router = build_auth_router(
            engine,
            secret_key=self.config.secret_key,
            expire_hours=self.config.token_expire_hours,
        )
        app.include_router(auth_router, prefix=f"{prefix}/api")

        crud_router = build_router(
            self.schemas,
            engine,
            require_admin=require_admin,
            allow_delete=self.config.allow_delete,
            default_page_size=self.config.page_size,
        )
        app.include_router(crud_router, prefix=f"{prefix}/api")

        system_router = build_system_router(engine, require_admin)
        app.include_router(system_router, prefix=f"{prefix}/api")

        # ── Config endpoint (read by React frontend) ──────────────────────────
        from fastapi import APIRouter
        meta_router = APIRouter()
        cfg = self.config

        @meta_router.get(f"{prefix}/api/config")
        def admin_config():
            return {
                "title": cfg.title,
                "prefix": prefix,
                "allow_delete": cfg.allow_delete,
                "page_size": cfg.page_size,
            }

        app.include_router(meta_router)

        # ── Serve React frontend ──────────────────────────────────────────────
        if _STATIC_DIR.exists():
            app.mount(
                prefix,
                StaticFiles(directory=_STATIC_DIR, html=True),
                name="admin_static",
            )
        else:
            from fastapi import Request
            from fastapi.responses import HTMLResponse

            @app.get(f"{prefix}/{{path:path}}", include_in_schema=False)
            async def admin_placeholder(request: Request, path: str = ""):
                return HTMLResponse(_dev_placeholder(prefix, self.config.title))

    # ── Public bootstrap (call from your lifespan if needed) ─────────────────

    async def bootstrap(self) -> None:
        """
        Manually run the async bootstrap.  Call this at the start of your
        lifespan if AdminPanel could not wrap it automatically.

            @asynccontextmanager
            async def manager(app):
                await panel.bootstrap()
                yield
        """
        await self._bootstrap_async()

    # ── Lifespan wrapping ─────────────────────────────────────────────────────

    def _wrap_lifespan(self, app: FastAPI) -> None:
        """
        Tries to inject the async bootstrap into the app's startup sequence.

        Strategy (tries each in order):
          1. Wrap lifespan_handler if it exists (Starlette ≥ 0.27 / FastAPI ≥ 0.93)
          2. Append to on_startup list (works when no lifespan= is set)

        If the app uses lifespan=manager AND lifespan_handler is unavailable,
        the auto-inject cannot work.  In that case call await panel.bootstrap()
        manually at the top of your lifespan function — see panel.bootstrap() docs.
        """
        panel_self = self

        # Strategy 1 — lifespan_handler attribute (Starlette ≥ 0.27)
        existing = getattr(app.router, "lifespan_handler", None)
        if existing is not None:
            @asynccontextmanager
            async def wrapped_lifespan(app_instance: FastAPI):
                await panel_self._bootstrap_async()
                async with existing(app_instance):
                    yield

            try:
                app.router.lifespan_handler = wrapped_lifespan
                return
            except AttributeError:
                pass  # fall through to strategy 2

        # Strategy 2 — on_startup list (no lifespan= set, or older Starlette)
        async def _startup() -> None:
            await panel_self._bootstrap_async()

        app.router.on_startup.append(_startup)

    # ── Internal bootstrap implementations ───────────────────────────────────

    def _bootstrap_sync(self) -> None:
        """Sync bootstrap for plain Engine (psycopg2, pg8000, etc.)."""
        admin_metadata.create_all(self._sync_engine, checkfirst=True)

        with Session(self._sync_engine) as session:
            count = session.execute(
                text("SELECT COUNT(*) FROM admin_panel_users")
            ).scalar()

            if count == 0:
                session.execute(
                    AdminUser.insert().values(
                        username=self.config.initial_admin_username,
                        hashed_password=hash_password(self.config.initial_admin_password),
                        is_active=True,
                    )
                )
                session.commit()

    async def _bootstrap_async(self) -> None:
        """
        Async bootstrap for AsyncEngine (asyncpg, aiosqlite, etc.).
        Uses conn.run_sync() for DDL — safe inside the running event loop.
        """
        from sqlalchemy import func, select
        from sqlalchemy.ext.asyncio import AsyncSession

        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: admin_metadata.create_all(c, checkfirst=True))

        async with AsyncSession(self.engine) as session:
            count = (
                await session.execute(
                    select(func.count()).select_from(AdminUser)
                )
            ).scalar_one()

            if count == 0:
                await session.execute(
                    AdminUser.insert().values(
                        username=self.config.initial_admin_username,
                        hashed_password=hash_password(self.config.initial_admin_password),
                        is_active=True,
                    )
                )
                await session.commit()

    @property
    def model_names(self) -> list[str]:
        return [s.name for s in self.schemas]


# ── Dev-mode placeholder ──────────────────────────────────────────────────────

def _dev_placeholder(prefix: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0;
           display: flex; flex-direction: column; align-items: center;
           justify-content: center; min-height: 100vh; margin: 0; gap: 0.5rem; }}
    h1 {{ font-size: 1.8rem; margin: 0; }}
    p  {{ color: #94a3b8; margin: 0; }}
    code {{ background: #1e293b; padding: 0.2em 0.5em; border-radius: 4px; font-size: 0.85em; }}
    a  {{ color: #38bdf8; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>Frontend not built yet.</p>
  <p>Run <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code></p>
  <p>or <code>python scripts/build.py</code></p>
  <p>API is live at <a href="{prefix}/api/config">{prefix}/api/config</a></p>
</body>
</html>"""
