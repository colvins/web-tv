import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LiveExtractionStats(BaseModel):
    groups_count: int
    channels_count: int
    created_count: int
    updated_count: int
    disabled_missing_count: int
    warnings: list[str]


class LiveChannelGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_config_id: uuid.UUID
    name: str
    sort_order: int
    channel_count: int
    created_at: datetime
    updated_at: datetime


class LiveChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_config_id: uuid.UUID
    group_id: uuid.UUID | None = None
    name: str
    tvg_id: str | None = None
    tvg_name: str | None = None
    tvg_logo: str | None = None
    group_title: str | None = None
    stream_url: str
    raw_extinf: dict[str, Any]
    enabled: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class LiveChannelUpdate(BaseModel):
    enabled: bool


class LiveChannelM3U8Info(BaseModel):
    playlist_kind: str | None = None
    has_media_segments: bool = False
    sample_segment_path: str | None = None
    preview_text: str | None = None


class LiveChannelSampleSegmentCheck(BaseModel):
    status_code: int | None = None
    content_type: str | None = None
    content_length: int | None = None
    final_host: str | None = None
    warning: str | None = None


class LiveChannelDiagnosisRead(BaseModel):
    channel_id: uuid.UUID
    channel_name: str
    group_name: str | None = None
    stream_host: str | None = None
    final_host: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    content_length: int | None = None
    redirect_count: int = 0
    stream_type_guess: str
    body_preview: str | None = None
    m3u8_info: LiveChannelM3U8Info | None = None
    sample_segment_check: LiveChannelSampleSegmentCheck | None = None
    diagnosis_level: str
    diagnosis_summary: str
    suggested_next_step: str
    warnings: list[str]
