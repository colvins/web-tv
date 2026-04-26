import uuid
from typing import Any, Literal

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


class CurrentVodSiteExtAnalysis(BaseModel):
    present: bool
    value_type: str | None
    summary: str
    looks_like_url: bool
    looks_like_json: bool
    looks_like_base64: bool
    looks_like_executable_or_opaque: bool


class CurrentVodSiteSupportAssessment(BaseModel):
    level: Literal["metadata_only", "possible_http", "requires_spider", "unsupported_unknown"]
    reason: str
    next_step: str


class CurrentVodSiteAnalysisRead(BaseModel):
    site_id: uuid.UUID
    site_name: str
    site_key: str
    site_type: int | None = None
    api: str | None = None
    source_name: str | None = None
    enabled: bool
    raw_keys: list[str]
    known_flags: dict[str, Any]
    ext_analysis: CurrentVodSiteExtAnalysis
    support_assessment: CurrentVodSiteSupportAssessment
    warnings: list[str]
