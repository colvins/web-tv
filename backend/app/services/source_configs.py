import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportJob, SourceConfig, SourceSnapshot
from app.schemas.source_config import SourceConfigCreate, SourceConfigUpdate


def _ordered_query() -> Select[tuple[SourceConfig]]:
    return select(SourceConfig).order_by(SourceConfig.created_at.desc(), SourceConfig.name.asc())


async def list_source_configs(db: AsyncSession) -> list[SourceConfig]:
    from app.services.live_m3u import count_live_channels_by_source
    from app.services.vod_sites import count_vod_sites_by_source

    result = await db.scalars(_ordered_query())
    configs = list(result)
    await _populate_source_config_metadata(
        db,
        configs,
        vod_counts=await count_vod_sites_by_source(db),
        live_counts=await count_live_channels_by_source(db),
    )
    return configs


async def get_source_config(db: AsyncSession, config_id: uuid.UUID) -> SourceConfig:
    from app.services.live_m3u import count_live_channels_by_source
    from app.services.vod_sites import count_vod_sites_by_source

    config = await db.get(SourceConfig, config_id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source config not found")
    await _populate_source_config_metadata(
        db,
        [config],
        vod_counts=await count_vod_sites_by_source(db),
        live_counts=await count_live_channels_by_source(db),
    )
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
    from app.services.app_settings import clear_current_vod_site_if_source_matches

    config = await get_source_config(db, config_id)
    for key, value in payload.model_dump(mode="json", exclude_unset=True).items():
        setattr(config, key, value)
    if payload.enabled is False:
        await clear_current_vod_site_if_source_matches(db, config.id)
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


async def _populate_source_config_metadata(
    db: AsyncSession,
    configs: list[SourceConfig],
    *,
    vod_counts: dict[uuid.UUID, int],
    live_counts: dict[uuid.UUID, int],
) -> None:
    if not configs:
        return

    config_ids = [config.id for config in configs]
    latest_imports = await _latest_imports_by_source(db, config_ids)
    snapshot_ids = await _snapshot_source_ids(db, config_ids)

    for config in configs:
        config.vod_site_count = vod_counts.get(config.id, 0)
        config.live_channel_count = live_counts.get(config.id, 0)
        latest_import = latest_imports.get(config.id)
        config.latest_import_status = latest_import.status if latest_import else None
        config.latest_detected_format = latest_import.detected_format if latest_import else None
        config.latest_snapshot_exists = config.id in snapshot_ids


async def _latest_imports_by_source(
    db: AsyncSession,
    config_ids: list[uuid.UUID],
) -> dict[uuid.UUID, ImportJob]:
    result = await db.scalars(
        select(ImportJob)
        .where(ImportJob.source_config_id.in_(config_ids))
        .order_by(ImportJob.source_config_id.asc(), ImportJob.created_at.desc(), ImportJob.updated_at.desc())
    )
    latest: dict[uuid.UUID, ImportJob] = {}
    for job in result:
        if job.source_config_id not in latest:
            latest[job.source_config_id] = job
    return latest


async def _snapshot_source_ids(db: AsyncSession, config_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    rows = await db.scalars(
        select(SourceSnapshot.source_config_id)
        .where(SourceSnapshot.source_config_id.in_(config_ids))
        .distinct()
    )
    return set(rows)
