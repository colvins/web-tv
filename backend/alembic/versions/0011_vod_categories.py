"""vod categories

Revision ID: 0011_vod_categories
Revises: 0010_live_m3u
Create Date: 2026-04-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_vod_categories"
down_revision: str | None = "0010_live_m3u"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vod_categories",
        sa.Column("source_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_key", sa.String(length=180), nullable=False),
        sa.Column("type_id", sa.String(length=120), nullable=False),
        sa.Column("type_name", sa.String(length=240), nullable=False),
        sa.Column("parent_type_id", sa.String(length=120), nullable=True),
        sa.Column("parent_type_name", sa.String(length=240), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_config_id"],
            ["source_configs.id"],
            name="fk_vod_categories_source_config_id_source_configs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vod_categories"),
        sa.UniqueConstraint("source_config_id", "site_key", "type_id", name="uq_vod_categories_source_site_type"),
    )
    op.create_index("ix_vod_categories_source_config_id", "vod_categories", ["source_config_id"], unique=False)
    op.create_index("ix_vod_categories_site_key", "vod_categories", ["site_key"], unique=False)
    op.create_index(
        "ix_vod_categories_source_site_sort",
        "vod_categories",
        ["source_config_id", "site_key", "sort_order"],
        unique=False,
    )
    op.create_index("ix_vod_categories_enabled_sort", "vod_categories", ["enabled", "sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vod_categories_enabled_sort", table_name="vod_categories")
    op.drop_index("ix_vod_categories_source_site_sort", table_name="vod_categories")
    op.drop_index("ix_vod_categories_site_key", table_name="vod_categories")
    op.drop_index("ix_vod_categories_source_config_id", table_name="vod_categories")
    op.drop_table("vod_categories")
