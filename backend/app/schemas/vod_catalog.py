import uuid

from pydantic import BaseModel


class VodCatalogSiteRead(BaseModel):
    source_config_id: uuid.UUID
    source_name: str
    site_key: str | None = None
    site_name: str | None = None


class VodCategoryRead(BaseModel):
    type_id: int | str | None = None
    type_name: str | None = None


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


class VodCatalogPageRead(BaseModel):
    site: VodCatalogSiteRead
    page: int
    pagecount: int
    total: int
    limit: int | None = None
    items: list[VodCatalogItemRead]
