"""spider entry analysis

Revision ID: 0009_spider_entry_analysis
Revises: 0008_spider_artifacts
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_spider_entry_analysis"
down_revision: str | None = "0008_spider_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spider_artifact_analyses",
        sa.Column("spider_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_status", sa.String(length=24), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_entries", sa.Integer(), nullable=True),
        sa.Column("total_compressed_size", sa.BigInteger(), nullable=True),
        sa.Column("total_uncompressed_size", sa.BigInteger(), nullable=True),
        sa.Column("top_level_dirs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extension_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("matching_api_entries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sample_entries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("has_class", sa.Boolean(), nullable=False),
        sa.Column("has_dex", sa.Boolean(), nullable=False),
        sa.Column("has_js", sa.Boolean(), nullable=False),
        sa.Column("has_json", sa.Boolean(), nullable=False),
        sa.Column("has_assets", sa.Boolean(), nullable=False),
        sa.Column("has_catvod_package", sa.Boolean(), nullable=False),
        sa.Column("suspicious_large_entries", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("analysis_status IN ('success', 'failed')", name="ck_spider_artifact_analyses_status"),
        sa.ForeignKeyConstraint(
            ["source_config_id"],
            ["source_configs.id"],
            name="fk_spider_artifact_analyses_source_config_id_source_configs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"],
            ["source_snapshots.id"],
            name="fk_spider_artifact_analyses_source_snapshot_id_source_snapshots",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["spider_artifact_id"],
            ["spider_artifacts.id"],
            name="fk_spider_artifact_analyses_spider_artifact_id_spider_artifacts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_spider_artifact_analyses"),
    )
    op.create_index(
        "ix_spider_artifact_analyses_analysis_status",
        "spider_artifact_analyses",
        ["analysis_status"],
        unique=False,
    )
    op.create_index(
        "ix_spider_artifact_analyses_artifact_created",
        "spider_artifact_analyses",
        ["spider_artifact_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_spider_artifact_analyses_source_config_id",
        "spider_artifact_analyses",
        ["source_config_id"],
        unique=False,
    )
    op.create_index(
        "ix_spider_artifact_analyses_source_created",
        "spider_artifact_analyses",
        ["source_config_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_spider_artifact_analyses_source_snapshot_id",
        "spider_artifact_analyses",
        ["source_snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_spider_artifact_analyses_spider_artifact_id",
        "spider_artifact_analyses",
        ["spider_artifact_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_spider_artifact_analyses_spider_artifact_id", table_name="spider_artifact_analyses")
    op.drop_index("ix_spider_artifact_analyses_source_snapshot_id", table_name="spider_artifact_analyses")
    op.drop_index("ix_spider_artifact_analyses_source_created", table_name="spider_artifact_analyses")
    op.drop_index("ix_spider_artifact_analyses_source_config_id", table_name="spider_artifact_analyses")
    op.drop_index("ix_spider_artifact_analyses_artifact_created", table_name="spider_artifact_analyses")
    op.drop_index("ix_spider_artifact_analyses_analysis_status", table_name="spider_artifact_analyses")
    op.drop_table("spider_artifact_analyses")
