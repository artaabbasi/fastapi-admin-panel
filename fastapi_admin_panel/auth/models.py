"""
Admin user model stored in its own metadata (separate from the user's app models).
The table is created automatically on startup — no migration needed.
"""

import datetime

import sqlalchemy as sa

# Separate metadata so we never pollute the user's models
admin_metadata = sa.MetaData()

AdminUser = sa.Table(
    "admin_panel_users",
    admin_metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("username", sa.String(64), unique=True, nullable=False, index=True),
    sa.Column("hashed_password", sa.String(256), nullable=False),
    sa.Column("is_active", sa.Boolean, default=True, nullable=False),
    sa.Column(
        "created_at",
        sa.DateTime,
        default=datetime.datetime.utcnow,
        nullable=False,
    ),
)
