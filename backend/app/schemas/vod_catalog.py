import uuid

from pydantic import BaseModel


class VodCatalogSiteRead(BaseModel):
    source_config_id: uuid.UUID
    source_name: str
    site_key: str | None = None
    site_name: str | None = None
    api_host: str | None = None
    api_path: str | None = None
    api_query_keys: list[str] = []


class VodCategoryRead(BaseModel):
    type_id: int | str | None = None
    type_name: str | None = None
    parent_type_id: int | str | None = None
    parent_type_name: str | None = None
    has_content: bool = True


class VodCatalogItemRead(BaseModel):
    vod_id: int | str | None = None
    name: str
    category_id: int | str | None = None
    category_name: str | None = None
    poster: str | None = None
    year: str | None = None
    area: str | None = None
    remarks: str | None = None


class VodCategoryListRead(BaseModel):
    site: VodCatalogSiteRead
    categories: list[VodCategoryRead]
    reason: str | None = None


class VodCatalogPageRead(BaseModel):
    site: VodCatalogSiteRead
    page: int
    pagecount: int
    total: int
    limit: int | None = None
    items: list[VodCatalogItemRead]


class VodPlaySourceSummaryRead(BaseModel):
    source_name: str
    episode_count: int
    episode_names: list[str]
    sample_episode_names: list[str]
    has_play_urls: bool


class VodCatalogDetailRead(BaseModel):
    site: VodCatalogSiteRead
    vod_id: int | str | None = None
    name: str
    category_id: int | str | None = None
    category_name: str | None = None
    poster: str | None = None
    year: str | None = None
    area: str | None = None
    language: str | None = None
    remarks: str | None = None
    actor: str | None = None
    director: str | None = None
    description: str | None = None
    preferred_source_name: str | None = None
    play_sources: list[VodPlaySourceSummaryRead]


class VodEpisodePlayRead(BaseModel):
    vod_id: int | str | None = None
    source_name: str
    episode_index: int
    episode_name: str
    stream_url: str
    stream_host: str | None = None
    stream_type_guess: str
    is_hls_like: bool
    is_direct_file_like: bool
