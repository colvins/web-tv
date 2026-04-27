import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.vod_catalog import VodCatalogDetailRead, VodCatalogPageRead, VodCategoryListRead, VodEpisodePlayRead
from app.services import vod_catalog

router = APIRouter(prefix="/vod", tags=["vod"])


@router.get("/categories", response_model=VodCategoryListRead)
async def get_vod_categories(
    source_config_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> VodCategoryListRead:
    return await vod_catalog.list_categories(db, source_config_id)


@router.get("/list", response_model=VodCatalogPageRead)
async def get_vod_list(
    source_config_id: uuid.UUID = Query(...),
    type_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> VodCatalogPageRead:
    return await vod_catalog.list_vods(db, source_config_id, type_id, page)


@router.get("/search", response_model=VodCatalogPageRead)
async def search_vod(
    source_config_id: uuid.UUID = Query(...),
    q: str = Query(..., min_length=1),
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> VodCatalogPageRead:
    return await vod_catalog.search_vods(db, source_config_id, q, page)


@router.get("/detail", response_model=VodCatalogDetailRead)
async def get_vod_detail(
    source_config_id: uuid.UUID = Query(...),
    vod_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> VodCatalogDetailRead:
    return await vod_catalog.get_vod_detail(db, source_config_id, vod_id)


@router.get("/episode-play", response_model=VodEpisodePlayRead)
async def get_vod_episode_play(
    source_config_id: uuid.UUID = Query(...),
    vod_id: str = Query(..., min_length=1),
    source_name: str = Query(..., min_length=1),
    episode_index: int = Query(..., ge=0),
    db: AsyncSession = Depends(get_db),
) -> VodEpisodePlayRead:
    return await vod_catalog.get_episode_play(db, source_config_id, vod_id, source_name, episode_index)
