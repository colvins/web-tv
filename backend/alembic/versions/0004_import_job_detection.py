"""import job detection fields

Revision ID: 0004_import_job_detection
Revises: 0003_import_jobs
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_import_job_detection"
down_revision: str | None = "0003_import_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("import_jobs", sa.Column("detected_format", sa.String(length=40), nullable=True))
    op.add_column("import_jobs", sa.Column("detection_confidence", sa.Float(), nullable=True))
    op.add_column("import_jobs", sa.Column("detection_note", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_import_jobs_detected_format",
        "import_jobs",
        "detected_format IS NULL OR detected_format IN ('plain_json', 'catvod_json', 'm3u', 'txt', 'base64_json', 'binary_wrapped', 'unknown')",
    )
    op.create_index("ix_import_jobs_detected_format", "import_jobs", ["detected_format"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_import_jobs_detected_format", table_name="import_jobs")
    op.drop_constraint("ck_import_jobs_detected_format", "import_jobs", type_="check")
    op.drop_column("import_jobs", "detection_note")
    op.drop_column("import_jobs", "detection_confidence")
    op.drop_column("import_jobs", "detected_format")
