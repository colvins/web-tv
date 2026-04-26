import uuid

from pydantic import BaseModel


class CurrentVodSiteUpdate(BaseModel):
    vod_site_id: uuid.UUID


class CurrentVodSiteRead(BaseModel):
    id: uuid.UUID
    source_config_id: uuid.UUID | None
    site_key: str
    site_name: str
    site_type: int | None = None
    api: str | None = None
    enabled: bool
    source_name: str | None = None
