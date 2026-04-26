"""vod site catalog

Revision ID: 0005_vod_site_catalog
Revises: 0004_import_job_detection
Create Date: 2026-04-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_vod_site_catalog"
down_revision: str | None = "0004_import_job_detection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vod_sites", sa.Column("source_config_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("vod_sites", sa.Column("import_job_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("vod_sites", sa.Column("site_key", sa.String(length=180), nullable=True))
    op.add_column("vod_sites", sa.Column("site_name", sa.String(length=240), nullable=True))
    op.add_column("vod_sites", sa.Column("site_type", sa.Integer(), nullable=True))
    op.add_column("vod_sites", sa.Column("api", sa.Text(), nullable=True))
    op.add_column("vod_sites", sa.Column("searchable", sa.Boolean(), nullable=True))
    op.add_column("vod_sites", sa.Column("changeable", sa.Boolean(), nullable=True))
    op.add_column("vod_sites", sa.Column("quick_search", sa.Boolean(), nullable=True))
    op.add_column("vod_sites", sa.Column("filterable", sa.Boolean(), nullable=True))
    op.add_column("vod_sites", sa.Column("player_type", sa.Integer(), nullable=True))
    op.add_column("vod_sites", sa.Column("ext", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("vod_sites", sa.Column("style", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("vod_sites", sa.Column("categories_hint", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("vod_sites", sa.Column("raw_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("vod_sites", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("vod_sites", sa.Column("analysis_note", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE vod_sites
        SET site_key = COALESCE(name, id::text),
            site_name = COALESCE(name, 'Legacy VOD Site'),
            api = base_url,
            raw_config = jsonb_build_object('legacy_base_url', base_url, 'legacy_config', config),
            enabled = false,
            analysis_note = 'Legacy skeleton row preserved during catalog migration; not linked to a SourceConfig.'
        WHERE site_key IS NULL
        """
    )
    op.alter_column("vod_sites", "site_key", existing_type=sa.String(length=180), nullable=False)
    op.alter_column("vod_sites", "site_name", existing_type=sa.String(length=240), nullable=False)
    op.alter_column("vod_sites", "raw_config", existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=False)

    op.drop_index("ix_vod_sites_enabled_priority", table_name="vod_sites")
    op.drop_constraint("uq_vod_sites_name", "vod_sites", type_="unique")
    op.drop_column("vod_sites", "priority")
    op.drop_column("vod_sites", "config")
    op.drop_column("vod_sites", "base_url")
    op.drop_column("vod_sites", "name")

    op.create_foreign_key(
        "fk_vod_sites_source_config_id_source_configs",
        "vod_sites",
        "source_configs",
        ["source_config_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_vod_sites_import_job_id_import_jobs",
        "vod_sites",
        "import_jobs",
        ["import_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint("uq_vod_sites_source_site_key", "vod_sites", ["source_config_id", "site_key"])
    op.create_index("ix_vod_sites_source_config_id", "vod_sites", ["source_config_id"], unique=False)
    op.create_index("ix_vod_sites_import_job_id", "vod_sites", ["import_job_id"], unique=False)
    op.create_index("ix_vod_sites_source_sort", "vod_sites", ["source_config_id", "sort_order"], unique=False)
    op.create_index("ix_vod_sites_enabled_sort", "vod_sites", ["enabled", "sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vod_sites_enabled_sort", table_name="vod_sites")
    op.drop_index("ix_vod_sites_source_sort", table_name="vod_sites")
    op.drop_index("ix_vod_sites_import_job_id", table_name="vod_sites")
    op.drop_index("ix_vod_sites_source_config_id", table_name="vod_sites")
    op.drop_constraint("uq_vod_sites_source_site_key", "vod_sites", type_="unique")
    op.drop_constraint("fk_vod_sites_import_job_id_import_jobs", "vod_sites", type_="foreignkey")
    op.drop_constraint("fk_vod_sites_source_config_id_source_configs", "vod_sites", type_="foreignkey")

    op.add_column("vod_sites", sa.Column("name", sa.String(length=120), nullable=True))
    op.add_column("vod_sites", sa.Column("base_url", sa.Text(), nullable=True))
    op.add_column("vod_sites", sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("vod_sites", sa.Column("priority", sa.Integer(), nullable=False, server_default="100"))
    op.execute("UPDATE vod_sites SET name = site_name, base_url = COALESCE(api, '')")
    op.alter_column("vod_sites", "name", existing_type=sa.String(length=120), nullable=False)
    op.alter_column("vod_sites", "base_url", existing_type=sa.Text(), nullable=False)

    op.drop_column("vod_sites", "analysis_note")
    op.drop_column("vod_sites", "sort_order")
    op.drop_column("vod_sites", "raw_config")
    op.drop_column("vod_sites", "categories_hint")
    op.drop_column("vod_sites", "style")
    op.drop_column("vod_sites", "ext")
    op.drop_column("vod_sites", "player_type")
    op.drop_column("vod_sites", "filterable")
    op.drop_column("vod_sites", "quick_search")
    op.drop_column("vod_sites", "changeable")
    op.drop_column("vod_sites", "searchable")
    op.drop_column("vod_sites", "api")
    op.drop_column("vod_sites", "site_type")
    op.drop_column("vod_sites", "site_name")
    op.drop_column("vod_sites", "site_key")
    op.drop_column("vod_sites", "import_job_id")
    op.drop_column("vod_sites", "source_config_id")
    op.create_unique_constraint("uq_vod_sites_name", "vod_sites", ["name"])
    op.create_index("ix_vod_sites_enabled_priority", "vod_sites", ["enabled", "priority"], unique=False)
