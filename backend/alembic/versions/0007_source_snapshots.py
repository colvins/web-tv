"""source snapshots

Revision ID: 0007_source_snapshots
Revises: 0006_current_vod_site
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_source_snapshots"
down_revision: str | None = "0006_current_vod_site"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_snapshots",
        sa.Column("source_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("detected_format", sa.String(length=40), nullable=True),
        sa.Column("recovered_format", sa.String(length=40), nullable=True),
        sa.Column("root_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("root_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sites_count", sa.Integer(), nullable=False),
        sa.Column("lives_count", sa.Integer(), nullable=False),
        sa.Column("parses_count", sa.Integer(), nullable=False),
        sa.Column("has_spider", sa.Boolean(), nullable=False),
        sa.Column("spider_summary", sa.Text(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_job_id"],
            ["import_jobs.id"],
            name="fk_source_snapshots_import_job_id_import_jobs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_config_id"],
            ["source_configs.id"],
            name="fk_source_snapshots_source_config_id_source_configs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_snapshots"),
        sa.UniqueConstraint("source_config_id", "content_sha256", name="uq_source_snapshots_source_sha"),
    )
    op.create_index("ix_source_snapshots_content_sha256", "source_snapshots", ["content_sha256"], unique=False)
    op.create_index("ix_source_snapshots_detected_format", "source_snapshots", ["detected_format"], unique=False)
    op.create_index("ix_source_snapshots_has_spider", "source_snapshots", ["has_spider"], unique=False)
    op.create_index("ix_source_snapshots_import_job_id", "source_snapshots", ["import_job_id"], unique=False)
    op.create_index("ix_source_snapshots_recovered_format", "source_snapshots", ["recovered_format"], unique=False)
    op.create_index("ix_source_snapshots_source_config_id", "source_snapshots", ["source_config_id"], unique=False)
    op.create_index(
        "ix_source_snapshots_source_created",
        "source_snapshots",
        ["source_config_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_source_snapshots_source_created", table_name="source_snapshots")
    op.drop_index("ix_source_snapshots_source_config_id", table_name="source_snapshots")
    op.drop_index("ix_source_snapshots_recovered_format", table_name="source_snapshots")
    op.drop_index("ix_source_snapshots_import_job_id", table_name="source_snapshots")
    op.drop_index("ix_source_snapshots_has_spider", table_name="source_snapshots")
    op.drop_index("ix_source_snapshots_detected_format", table_name="source_snapshots")
    op.drop_index("ix_source_snapshots_content_sha256", table_name="source_snapshots")
    op.drop_table("source_snapshots")
