import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceSnapshotSiteSample(BaseModel):
    key: str | None = None
    name: str | None = None
    type: int | None = None
    api: str | None = None
    searchable: bool | int | None = None
    quickSearch: bool | int | None = None
    changeable: bool | int | None = None
    categories_hint: list[str] | str | None = None


class SourceSnapshotLiveSample(BaseModel):
    name: str | None = None
    type: str | int | None = None
    url_host: str | None = None
    playerType: str | int | None = None


class SourceSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_config_id: uuid.UUID
    import_job_id: uuid.UUID | None = None
    content_sha256: str
    detected_format: str | None = None
    recovered_format: str | None = None
    root_keys: list[str]
    sites_count: int
    lives_count: int
    parses_count: int
    has_spider: bool
    spider_summary: str | None = None
    site_samples: list[SourceSnapshotSiteSample] = []
    live_samples: list[SourceSnapshotLiveSample] = []
    warnings: list[str]
    created_at: datetime
    updated_at: datetime
