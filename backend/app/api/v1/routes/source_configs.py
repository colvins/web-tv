import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.source_config import SourceConfigCreate, SourceConfigRead, SourceConfigUpdate
from app.services import source_configs

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
