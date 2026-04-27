from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import VodCategory
from app.services.source_detection import (
    build_indexed_site_key,
    looks_like_direct_maccms_collector_url,
    normalize_collector_api_url,
)

REQUEST_TIMEOUT_SECONDS = 20.0
IMPORT_HEADERS = {
    "User-Agent": "okhttp/4.10.0",
    "Accept": "*/*",
}


async def list_categories_for_source(
    db: AsyncSession,
    *,
    source_config_id: uuid.UUID,
    site_key: str,
) -> list[VodCategory]:
    result = await db.scalars(
        select(VodCategory)
        .where(
            VodCategory.source_config_id == source_config_id,
            VodCategory.site_key == site_key,
            VodCategory.enabled.is_(True),
        )
        .order_by(VodCategory.sort_order.asc(), VodCategory.type_name.asc())
    )
    return list(result)


async def sync_categories_from_root_config(
    db: AsyncSession,
    *,
    source_config_id: uuid.UUID,
    root_config: dict[str, Any],
    preloaded_categories_by_site_key: dict[str, list[dict[str, Any]]] | None = None,
) -> None:
    sites = root_config.get("sites")
    if not isinstance(sites, list):
        return

    seen_site_keys: set[str] = set()
    for index, item in enumerate(sites):
        if not isinstance(item, dict):
            continue
        ext = item.get("ext")
        ext_api = ext.get("api") if isinstance(ext, dict) else None
        api_url = normalize_collector_api_url(_string_or_none(item.get("api")) or _string_or_none(ext_api))
        site_key = build_indexed_site_key(item.get("key"), api_url)
        if not site_key or not api_url or not looks_like_direct_maccms_collector_url(api_url):
            continue

        seen_site_keys.add(site_key)
        categories = (preloaded_categories_by_site_key or {}).get(site_key)
        if categories is None:
            categories = await _fetch_categories(api_url)
        await _sync_site_categories(
            db,
            source_config_id=source_config_id,
            site_key=site_key,
            categories=categories,
        )

    if seen_site_keys:
        await _disable_missing_site_categories(db, source_config_id=source_config_id, seen_site_keys=seen_site_keys)


async def _fetch_categories(api_url: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS),
    ) as client:
        response = await client.get(_build_url(api_url, {"ac": "list"}), headers=IMPORT_HEADERS)
        response.raise_for_status()
        payload = response.json()

    items = payload.get("class")
    if not isinstance(items, list):
        return []

    categories: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        type_id = _string_or_none(item.get("type_id"))
        type_name = _string_or_none(item.get("type_name"))
        if not type_id or not type_name:
            continue
        categories.append(
            {
                "type_id": type_id,
                "type_name": type_name,
                "parent_type_id": _normalized_parent_type_id(item.get("type_pid", item.get("parent_id", item.get("type_id_1")))),
                "parent_type_name": _string_or_none(item.get("parent_name") or item.get("type_name_1")),
                "sort_order": index,
            }
        )
    return categories


async def _sync_site_categories(
    db: AsyncSession,
    *,
    source_config_id: uuid.UUID,
    site_key: str,
    categories: list[dict[str, Any]],
) -> None:
    seen_type_ids: set[str] = set()

    for index, category in enumerate(categories):
        type_id = _string_or_none(category.get("type_id"))
        type_name = _string_or_none(category.get("type_name"))
        if not type_id or not type_name:
            continue

        parent_type_id = _string_or_none(category.get("parent_type_id"))
        parent_type_name = _string_or_none(category.get("parent_type_name"))
        if parent_type_id == type_id:
            parent_type_id = None
        if parent_type_name == type_name:
            parent_type_name = None

        values = {
            "source_config_id": source_config_id,
            "site_key": site_key,
            "type_id": type_id,
            "type_name": type_name,
            "parent_type_id": parent_type_id,
            "parent_type_name": parent_type_name,
            "sort_order": int(category.get("sort_order", index)),
            "enabled": True,
        }
        seen_type_ids.add(type_id)
        statement = insert(VodCategory).values(**values)
        await db.execute(
            statement.on_conflict_do_update(
                constraint="uq_vod_categories_source_site_type",
                set_={
                    "type_name": statement.excluded.type_name,
                    "parent_type_id": statement.excluded.parent_type_id,
                    "parent_type_name": statement.excluded.parent_type_name,
                    "sort_order": statement.excluded.sort_order,
                    "enabled": statement.excluded.enabled,
                },
            )
        )

    existing = await db.scalars(
        select(VodCategory).where(
            VodCategory.source_config_id == source_config_id,
            VodCategory.site_key == site_key,
        )
    )
    for item in existing:
        if item.type_id not in seen_type_ids:
            item.enabled = False


async def _disable_missing_site_categories(
    db: AsyncSession,
    *,
    source_config_id: uuid.UUID,
    seen_site_keys: set[str],
) -> None:
    existing = await db.scalars(select(VodCategory).where(VodCategory.source_config_id == source_config_id))
    for item in existing:
        if item.site_key not in seen_site_keys:
            item.enabled = False


def _build_url(url: str, updates: dict[str, str | int | None]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in updates.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalized_parent_type_id(value: Any) -> str | None:
    text = _string_or_none(value)
    if text in {None, "0"}:
        return None
    return text
