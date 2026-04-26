import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ImportJobStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_config_id: uuid.UUID
    status: ImportJobStatus
    source_url: str
    content_type: str | None = None
    content_length: int | None = None
    content_sha256: str | None = None
    raw_preview: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
