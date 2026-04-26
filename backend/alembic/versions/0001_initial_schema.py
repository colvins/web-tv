"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_configs",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_configs")),
        sa.UniqueConstraint("name", "source_type", name="uq_source_configs_name_type"),
    )
    op.create_index(op.f("ix_source_configs_source_type"), "source_configs", ["source_type"], unique=False)
    op.create_index(op.f("ix_source_configs_enabled"), "source_configs", ["enabled"], unique=False)
    op.create_index("ix_source_configs_enabled_priority", "source_configs", ["enabled", "priority"], unique=False)

    op.create_table(
        "vod_sites",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vod_sites")),
        sa.UniqueConstraint("name", name=op.f("uq_vod_sites_name")),
    )
    op.create_index(op.f("ix_vod_sites_enabled"), "vod_sites", ["enabled"], unique=False)
    op.create_index("ix_vod_sites_enabled_priority", "vod_sites", ["enabled", "priority"], unique=False)

    op.create_table(
        "live_sources",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("refresh_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_sources")),
        sa.UniqueConstraint("name", name=op.f("uq_live_sources_name")),
    )
    op.create_index(op.f("ix_live_sources_enabled"), "live_sources", ["enabled"], unique=False)

    op.create_table(
        "parse_apis",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parse_apis")),
        sa.UniqueConstraint("name", name=op.f("uq_parse_apis_name")),
    )
    op.create_index(op.f("ix_parse_apis_enabled"), "parse_apis", ["enabled"], unique=False)
    op.create_index("ix_parse_apis_enabled_priority", "parse_apis", ["enabled", "priority"], unique=False)

    op.create_table(
        "vod_cache",
        sa.Column("source_key", sa.String(length=180), nullable=False),
        sa.Column("external_id", sa.String(length=180), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("detail_url", sa.Text(), nullable=True),
        sa.Column("poster_url", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vod_cache")),
        sa.UniqueConstraint("source_key", "external_id", name="uq_vod_cache_source_external"),
    )
    op.create_index(op.f("ix_vod_cache_source_key"), "vod_cache", ["source_key"], unique=False)
    op.create_index(op.f("ix_vod_cache_title"), "vod_cache", ["title"], unique=False)
    op.create_index(op.f("ix_vod_cache_category"), "vod_cache", ["category"], unique=False)
    op.create_index(op.f("ix_vod_cache_expires_at"), "vod_cache", ["expires_at"], unique=False)
    op.create_index("ix_vod_cache_title_category", "vod_cache", ["title", "category"], unique=False)

    op.create_table(
        "play_history",
        sa.Column("content_type", sa.String(length=24), nullable=False),
        sa.Column("content_id", sa.String(length=180), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("position_seconds", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_play_history")),
    )
    op.create_index(op.f("ix_play_history_content_type"), "play_history", ["content_type"], unique=False)
    op.create_index(op.f("ix_play_history_content_id"), "play_history", ["content_id"], unique=False)
    op.create_index(op.f("ix_play_history_played_at"), "play_history", ["played_at"], unique=False)
    op.create_index("ix_play_history_type_played", "play_history", ["content_type", "played_at"], unique=False)

    op.create_table(
        "favorites",
        sa.Column("content_type", sa.String(length=24), nullable=False),
        sa.Column("content_id", sa.String(length=180), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_favorites")),
        sa.UniqueConstraint("content_type", "content_id", name="uq_favorites_type_content"),
    )
    op.create_index(op.f("ix_favorites_content_type"), "favorites", ["content_type"], unique=False)
    op.create_index("ix_favorites_type_created", "favorites", ["content_type", "created_at"], unique=False)

    op.create_table(
        "live_channels",
        sa.Column("live_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("group_name", sa.String(length=120), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("stream_url", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["live_source_id"], ["live_sources.id"], name=op.f("fk_live_channels_live_source_id_live_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_channels")),
        sa.UniqueConstraint("live_source_id", "name", "stream_url", name="uq_live_channels_source_name_stream"),
    )
    op.create_index(op.f("ix_live_channels_live_source_id"), "live_channels", ["live_source_id"], unique=False)
    op.create_index(op.f("ix_live_channels_group_name"), "live_channels", ["group_name"], unique=False)
    op.create_index(op.f("ix_live_channels_enabled"), "live_channels", ["enabled"], unique=False)
    op.create_index("ix_live_channels_group_sort", "live_channels", ["group_name", "sort_order"], unique=False)


def downgrade() -> None:
    op.drop_table("live_channels")
    op.drop_table("favorites")
    op.drop_table("play_history")
    op.drop_table("vod_cache")
    op.drop_table("parse_apis")
    op.drop_table("live_sources")
    op.drop_table("vod_sites")
    op.drop_table("source_configs")
