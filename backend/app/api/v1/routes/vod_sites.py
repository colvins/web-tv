import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.vod_site import VodSiteRead, VodSiteUpdate
from app.services import vod_sites

router = APIRouter(prefix="/vod-sites", tags=["vod-sites"])


@router.get("/{site_id}", response_model=VodSiteRead)
async def get_site(site_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> VodSiteRead:
    return await vod_sites.get_vod_site(db, site_id)


@router.patch("/{site_id}", response_model=VodSiteRead)
async def update_site(
    site_id: uuid.UUID,
    payload: VodSiteUpdate,
    db: AsyncSession = Depends(get_db),
) -> VodSiteRead:
    return await vod_sites.update_vod_site_enabled(db, site_id, payload.enabled)
