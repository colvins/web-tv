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

FALLBACK_PARENT_GROUPS: dict[str, tuple[str, ...]] = {
    "电影": (
        "动作片",
        "喜剧片",
        "爱情片",
        "科幻片",
        "恐怖片",
        "剧情片",
        "战争片",
        "纪录片",
        "动画片",
        "4K电影",
        "邵氏电影",
        "Netflix电影",
    ),
    "电视剧": (
        "国产剧",
        "欧美剧",
        "韩剧",
        "日剧",
        "港剧",
        "台剧",
        "泰剧",
        "海外剧",
        "Netflix自制剧",
    ),
    "综艺": (
        "大陆综艺",
        "日韩综艺",
        "港台综艺",
        "欧美综艺",
        "演唱会",
        "体育赛事",
        "篮球",
        "足球",
        "斯诺克",
    ),
    "动漫": (
        "国产动漫",
        "日韩动漫",
        "欧美动漫",
        "港台动漫",
        "海外动漫",
        "有声动漫",
        "漫剧",
    ),
    "短剧": (
        "爽文短剧",
        "女频恋爱",
        "反转爽剧",
        "古装仙侠",
        "年代穿越",
        "脑洞悬疑",
        "现代都市",
        "擦边短剧",
    ),
    "伦理": (
        "港台三级",
        "韩国伦理",
        "西方伦理",
        "日本伦理",
        "两性课堂",
        "写真热舞",
    ),
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

    return parse_categories_payload(payload)


def parse_categories_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("class")
    if not isinstance(items, list):
        return []

    raw_categories: list[dict[str, Any]] = []
    names_by_type_id: dict[str, str] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        type_id = _string_or_none(item.get("type_id"))
        type_name = _string_or_none(item.get("type_name"))
        if not type_id or not type_name:
            continue
        names_by_type_id[type_id] = type_name
        raw_categories.append(
            {
                "type_id": type_id,
                "type_name": type_name,
                "parent_type_id": _normalized_parent_type_id(
                    item.get("type_pid", item.get("parent_id", item.get("pid", item.get("type_pid_1", item.get("type_id_1")))))
                ),
                "parent_type_name": _string_or_none(
                    item.get("parent_name")
                    or item.get("parent_type_name")
                    or item.get("type_name_1")
                    or item.get("parent")
                ),
                "sort_order": index,
            }
        )

    categories: list[dict[str, Any]] = []
    has_real_parent_structure = False
    for category in raw_categories:
        parent_type_id = _string_or_none(category.get("parent_type_id"))
        parent_type_name = _string_or_none(category.get("parent_type_name")) or names_by_type_id.get(parent_type_id or "")
        if parent_type_id or parent_type_name:
            has_real_parent_structure = True
        categories.append(
            {
                **category,
                "parent_type_name": parent_type_name,
            }
        )

    if has_real_parent_structure:
        return categories
    return _apply_name_based_parent_fallback(categories)


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


def _apply_name_based_parent_fallback(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not categories:
        return categories

    canonical_parent_ids: dict[str, str] = {}
    for category in categories:
        type_id = _string_or_none(category.get("type_id"))
        canonical_name = _canonical_parent_name(category.get("type_name"))
        if type_id and canonical_name and canonical_name not in canonical_parent_ids:
            canonical_parent_ids[canonical_name] = type_id

    updated: list[dict[str, Any]] = []
    for category in categories:
        if _string_or_none(category.get("parent_type_id")) or _string_or_none(category.get("parent_type_name")):
            updated.append(category)
            continue

        parent_name = FALLBACK_CHILD_TO_PARENT.get(_normalize_category_name(category.get("type_name")))
        if not parent_name:
            updated.append(category)
            continue

        updated.append(
            {
                **category,
                "parent_type_id": canonical_parent_ids.get(parent_name, _synthetic_parent_type_id(parent_name)),
                "parent_type_name": parent_name,
            }
        )
    return updated


def _canonical_parent_name(value: Any) -> str | None:
    normalized = _normalize_category_name(value)
    if not normalized:
        return None
    for parent_name in FALLBACK_PARENT_GROUPS:
        if normalized == _normalize_category_name(parent_name):
            return parent_name
    return None


def _normalize_category_name(value: Any) -> str:
    text = _string_or_none(value)
    if not text:
        return ""
    return "".join(text.replace("/", "").replace("-", "").split()).casefold()


def _synthetic_parent_type_id(parent_name: str) -> str:
    return f"fallback:{_normalize_category_name(parent_name)}"


FALLBACK_CHILD_TO_PARENT = {
    _normalize_category_name(child_name): parent_name
    for parent_name, child_names in FALLBACK_PARENT_GROUPS.items()
    for child_name in child_names
}
