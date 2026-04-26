import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SourceConfig
from app.schemas.source_config import SourceConfigCreate, SourceConfigUpdate


def _ordered_query() -> Select[tuple[SourceConfig]]:
    return select(SourceConfig).order_by(SourceConfig.created_at.desc(), SourceConfig.name.asc())


async def list_source_configs(db: AsyncSession) -> list[SourceConfig]:
    result = await db.scalars(_ordered_query())
    return list(result)


async def get_source_config(db: AsyncSession, config_id: uuid.UUID) -> SourceConfig:
    config = await db.get(SourceConfig, config_id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source config not found")
    return config


async def create_source_config(db: AsyncSession, payload: SourceConfigCreate) -> SourceConfig:
    config = SourceConfig(**payload.model_dump(mode="json"))
    db.add(config)
    await _commit_or_conflict(db)
    await db.refresh(config)
    return config


async def update_source_config(
    db: AsyncSession,
    config_id: uuid.UUID,
    payload: SourceConfigUpdate,
) -> SourceConfig:
    config = await get_source_config(db, config_id)
    for key, value in payload.model_dump(mode="json", exclude_unset=True).items():
        setattr(config, key, value)
    await _commit_or_conflict(db)
    await db.refresh(config)
    return config


async def delete_source_config(db: AsyncSession, config_id: uuid.UUID) -> None:
    config = await get_source_config(db, config_id)
    await db.delete(config)
    await db.commit()


async def _commit_or_conflict(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source config conflicts with an existing record",
        ) from exc
