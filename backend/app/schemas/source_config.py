import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer


class SourceType(StrEnum):
    json = "json"
    m3u = "m3u"
    txt = "txt"
    m3u8 = "m3u8"


class SourceConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    source_type: SourceType
    url: HttpUrl
    enabled: bool = True

    @field_serializer("url")
    def serialize_url(self, value: HttpUrl) -> str:
        return str(value)


class SourceConfigCreate(SourceConfigBase):
    pass


class SourceConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    source_type: SourceType | None = None
    url: HttpUrl | None = None
    enabled: bool | None = None

    @field_serializer("url")
    def serialize_url(self, value: HttpUrl | None) -> str | None:
        return str(value) if value is not None else None


class SourceConfigRead(SourceConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    last_import_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
    latest_import_status: str | None = None
    latest_detected_format: str | None = None
    latest_snapshot_exists: bool = False
    vod_site_count: int = 0
    live_channel_count: int = 0
    created_at: datetime
    updated_at: datetime
