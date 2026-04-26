import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import JsonDict, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class SourceConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_configs"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    config: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("name", "source_type", name="uq_source_configs_name_type"),
        Index("ix_source_configs_enabled_priority", "enabled", "priority"),
    )


class VodSite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vod_sites"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    config: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (Index("ix_vod_sites_enabled_priority", "enabled", "priority"),)


class LiveSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "live_sources"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    refresh_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    metadata_: Mapped[JsonDict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    channels: Mapped[list["LiveChannel"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class LiveChannel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "live_channels"

    live_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("live_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    group_name: Mapped[str | None] = mapped_column(String(120), index=True)
    logo_url: Mapped[str | None] = mapped_column(Text)
    stream_url: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    metadata_: Mapped[JsonDict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    source: Mapped[LiveSource] = relationship(back_populates="channels")

    __table_args__ = (
        UniqueConstraint("live_source_id", "name", "stream_url", name="uq_live_channels_source_name_stream"),
        Index("ix_live_channels_group_sort", "group_name", "sort_order"),
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
