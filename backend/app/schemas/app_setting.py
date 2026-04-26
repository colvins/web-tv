import uuid
from datetime import datetime
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


class CurrentVodSiteSpiderSupportStrategy(BaseModel):
    level: Literal[
        "unsupported_unknown",
        "needs_spider_runtime",
        "possible_js_runtime",
        "possible_http_adapter",
        "metadata_only",
    ]
    reason: str
    recommended_next_step: str


class CurrentVodSiteSpiderAnalysisRead(BaseModel):
    site_id: uuid.UUID
    site_key: str
    site_name: str
    site_type: int | None = None
    api: str | None = None
    source_name: str | None = None
    root_config_keys: list[str]
    spider_field_present: bool
    spider_field_summary: str
    api_reference_found: bool
    api_reference_locations: list[str]
    possible_reference_type: Literal[
        "none",
        "jar_reference",
        "js_reference",
        "py_reference",
        "remote_url_reference",
        "inline_name_only",
        "unknown",
    ]
    possible_reference_summary: str
    support_strategy: CurrentVodSiteSpiderSupportStrategy
    warnings: list[str]


class SpiderArtifactRead(BaseModel):
    id: uuid.UUID
    artifact_url: str
    expected_md5: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    sha256: str | None = None
    md5: str | None = None
    md5_matches: bool | None = None
    magic_hex: str | None = None
    detected_kind: str | None = None
    probe_status: Literal["pending", "success", "failed"]
    error_message: str | None = None
    probed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SpiderArtifactEntryAnalysisRead(BaseModel):
    id: uuid.UUID
    spider_artifact_id: uuid.UUID
    source_config_id: uuid.UUID
    source_snapshot_id: uuid.UUID | None = None
    analysis_status: Literal["success", "failed"]
    error_message: str | None = None
    total_entries: int | None = None
    total_compressed_size: int | None = None
    total_uncompressed_size: int | None = None
    top_level_dirs: list[str]
    extension_counts: dict[str, int]
    matching_api_entries: list[str]
    sample_entries: list[str]
    has_class: bool
    has_dex: bool
    has_js: bool
    has_json: bool
    has_assets: bool
    has_catvod_package: bool
    suspicious_large_entries: int
    created_at: datetime
    updated_at: datetime
