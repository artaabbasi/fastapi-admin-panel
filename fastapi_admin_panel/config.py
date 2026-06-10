from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AdminConfig:
    """
    Full configuration for AdminPanel.  Pass an instance to AdminPanel().

    Minimal example
    ---------------
    config = AdminConfig(secret_key="change-me-in-production")

    Full example
    ------------
    config = AdminConfig(
        secret_key=os.environ["ADMIN_SECRET_KEY"],
        title="My Project Admin",
        prefix="/admin",
        page_size=50,
        token_expire_hours=8,
        allow_delete=True,
        models_exclude=["SensitiveAuditLog"],
        initial_admin_username="admin",
        initial_admin_password="changeme123",
        project_root=Path(__file__).parent,
    )
    """

    # ── Required ──────────────────────────────────────────────────────────────
    secret_key: str = "CHANGE-ME-IN-PRODUCTION-use-secrets.token_hex(32)"

    # ── UI ────────────────────────────────────────────────────────────────────
    title: str = "Admin Panel"
    prefix: str = "/admin"
    page_size: int = 50

    # ── Auth ──────────────────────────────────────────────────────────────────
    token_expire_hours: int = 8
    # Created automatically on first startup if no admin users exist
    initial_admin_username: str = "admin"
    initial_admin_password: str = "admin"

    # ── Behaviour ─────────────────────────────────────────────────────────────
    allow_delete: bool = True
    # Model class names to hide from the panel (e.g. internal audit tables)
    models_exclude: list[str] = field(default_factory=list)

    # ── Discovery ─────────────────────────────────────────────────────────────
    # Root dir that contains alembic.ini — defaults to cwd at runtime
    project_root: Optional[Path] = None
