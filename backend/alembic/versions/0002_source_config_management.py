"""source config management fields

Revision ID: 0002_source_config_management
Revises: 0001_initial_schema
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_source_config_management"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("source_configs", sa.Column("last_import_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source_configs", sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source_configs", sa.Column("last_error", sa.Text(), nullable=True))
    op.execute("UPDATE source_configs SET url = '' WHERE url IS NULL")
    op.alter_column("source_configs", "url", existing_type=sa.Text(), nullable=False)
    op.drop_index("ix_source_configs_enabled_priority", table_name="source_configs")
    op.drop_index("ix_source_configs_source_type", table_name="source_configs")
    op.drop_constraint("uq_source_configs_name_type", "source_configs", type_="unique")
    op.drop_column("source_configs", "last_checked_at")
    op.drop_column("source_configs", "priority")
    op.drop_column("source_configs", "config")
    op.create_unique_constraint("uq_source_configs_name", "source_configs", ["name"])
    op.create_check_constraint(
        "ck_source_configs_source_type",
        "source_configs",
        "source_type IN ('json', 'm3u', 'txt', 'm3u8')",
    )
    op.create_index("ix_source_configs_source_type", "source_configs", ["source_type"], unique=False)
    op.create_index("ix_source_configs_enabled_type", "source_configs", ["enabled", "source_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_source_configs_enabled_type", table_name="source_configs")
    op.drop_index("ix_source_configs_source_type", table_name="source_configs")
    op.drop_constraint("ck_source_configs_source_type", "source_configs", type_="check")
    op.drop_constraint("uq_source_configs_name", "source_configs", type_="unique")
    op.add_column("source_configs", sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.add_column("source_configs", sa.Column("priority", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("source_configs", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_source_configs_name_type", "source_configs", ["name", "source_type"])
    op.create_index("ix_source_configs_source_type", "source_configs", ["source_type"], unique=False)
    op.create_index("ix_source_configs_enabled_priority", "source_configs", ["enabled", "priority"], unique=False)
    op.alter_column("source_configs", "url", existing_type=sa.Text(), nullable=True)
    op.drop_column("source_configs", "last_error")
    op.drop_column("source_configs", "last_success_at")
    op.drop_column("source_configs", "last_import_at")
