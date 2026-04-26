import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting, SourceConfig, VodSite

CURRENT_VOD_SITE_KEY = "current_vod_site_id"


async def get_current_vod_site(db: AsyncSession) -> VodSite | None:
    setting = await db.scalar(select(AppSetting).where(AppSetting.key == CURRENT_VOD_SITE_KEY))
    if setting is None:
        return None

    site_id = setting.value.get("vod_site_id")
    if not site_id:
        return None

    try:
        parsed_site_id = uuid.UUID(str(site_id))
    except ValueError:
        return None

    return await _get_site_with_source(db, parsed_site_id)


async def set_current_vod_site(db: AsyncSession, vod_site_id: uuid.UUID) -> VodSite:
    site = await _get_site_with_source(db, vod_site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VOD site not found")
    if not site.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Disabled VOD site cannot be selected")
    if site.source_config is None or not site.source_config.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="VOD site parent source must be enabled",
        )

    statement = insert(AppSetting).values(key=CURRENT_VOD_SITE_KEY, value={"vod_site_id": str(site.id)})
    await db.execute(
        statement.on_conflict_do_update(
            index_elements=[AppSetting.key],
            set_={"value": statement.excluded.value},
        )
    )
    await db.commit()
    return site


async def clear_current_vod_site_if_matches(db: AsyncSession, vod_site_id: uuid.UUID) -> bool:
    setting = await db.scalar(select(AppSetting).where(AppSetting.key == CURRENT_VOD_SITE_KEY))
    if setting is None or str(setting.value.get("vod_site_id")) != str(vod_site_id):
        return False

    await db.delete(setting)
    return True


async def clear_current_vod_site_if_source_matches(db: AsyncSession, source_config_id: uuid.UUID) -> bool:
    site = await get_current_vod_site(db)
    if site is None or site.source_config_id != source_config_id:
        return False

    setting = await db.scalar(select(AppSetting).where(AppSetting.key == CURRENT_VOD_SITE_KEY))
    if setting is None:
        return False
    await db.delete(setting)
    return True


def current_vod_site_response(site: VodSite | None) -> dict | None:
    if site is None:
        return None
    return {
        "id": site.id,
        "source_config_id": site.source_config_id,
        "site_key": site.site_key,
        "site_name": site.site_name,
        "site_type": site.site_type,
        "api": site.api,
        "enabled": site.enabled,
        "source_name": site.source_config.name if site.source_config else None,
    }


async def _get_site_with_source(db: AsyncSession, site_id: uuid.UUID) -> VodSite | None:
    result = await db.execute(
        select(VodSite, SourceConfig)
        .join(SourceConfig, VodSite.source_config_id == SourceConfig.id, isouter=True)
        .where(VodSite.id == site_id)
    )
    row = result.first()
    if row is None:
        return None

    site, source_config = row
    site.source_config = source_config
    return site
