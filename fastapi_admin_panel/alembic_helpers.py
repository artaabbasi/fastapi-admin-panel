"""
Helpers for including admin_panel_users in your Alembic migrations.

Usage in your alembic/env.py
-----------------------------

    from myapp.models import Base
    from fastapi_admin_panel.alembic_helpers import include_admin_metadata

    # Combine your app's metadata with admin panel metadata
    target_metadata = include_admin_metadata(Base.metadata)

    # Then use target_metadata as usual in run_migrations_offline()
    # and run_migrations_online().

That's all — Alembic will now generate and run migrations for
admin_panel_users alongside your own models.
"""

from sqlalchemy import MetaData

from .auth.models import admin_metadata


def include_admin_metadata(*metadatas: MetaData) -> list[MetaData]:
    """
    Returns a list containing all provided MetaData objects plus the
    admin panel's own MetaData.  Pass the result as target_metadata in env.py.

    Example
    -------
        target_metadata = include_admin_metadata(Base.metadata)
        # or with multiple bases:
        target_metadata = include_admin_metadata(Base.metadata, other_base.metadata)
    """
    return [*metadatas, admin_metadata]
