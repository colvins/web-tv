import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VodSiteCapabilityAnalysis(BaseModel):
    key: str | None = None
    name: str | None = None
    type: int | str | None = None
    api: str | None = None
    api_host: str | None = None
    searchable: bool | int | None = None
    quickSearch: bool | int | None = None
    filterable: bool | int | None = None
    has_ext: bool
    ext_type: str | None = None
    ext_summary: str | None = None
    capability_level: str
    capability_reason: str


class VodCapabilityAnalysisSummary(BaseModel):
    total_sites: int
    generic_candidate_count: int
    spider_required_count: int
    unsupported_special_count: int
    missing_or_invalid_count: int
    unknown_count: int


class VodCapabilityAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_config_id: uuid.UUID
    source_snapshot_id: uuid.UUID
    source_snapshot_created_at: datetime
    summary: VodCapabilityAnalysisSummary
    site_analyses: list[VodSiteCapabilityAnalysis] = []
