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
