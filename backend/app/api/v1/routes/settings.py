from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.app_setting import (
    CurrentVodSiteAnalysisRead,
    CurrentVodSiteRead,
    CurrentVodSiteSpiderAnalysisRead,
    CurrentVodSiteUpdate,
    SpiderArtifactEntryAnalysisRead,
    SpiderArtifactRead,
)
from app.services import app_settings, spider_artifact_analyses, spider_artifacts

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/current-vod-site", response_model=CurrentVodSiteRead | None)
async def get_current_vod_site(db: AsyncSession = Depends(get_db)) -> dict | None:
    site = await app_settings.get_current_vod_site(db)
    return app_settings.current_vod_site_response(site)


@router.get("/current-vod-site/analysis", response_model=CurrentVodSiteAnalysisRead | None)
async def get_current_vod_site_analysis(db: AsyncSession = Depends(get_db)) -> dict | None:
    return await app_settings.get_current_vod_site_analysis(db)


@router.get("/current-vod-site/spider-analysis", response_model=CurrentVodSiteSpiderAnalysisRead | None)
async def get_current_vod_site_spider_analysis(db: AsyncSession = Depends(get_db)) -> dict | None:
    return await app_settings.get_current_vod_site_spider_analysis(db)


@router.get("/current-vod-site/spider-artifact/latest", response_model=SpiderArtifactRead | None)
async def get_latest_spider_artifact(db: AsyncSession = Depends(get_db)) -> object | None:
    return await spider_artifacts.latest_current_spider_artifact(db)


@router.post("/current-vod-site/spider-artifact/probe", response_model=SpiderArtifactRead)
async def probe_spider_artifact(db: AsyncSession = Depends(get_db)) -> object:
    return await spider_artifacts.probe_current_spider_artifact(db)


@router.get(
    "/current-vod-site/spider-artifact/entry-analysis/latest",
    response_model=SpiderArtifactEntryAnalysisRead | None,
)
async def get_latest_spider_artifact_entry_analysis(db: AsyncSession = Depends(get_db)) -> object | None:
    return await spider_artifact_analyses.latest_current_entry_analysis(db)


@router.post(
    "/current-vod-site/spider-artifact/analyze-entries",
    response_model=SpiderArtifactEntryAnalysisRead | None,
)
async def analyze_spider_artifact_entries(db: AsyncSession = Depends(get_db)) -> object | None:
    return await spider_artifact_analyses.analyze_current_artifact_entries(db)


@router.put("/current-vod-site", response_model=CurrentVodSiteRead)
async def set_current_vod_site(
    payload: CurrentVodSiteUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    site = await app_settings.set_current_vod_site(db, payload.vod_site_id)
    return app_settings.current_vod_site_response(site)
