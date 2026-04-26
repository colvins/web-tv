import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.source_config import SourceConfigCreate, SourceConfigRead, SourceConfigUpdate
from app.schemas.import_job import ImportJobRead
from app.schemas.source_snapshot import SourceSnapshotRead
from app.schemas.vod_site import VodSiteRead
from app.services import import_jobs, source_configs, source_snapshots, vod_sites

router = APIRouter(prefix="/configs", tags=["source-configs"])


@router.get("", response_model=list[SourceConfigRead])
async def list_configs(db: AsyncSession = Depends(get_db)) -> list[SourceConfigRead]:
    return await source_configs.list_source_configs(db)


@router.post("", response_model=SourceConfigRead, status_code=status.HTTP_201_CREATED)
async def create_config(
    payload: SourceConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> SourceConfigRead:
    return await source_configs.create_source_config(db, payload)


@router.get("/{config_id}", response_model=SourceConfigRead)
async def get_config(config_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SourceConfigRead:
    return await source_configs.get_source_config(db, config_id)


@router.patch("/{config_id}", response_model=SourceConfigRead)
async def update_config(
    config_id: uuid.UUID,
    payload: SourceConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> SourceConfigRead:
    return await source_configs.update_source_config(db, config_id, payload)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(config_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Response:
    await source_configs.delete_source_config(db, config_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{config_id}/import", response_model=ImportJobRead)
async def import_config(config_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ImportJobRead:
    return await import_jobs.import_source_config(db, config_id)


@router.post("/{config_id}/extract-sites", response_model=list[VodSiteRead])
async def extract_sites(config_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[VodSiteRead]:
    return await vod_sites.extract_sites_for_source(db, config_id)


@router.get("/{config_id}/snapshot/latest", response_model=SourceSnapshotRead)
async def get_latest_snapshot(config_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SourceSnapshotRead:
    return await source_snapshots.require_latest_source_snapshot(db, config_id)


@router.get("/{config_id}/vod-sites", response_model=list[VodSiteRead])
async def list_vod_sites(config_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[VodSiteRead]:
    return await vod_sites.list_vod_sites_for_source(db, config_id)
