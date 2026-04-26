"""live m3u phase 1

Revision ID: 0010_live_m3u
Revises: 0009_spider_entry_analysis
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_live_m3u"
down_revision: str | None = "0009_spider_entry_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "live_channel_groups",
        sa.Column("source_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("channel_count", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_config_id"],
            ["source_configs.id"],
            name="fk_live_channel_groups_source_config_id_source_configs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_live_channel_groups"),
        sa.UniqueConstraint("source_config_id", "name", name="uq_live_channel_groups_source_name"),
    )
    op.create_index("ix_live_channel_groups_source_config_id", "live_channel_groups", ["source_config_id"], unique=False)
    op.create_index(
        "ix_live_channel_groups_source_sort",
        "live_channel_groups",
        ["source_config_id", "sort_order"],
        unique=False,
    )

    op.add_column("live_channels", sa.Column("source_config_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("live_channels", sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("live_channels", sa.Column("tvg_id", sa.String(length=180), nullable=True))
    op.add_column("live_channels", sa.Column("tvg_name", sa.String(length=240), nullable=True))
    op.add_column("live_channels", sa.Column("tvg_logo", sa.Text(), nullable=True))
    op.add_column("live_channels", sa.Column("group_title", sa.String(length=160), nullable=True))
    op.add_column("live_channels", sa.Column("raw_extinf", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.alter_column("live_channels", "live_source_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("live_channels", "metadata", existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    op.execute("UPDATE live_channels SET raw_extinf = '{}'::jsonb WHERE raw_extinf IS NULL")
    op.alter_column("live_channels", "raw_extinf", nullable=False)
    op.create_foreign_key(
        "fk_live_channels_source_config_id_source_configs",
        "live_channels",
        "source_configs",
        ["source_config_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_live_channels_group_id_live_channel_groups",
        "live_channels",
        "live_channel_groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_live_channels_source_config_id", "live_channels", ["source_config_id"], unique=False)
    op.create_index("ix_live_channels_group_id", "live_channels", ["group_id"], unique=False)
    op.create_index("ix_live_channels_tvg_id", "live_channels", ["tvg_id"], unique=False)
    op.create_index("ix_live_channels_tvg_name", "live_channels", ["tvg_name"], unique=False)
    op.create_index("ix_live_channels_group_title", "live_channels", ["group_title"], unique=False)
    op.create_index(
        "ix_live_channels_source_group_sort",
        "live_channels",
        ["source_config_id", "group_id", "sort_order"],
        unique=False,
    )
    op.create_index("ix_live_channels_enabled_sort", "live_channels", ["enabled", "sort_order"], unique=False)
    op.create_unique_constraint("uq_live_channels_source_stream", "live_channels", ["source_config_id", "stream_url"])


def downgrade() -> None:
    op.drop_constraint("uq_live_channels_source_stream", "live_channels", type_="unique")
    op.drop_index("ix_live_channels_enabled_sort", table_name="live_channels")
    op.drop_index("ix_live_channels_source_group_sort", table_name="live_channels")
    op.drop_index("ix_live_channels_group_title", table_name="live_channels")
    op.drop_index("ix_live_channels_tvg_name", table_name="live_channels")
    op.drop_index("ix_live_channels_tvg_id", table_name="live_channels")
    op.drop_index("ix_live_channels_group_id", table_name="live_channels")
    op.drop_index("ix_live_channels_source_config_id", table_name="live_channels")
    op.drop_constraint("fk_live_channels_group_id_live_channel_groups", "live_channels", type_="foreignkey")
    op.drop_constraint("fk_live_channels_source_config_id_source_configs", "live_channels", type_="foreignkey")
    op.alter_column("live_channels", "metadata", existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=False)
    op.alter_column("live_channels", "live_source_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_column("live_channels", "raw_extinf")
    op.drop_column("live_channels", "group_title")
    op.drop_column("live_channels", "tvg_logo")
    op.drop_column("live_channels", "tvg_name")
    op.drop_column("live_channels", "tvg_id")
    op.drop_column("live_channels", "group_id")
    op.drop_column("live_channels", "source_config_id")
    op.drop_index("ix_live_channel_groups_source_sort", table_name="live_channel_groups")
    op.drop_index("ix_live_channel_groups_source_config_id", table_name="live_channel_groups")
    op.drop_table("live_channel_groups")
