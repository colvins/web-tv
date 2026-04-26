import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VodSiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_config_id: uuid.UUID | None
    import_job_id: uuid.UUID | None
    site_key: str
    site_name: str
    site_type: int | None = None
    api: str | None = None
    searchable: bool | None = None
    changeable: bool | None = None
    quick_search: bool | None = None
    filterable: bool | None = None
    player_type: int | None = None
    enabled: bool
    sort_order: int
    analysis_note: str | None = None
    created_at: datetime
    updated_at: datetime


class VodSiteUpdate(BaseModel):
    enabled: bool
