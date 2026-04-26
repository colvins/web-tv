from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.app_setting import CurrentVodSiteAnalysisRead, CurrentVodSiteRead, CurrentVodSiteUpdate
from app.services import app_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/current-vod-site", response_model=CurrentVodSiteRead | None)
async def get_current_vod_site(db: AsyncSession = Depends(get_db)) -> dict | None:
    site = await app_settings.get_current_vod_site(db)
    return app_settings.current_vod_site_response(site)


@router.get("/current-vod-site/analysis", response_model=CurrentVodSiteAnalysisRead | None)
async def get_current_vod_site_analysis(db: AsyncSession = Depends(get_db)) -> dict | None:
    return await app_settings.get_current_vod_site_analysis(db)


@router.put("/current-vod-site", response_model=CurrentVodSiteRead)
async def set_current_vod_site(
    payload: CurrentVodSiteUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    site = await app_settings.set_current_vod_site(db, payload.vod_site_id)
    return app_settings.current_vod_site_response(site)
