"""import jobs

Revision ID: 0003_import_jobs
Revises: 0002_source_config_management
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_import_jobs"
down_revision: str | None = "0002_source_config_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("source_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_preview", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'running', 'success', 'failed')", name="ck_import_jobs_status"),
        sa.ForeignKeyConstraint(["source_config_id"], ["source_configs.id"], name="fk_import_jobs_source_config_id_source_configs", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_import_jobs"),
    )
    op.create_index("ix_import_jobs_source_config_id", "import_jobs", ["source_config_id"], unique=False)
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"], unique=False)
    op.create_index("ix_import_jobs_content_sha256", "import_jobs", ["content_sha256"], unique=False)
    op.create_index("ix_import_jobs_started_at", "import_jobs", ["started_at"], unique=False)
    op.create_index("ix_import_jobs_finished_at", "import_jobs", ["finished_at"], unique=False)
    op.create_index("ix_import_jobs_source_status", "import_jobs", ["source_config_id", "status"], unique=False)
    op.create_index("ix_import_jobs_created_at", "import_jobs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("import_jobs")
