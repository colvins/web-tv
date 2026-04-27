import hashlib
import json
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportJob, SourceConfig, VodSite
from app.services.import_jobs import MAX_IMPORT_BYTES, REQUEST_TIMEOUT_SECONDS
from app.services.app_settings import clear_current_vod_site_if_matches
from app.services.source_detection import (
    build_host_derived_source_name,
    build_indexed_site_key,
    looks_like_direct_maccms_collector_url,
    normalize_collector_api_url,
    recover_json_config,
)
from app.services.source_configs import get_source_config

SUPPORTED_FORMATS = {"catvod_json", "plain_json", "base64_json", "binary_wrapped"}
UNKNOWN_SITE_FIELDS = {
    "key",
    "name",
    "type",
    "api",
    "searchable",
    "changeable",
    "quickSearch",
    "quick_search",
    "filterable",
    "filter",
    "playerType",
    "player_type",
    "ext",
    "style",
    "categories",
    "categories_hint",
    "categoriesHint",
}


async def list_vod_sites_for_source(db: AsyncSession, source_config_id: uuid.UUID) -> list[VodSite]:
    await get_source_config(db, source_config_id)
    result = await db.scalars(
        select(VodSite)
        .where(VodSite.source_config_id == source_config_id)
        .order_by(VodSite.sort_order.asc(), VodSite.site_name.asc())
    )
    return list(result)


async def get_vod_site(db: AsyncSession, site_id: uuid.UUID) -> VodSite:
    site = await db.get(VodSite, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VOD site not found")
    return site


async def update_vod_site_enabled(db: AsyncSession, site_id: uuid.UUID, enabled: bool) -> VodSite:
    site = await get_vod_site(db, site_id)
    site.enabled = enabled
    if not enabled:
        await clear_current_vod_site_if_matches(db, site.id)
    await db.commit()
    await db.refresh(site)
    return site


async def extract_sites_for_source(db: AsyncSession, source_config_id: uuid.UUID) -> list[VodSite]:
    source_config = await get_source_config(db, source_config_id)
    import_job = await _latest_successful_import_job(db, source_config_id)
    if import_job.detected_format not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Latest successful import is not a JSON-compatible aggregation config",
        )

    content = await _download_source_config(source_config.url)
    if import_job.content_sha256:
        content_sha256 = hashlib.sha256(content).hexdigest()
        if content_sha256 != import_job.content_sha256:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Source content changed since the latest successful import; import again before extracting",
            )

    config = recover_json_config(content)
    if not isinstance(config, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unable to recover JSON config")

    if not isinstance(config.get("sites"), list):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Config does not contain sites[]")

    return await sync_sites_from_root_config(
        db,
        source_config_id=source_config.id,
        import_job_id=import_job.id,
        root_config=config,
        commit=True,
    )


async def count_vod_sites_by_source(db: AsyncSession) -> dict[uuid.UUID, int]:
    rows = await db.execute(
        select(VodSite.source_config_id, func.count(VodSite.id))
        .where(
            VodSite.source_config_id.is_not(None),
            VodSite.enabled.is_(True),
        )
        .group_by(VodSite.source_config_id)
    )
    return {source_id: count for source_id, count in rows if source_id is not None}


async def sync_sites_from_root_config(
    db: AsyncSession,
    *,
    source_config_id: uuid.UUID,
    import_job_id: uuid.UUID,
    root_config: dict[str, Any],
    commit: bool = False,
) -> list[VodSite]:
    sites = root_config.get("sites")
    if not isinstance(sites, list):
        return []

    seen_keys: set[str] = set()
    for index, entry in enumerate(sites):
        if not isinstance(entry, dict):
            continue
        values = _site_values(source_config_id, import_job_id, entry, index)
        if values is None:
            continue
        seen_keys.add(values["site_key"])
        await _upsert_site(db, values)

    await _disable_missing_sites(db, source_config_id, seen_keys)
    if commit:
        await db.commit()

    result = await db.scalars(
        select(VodSite)
        .where(VodSite.source_config_id == source_config_id)
        .order_by(VodSite.sort_order.asc(), VodSite.site_name.asc())
    )
    return list(result)


async def _latest_successful_import_job(db: AsyncSession, source_config_id: uuid.UUID) -> ImportJob:
    job = await db.scalar(
        select(ImportJob)
        .where(ImportJob.source_config_id == source_config_id, ImportJob.status == "success")
        .order_by(ImportJob.finished_at.desc().nullslast(), ImportJob.created_at.desc())
        .limit(1)
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Source has no successful import job")
    return job


async def _download_source_config(url: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS)) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            length = response.headers.get("content-length")
            if length and int(length) > MAX_IMPORT_BYTES:
                raise ValueError("Source response exceeds 5MB limit")
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > MAX_IMPORT_BYTES:
                    raise ValueError("Source response exceeds 5MB limit")
                chunks.append(chunk)
    return b"".join(chunks)


def _site_values(
    source_config_id: uuid.UUID,
    import_job_id: uuid.UUID,
    entry: dict[str, Any],
    index: int,
) -> dict[str, Any] | None:
    ext = entry.get("ext")
    ext_api = ext.get("api") if isinstance(ext, dict) else None
    api_url = normalize_collector_api_url(_string_or_none(entry.get("api")) or _string_or_none(ext_api))
    if not api_url or not looks_like_direct_maccms_collector_url(api_url):
        return None

    site_key = build_indexed_site_key(entry.get("key"), api_url)
    site_name = _string_or_none(entry.get("name")) or build_host_derived_source_name(api_url)
    if not site_key or not site_name:
        return None

    unknown_keys = sorted(str(key) for key in entry.keys() if str(key) not in UNKNOWN_SITE_FIELDS)
    risky_keys = [key for key in ("spider", "jar", "js", "python", "ext") if key in entry]
    notes = ["Catalog metadata only; site API and executable fields were not called."]
    if unknown_keys:
        notes.append(f"Unknown fields kept in raw_config: {', '.join(unknown_keys[:8])}.")
    if risky_keys:
        notes.append(f"Executable or opaque fields left inert in raw_config: {', '.join(risky_keys)}.")

    return {
        "source_config_id": source_config_id,
        "import_job_id": import_job_id,
        "site_key": site_key,
        "site_name": site_name,
        "site_type": _int_or_none(entry.get("type")),
        "api": api_url,
        "searchable": _bool_or_none(entry.get("searchable")),
        "changeable": _bool_or_none(entry.get("changeable")),
        "quick_search": _bool_or_none(entry.get("quickSearch", entry.get("quick_search"))),
        "filterable": _bool_or_none(entry.get("filterable", entry.get("filter"))),
        "player_type": _int_or_none(entry.get("playerType", entry.get("player_type"))),
        "ext": entry.get("ext"),
        "style": entry.get("style"),
        "categories_hint": entry.get("categories_hint", entry.get("categoriesHint", entry.get("categories"))),
        "raw_config": entry,
        "enabled": True,
        "sort_order": index,
        "analysis_note": " ".join(notes),
    }


async def _upsert_site(db: AsyncSession, values: dict[str, Any]) -> None:
    statement = insert(VodSite).values(**values)
    update_values = {
        key: statement.excluded[key]
        for key in values.keys()
        if key not in {"source_config_id", "site_key"}
    }
    await db.execute(
        statement.on_conflict_do_update(
            index_elements=[VodSite.source_config_id, VodSite.site_key],
            set_=update_values,
        )
    )


async def _disable_missing_sites(db: AsyncSession, source_config_id: uuid.UUID, seen_keys: set[str]) -> None:
    existing = await db.scalars(select(VodSite).where(VodSite.source_config_id == source_config_id))
    for site in existing:
        if site.site_key not in seen_keys:
            site.enabled = False
            site.analysis_note = "Disabled because it was absent from the latest extracted config."


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return None
