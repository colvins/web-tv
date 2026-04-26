"""spider artifacts

Revision ID: 0008_spider_artifacts
Revises: 0007_source_snapshots
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_spider_artifacts"
down_revision: str | None = "0007_source_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spider_artifacts",
        sa.Column("source_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_url", sa.Text(), nullable=False),
        sa.Column("expected_md5", sa.String(length=32), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("md5", sa.String(length=32), nullable=True),
        sa.Column("md5_matches", sa.Boolean(), nullable=True),
        sa.Column("magic_hex", sa.String(length=64), nullable=True),
        sa.Column("detected_kind", sa.String(length=40), nullable=True),
        sa.Column("probe_status", sa.String(length=24), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("probed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("probe_status IN ('pending', 'success', 'failed')", name="ck_spider_artifacts_status"),
        sa.ForeignKeyConstraint(
            ["source_config_id"],
            ["source_configs.id"],
            name="fk_spider_artifacts_source_config_id_source_configs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"],
            ["source_snapshots.id"],
            name="fk_spider_artifacts_source_snapshot_id_source_snapshots",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_spider_artifacts"),
        sa.UniqueConstraint("source_config_id", "artifact_url", "expected_md5", name="uq_spider_artifacts_source_url_md5"),
    )
    op.create_index("ix_spider_artifacts_detected_kind", "spider_artifacts", ["detected_kind"], unique=False)
    op.create_index("ix_spider_artifacts_md5", "spider_artifacts", ["md5"], unique=False)
    op.create_index("ix_spider_artifacts_probe_status", "spider_artifacts", ["probe_status"], unique=False)
    op.create_index("ix_spider_artifacts_probed_at", "spider_artifacts", ["probed_at"], unique=False)
    op.create_index("ix_spider_artifacts_sha256", "spider_artifacts", ["sha256"], unique=False)
    op.create_index("ix_spider_artifacts_source_config_id", "spider_artifacts", ["source_config_id"], unique=False)
    op.create_index("ix_spider_artifacts_source_created", "spider_artifacts", ["source_config_id", "created_at"], unique=False)
    op.create_index("ix_spider_artifacts_source_snapshot_id", "spider_artifacts", ["source_snapshot_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_spider_artifacts_source_snapshot_id", table_name="spider_artifacts")
    op.drop_index("ix_spider_artifacts_source_created", table_name="spider_artifacts")
    op.drop_index("ix_spider_artifacts_source_config_id", table_name="spider_artifacts")
    op.drop_index("ix_spider_artifacts_sha256", table_name="spider_artifacts")
    op.drop_index("ix_spider_artifacts_probed_at", table_name="spider_artifacts")
    op.drop_index("ix_spider_artifacts_probe_status", table_name="spider_artifacts")
    op.drop_index("ix_spider_artifacts_md5", table_name="spider_artifacts")
    op.drop_index("ix_spider_artifacts_detected_kind", table_name="spider_artifacts")
    op.drop_table("spider_artifacts")
