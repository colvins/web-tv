from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import JsonDict, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class SourceConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_configs"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    last_import_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    import_jobs: Mapped[list["ImportJob"]] = relationship(back_populates="source_config", cascade="all, delete-orphan")
    vod_sites: Mapped[list["VodSite"]] = relationship(back_populates="source_config", cascade="all, delete-orphan")
    vod_categories: Mapped[list["VodCategory"]] = relationship(back_populates="source_config", cascade="all, delete-orphan")
    snapshots: Mapped[list["SourceSnapshot"]] = relationship(back_populates="source_config", cascade="all, delete-orphan")
    live_channel_groups: Mapped[list["LiveChannelGroup"]] = relationship(
        back_populates="source_config",
        cascade="all, delete-orphan",
    )
    live_channels: Mapped[list["LiveChannel"]] = relationship(back_populates="source_config", cascade="all, delete-orphan")
    spider_artifacts: Mapped[list["SpiderArtifact"]] = relationship(
        back_populates="source_config",
        cascade="all, delete-orphan",
    )
    spider_artifact_analyses: Mapped[list["SpiderArtifactAnalysis"]] = relationship(
        back_populates="source_config",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("source_type IN ('json', 'm3u', 'txt', 'm3u8')", name="ck_source_configs_source_type"),
        UniqueConstraint("name", name="uq_source_configs_name"),
        Index("ix_source_configs_enabled_type", "enabled", "source_type"),
    )


class ImportJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "import_jobs"

    source_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    content_length: Mapped[int | None] = mapped_column(Integer)
    content_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    raw_preview: Mapped[str | None] = mapped_column(Text)
    detected_format: Mapped[str | None] = mapped_column(String(40), index=True)
    detection_confidence: Mapped[float | None] = mapped_column()
    detection_note: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    source_config: Mapped[SourceConfig] = relationship(back_populates="import_jobs")
    vod_sites: Mapped[list["VodSite"]] = relationship(back_populates="import_job")
    snapshots: Mapped[list["SourceSnapshot"]] = relationship(back_populates="import_job")

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'success', 'failed')", name="ck_import_jobs_status"),
        CheckConstraint(
            "detected_format IS NULL OR detected_format IN ('plain_json', 'catvod_json', 'm3u', 'txt', 'base64_json', 'binary_wrapped', 'unknown')",
            name="ck_import_jobs_detected_format",
        ),
        Index("ix_import_jobs_source_status", "source_config_id", "status"),
        Index("ix_import_jobs_created_at", "created_at"),
    )


class SourceSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_snapshots"

    source_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="SET NULL"),
        index=True,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    detected_format: Mapped[str | None] = mapped_column(String(40), index=True)
    recovered_format: Mapped[str | None] = mapped_column(String(40), index=True)
    root_config: Mapped[JsonDict | None] = mapped_column(JSONB)
    root_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    sites_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lives_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_spider: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    spider_summary: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    source_config: Mapped[SourceConfig] = relationship(back_populates="snapshots")
    import_job: Mapped[ImportJob | None] = relationship(back_populates="snapshots")
    spider_artifacts: Mapped[list["SpiderArtifact"]] = relationship(back_populates="source_snapshot")
    spider_artifact_analyses: Mapped[list["SpiderArtifactAnalysis"]] = relationship(back_populates="source_snapshot")

    __table_args__ = (
        UniqueConstraint("source_config_id", "content_sha256", name="uq_source_snapshots_source_sha"),
        Index("ix_source_snapshots_source_created", "source_config_id", "created_at"),
    )


class SpiderArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spider_artifacts"

    source_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="SET NULL"),
        index=True,
    )
    artifact_url: Mapped[str] = mapped_column(Text, nullable=False)
    expected_md5: Mapped[str | None] = mapped_column(String(32))
    content_type: Mapped[str | None] = mapped_column(String(255))
    content_length: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    md5: Mapped[str | None] = mapped_column(String(32), index=True)
    md5_matches: Mapped[bool | None] = mapped_column(Boolean)
    magic_hex: Mapped[str | None] = mapped_column(String(64))
    detected_kind: Mapped[str | None] = mapped_column(String(40), index=True)
    probe_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    probed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    source_config: Mapped[SourceConfig] = relationship(back_populates="spider_artifacts")
    source_snapshot: Mapped[SourceSnapshot | None] = relationship(back_populates="spider_artifacts")
    entry_analyses: Mapped[list["SpiderArtifactAnalysis"]] = relationship(
        back_populates="spider_artifact",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("probe_status IN ('pending', 'success', 'failed')", name="ck_spider_artifacts_status"),
        UniqueConstraint("source_config_id", "artifact_url", "expected_md5", name="uq_spider_artifacts_source_url_md5"),
        Index("ix_spider_artifacts_source_created", "source_config_id", "created_at"),
    )


class SpiderArtifactAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spider_artifact_analyses"

    spider_artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("spider_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="SET NULL"),
        index=True,
    )
    analysis_status: Mapped[str] = mapped_column(String(24), nullable=False, default="success", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    total_entries: Mapped[int | None] = mapped_column(Integer)
    total_compressed_size: Mapped[int | None] = mapped_column(BigInteger)
    total_uncompressed_size: Mapped[int | None] = mapped_column(BigInteger)
    top_level_dirs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    extension_counts: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)
    matching_api_entries: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    sample_entries: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    has_class: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_dex: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_js: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_json: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_assets: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_catvod_package: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suspicious_large_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    spider_artifact: Mapped[SpiderArtifact] = relationship(back_populates="entry_analyses")
    source_config: Mapped[SourceConfig] = relationship(back_populates="spider_artifact_analyses")
    source_snapshot: Mapped[SourceSnapshot | None] = relationship(back_populates="spider_artifact_analyses")

    __table_args__ = (
        CheckConstraint(
            "analysis_status IN ('success', 'failed')",
            name="ck_spider_artifact_analyses_status",
        ),
        Index("ix_spider_artifact_analyses_artifact_created", "spider_artifact_id", "created_at"),
        Index("ix_spider_artifact_analyses_source_created", "source_config_id", "created_at"),
    )


class VodSite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vod_sites"

    source_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_configs.id", ondelete="CASCADE"),
        index=True,
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="SET NULL"),
        index=True,
    )
    site_key: Mapped[str] = mapped_column(String(180), nullable=False)
    site_name: Mapped[str] = mapped_column(String(240), nullable=False)
    site_type: Mapped[int | None] = mapped_column(Integer)
    api: Mapped[str | None] = mapped_column(Text)
    searchable: Mapped[bool | None] = mapped_column(Boolean)
    changeable: Mapped[bool | None] = mapped_column(Boolean)
    quick_search: Mapped[bool | None] = mapped_column(Boolean)
    filterable: Mapped[bool | None] = mapped_column(Boolean)
    player_type: Mapped[int | None] = mapped_column(Integer)
    ext: Mapped[JsonDict | list | str | int | None] = mapped_column(JSONB)
    style: Mapped[JsonDict | list | str | int | None] = mapped_column(JSONB)
    categories_hint: Mapped[JsonDict | list | str | int | None] = mapped_column(JSONB)
    raw_config: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_note: Mapped[str | None] = mapped_column(Text)

    source_config: Mapped[SourceConfig | None] = relationship(back_populates="vod_sites")
    import_job: Mapped[ImportJob | None] = relationship(back_populates="vod_sites")

    __table_args__ = (
        UniqueConstraint("source_config_id", "site_key", name="uq_vod_sites_source_site_key"),
        Index("ix_vod_sites_source_sort", "source_config_id", "sort_order"),
        Index("ix_vod_sites_enabled_sort", "enabled", "sort_order"),
    )


class VodCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vod_categories"

    source_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_key: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    type_id: Mapped[str] = mapped_column(String(120), nullable=False)
    type_name: Mapped[str] = mapped_column(String(240), nullable=False)
    parent_type_id: Mapped[str | None] = mapped_column(String(120))
    parent_type_name: Mapped[str | None] = mapped_column(String(240))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    source_config: Mapped[SourceConfig] = relationship(back_populates="vod_categories")

    __table_args__ = (
        UniqueConstraint("source_config_id", "site_key", "type_id", name="uq_vod_categories_source_site_type"),
        Index("ix_vod_categories_source_site_sort", "source_config_id", "site_key", "sort_order"),
        Index("ix_vod_categories_enabled_sort", "enabled", "sort_order"),
    )


class AppSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    value: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)


class LiveSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "live_sources"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    refresh_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    metadata_: Mapped[JsonDict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class LiveChannel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "live_channels"

    source_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_configs.id", ondelete="CASCADE"),
        index=True,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("live_channel_groups.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tvg_id: Mapped[str | None] = mapped_column(String(180), index=True)
    tvg_name: Mapped[str | None] = mapped_column(String(240), index=True)
    tvg_logo: Mapped[str | None] = mapped_column(Text)
    group_title: Mapped[str | None] = mapped_column(String(160), index=True)
    stream_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_extinf: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    source_config: Mapped[SourceConfig] = relationship(back_populates="live_channels")
    group: Mapped[LiveChannelGroup | None] = relationship(back_populates="channels")

    __table_args__ = (
        UniqueConstraint("source_config_id", "stream_url", name="uq_live_channels_source_stream"),
        Index("ix_live_channels_source_group_sort", "source_config_id", "group_id", "sort_order"),
        Index("ix_live_channels_enabled_sort", "enabled", "sort_order"),
    )


class ParseApi(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parse_apis"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    headers: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)
    params: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (Index("ix_parse_apis_enabled_priority", "enabled", "priority"),)


class LiveChannelGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "live_channel_groups"

    source_config_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    channel_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    source_config: Mapped[SourceConfig] = relationship(back_populates="live_channel_groups")
    channels: Mapped[list["LiveChannel"]] = relationship(back_populates="group")

    __table_args__ = (
        UniqueConstraint("source_config_id", "name", name="uq_live_channel_groups_source_name"),
        Index("ix_live_channel_groups_source_sort", "source_config_id", "sort_order"),
    )


class VodCache(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vod_cache"

    source_key: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(180), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    detail_url: Mapped[str | None] = mapped_column(Text)
    poster_url: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        UniqueConstraint("source_key", "external_id", name="uq_vod_cache_source_external"),
        Index("ix_vod_cache_title_category", "title", "category"),
    )


class PlayHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "play_history"

    content_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    content_id: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    position_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (Index("ix_play_history_type_played", "content_type", "played_at"),)


class Favorite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "favorites"

    content_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    content_id: Mapped[str] = mapped_column(String(180), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    payload: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("content_type", "content_id", name="uq_favorites_type_content"),
        Index("ix_favorites_type_created", "content_type", "created_at"),
    )
