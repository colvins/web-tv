import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    warnings: list[str]
    created_at: datetime
    updated_at: datetime
