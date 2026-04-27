from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
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
REAL_PARENT_FIELD_NAMES = (
    "type_pid",
    "parent_id",
    "pid",
    "type_pid_1",
    "type_id_1",
    "parent_type_id",
)
LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class SemanticParentGroup:
    canonical_name: str
    aliases: tuple[str, ...]
    child_names: tuple[str, ...]


SEMANTIC_PARENT_GROUPS: tuple[SemanticParentGroup, ...] = (
    SemanticParentGroup(
        canonical_name="电影",
        aliases=("电影",),
        child_names=(
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
    ),
    SemanticParentGroup(
        canonical_name="电视剧",
        aliases=("电视剧", "连续剧"),
        child_names=(
            "国产剧",
            "欧美剧",
            "韩剧",
            "日剧",
            "港剧",
            "台剧",
            "泰剧",
            "海外剧",
            "Netflix自制剧",
            "台湾剧",
            "韩国剧",
            "香港剧",
            "泰国剧",
            "日本剧",
            "大陆剧",
            "连续剧",
            "电视剧",
        ),
    ),
    SemanticParentGroup(
        canonical_name="综艺",
        aliases=("综艺",),
        child_names=(
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
    ),
    SemanticParentGroup(
        canonical_name="动漫",
        aliases=("动漫",),
        child_names=(
            "国产动漫",
            "日韩动漫",
            "欧美动漫",
            "港台动漫",
            "海外动漫",
            "有声动漫",
            "漫剧",
        ),
    ),
    SemanticParentGroup(
        canonical_name="短剧",
        aliases=("短剧",),
        child_names=(
            "爽文短剧",
            "女频恋爱",
            "反转爽剧",
            "古装仙侠",
            "年代穿越",
            "脑洞悬疑",
            "现代都市",
            "擦边短剧",
        ),
    ),
    SemanticParentGroup(
        canonical_name="伦理",
        aliases=("伦理",),
        child_names=(
            "港台三级",
            "韩国伦理",
            "西方伦理",
            "日本伦理",
            "两性课堂",
            "写真热舞",
        ),
    ),
)

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
        parent_type_id = _extract_parent_type_id(item)
        raw_categories.append(
            {
                "type_id": type_id,
                "type_name": type_name,
                "parent_type_id": parent_type_id,
                "parent_type_name": _string_or_none(
                    item.get("parent_name")
                    or item.get("parent_type_name")
                    or item.get("type_name_1")
                    or item.get("parent")
                ),
                "sort_order": index,
            }
        )

    if _has_native_hierarchy(raw_categories):
        return _finalize_native_categories(raw_categories, names_by_type_id)
    return _apply_semantic_fallback(raw_categories)


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


def _extract_parent_type_id(item: dict[str, Any]) -> str | None:
    for field_name in REAL_PARENT_FIELD_NAMES:
        if field_name not in item:
            continue
        parent_type_id = _normalized_parent_type_id(item.get(field_name))
        if parent_type_id is not None:
            return parent_type_id
    return None


def _has_native_hierarchy(categories: list[dict[str, Any]]) -> bool:
    return any(_string_or_none(category.get("parent_type_id")) for category in categories)


def _finalize_root_categories(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **category,
            "parent_type_id": None,
            "parent_type_name": None,
        }
        for category in categories
    ]


def _semantic_group_by_canonical_name() -> dict[str, SemanticParentGroup]:
    return {group.canonical_name: group for group in SEMANTIC_PARENT_GROUPS}


def _semantic_alias_to_canonical_name() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group in SEMANTIC_PARENT_GROUPS:
        for alias in group.aliases:
            mapping[_normalize_category_name(alias)] = group.canonical_name
    return mapping


def _semantic_child_to_canonical_name() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group in SEMANTIC_PARENT_GROUPS:
        for child_name in group.child_names:
            mapping[_normalize_category_name(child_name)] = group.canonical_name
    return mapping


def _finalize_native_categories(
    categories: list[dict[str, Any]],
    names_by_type_id: dict[str, str],
) -> list[dict[str, Any]]:
    finalized: list[dict[str, Any]] = []
    for category in categories:
        type_id = _string_or_none(category.get("type_id"))
        type_name = _string_or_none(category.get("type_name"))
        parent_type_id = _string_or_none(category.get("parent_type_id"))
        parent_type_name = _string_or_none(category.get("parent_type_name"))

        if parent_type_id == type_id:
            parent_type_id = None
            parent_type_name = None
        elif parent_type_id and parent_type_id not in names_by_type_id:
            LOGGER.warning(
                "VOD category parent id %s was not found in class list; treating %s (%s) as a root leaf",
                parent_type_id,
                type_name,
                type_id,
            )
            parent_type_id = None
            parent_type_name = None
        elif parent_type_id:
            parent_type_name = parent_type_name or names_by_type_id.get(parent_type_id)
        else:
            parent_type_name = None

        finalized.append(
            {
                **category,
                "parent_type_id": parent_type_id,
                "parent_type_name": parent_type_name,
            }
        )
    return finalized


def _apply_semantic_fallback(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not categories:
        return categories

    root_categories = _finalize_root_categories(categories)
    alias_to_canonical = SEMANTIC_ALIAS_TO_CANONICAL_NAME
    child_to_canonical = SEMANTIC_CHILD_TO_CANONICAL_NAME
    canonical_groups = SEMANTIC_GROUP_BY_CANONICAL_NAME
    chosen_parent_by_canonical: dict[str, dict[str, Any]] = {}
    parent_duplicates_to_skip: set[str] = set()

    for category in root_categories:
        type_id = _string_or_none(category.get("type_id"))
        if not type_id:
            continue
        normalized_name = _normalize_category_name(category.get("type_name"))
        canonical_name = alias_to_canonical.get(normalized_name)
        if not canonical_name:
            continue
        existing = chosen_parent_by_canonical.get(canonical_name)
        if existing is None:
            chosen_parent_by_canonical[canonical_name] = category
            continue
        group = canonical_groups[canonical_name]
        preferred_name = _preferred_semantic_parent_name(existing.get("type_name"), category.get("type_name"), group)
        if _string_or_none(category.get("type_name")) == preferred_name:
            existing_type_id = _string_or_none(existing.get("type_id"))
            if existing_type_id:
                parent_duplicates_to_skip.add(existing_type_id)
            chosen_parent_by_canonical[canonical_name] = category
            continue
        parent_duplicates_to_skip.add(type_id)

    assigned_child_count = 0
    updated: list[dict[str, Any]] = []
    for category in root_categories:
        type_id = _string_or_none(category.get("type_id"))
        if type_id and type_id in parent_duplicates_to_skip:
            continue

        normalized_name = _normalize_category_name(category.get("type_name"))
        canonical_name = child_to_canonical.get(normalized_name)
        chosen_parent = chosen_parent_by_canonical.get(canonical_name or "")
        chosen_parent_id = _string_or_none(chosen_parent.get("type_id")) if chosen_parent else None
        is_chosen_parent = bool(chosen_parent_id and chosen_parent_id == type_id)

        if canonical_name and not is_chosen_parent:
            assigned_child_count += 1
            updated.append(
                {
                    **category,
                    "parent_type_id": chosen_parent_id or _synthetic_parent_type_id(canonical_name),
                    "parent_type_name": canonical_name,
                }
            )
            continue

        if canonical_name and chosen_parent and is_chosen_parent:
            updated.append(
                {
                    **category,
                    "type_name": canonical_name,
                }
            )
            continue

        updated.append(category)

    if assigned_child_count == 0:
        return root_categories

    return updated


def _preferred_semantic_parent_name(existing_name: Any, candidate_name: Any, group: SemanticParentGroup) -> str:
    existing = _string_or_none(existing_name) or group.canonical_name
    candidate = _string_or_none(candidate_name) or group.canonical_name
    ordered_names = (group.canonical_name, *group.aliases)
    existing_rank = ordered_names.index(existing) if existing in ordered_names else len(ordered_names)
    candidate_rank = ordered_names.index(candidate) if candidate in ordered_names else len(ordered_names)
    if candidate_rank < existing_rank:
        return candidate
    return existing


def _canonical_parent_name(value: Any) -> str | None:
    normalized = _normalize_category_name(value)
    if not normalized:
        return None
    return SEMANTIC_ALIAS_TO_CANONICAL_NAME.get(normalized)


def _normalize_category_name(value: Any) -> str:
    text = _string_or_none(value)
    if not text:
        return ""
    return "".join(text.replace("/", "").replace("-", "").split()).casefold()


def _synthetic_parent_type_id(parent_name: str) -> str:
    return f"fallback:{_normalize_category_name(parent_name)}"


SEMANTIC_GROUP_BY_CANONICAL_NAME = _semantic_group_by_canonical_name()
SEMANTIC_ALIAS_TO_CANONICAL_NAME = _semantic_alias_to_canonical_name()
SEMANTIC_CHILD_TO_CANONICAL_NAME = _semantic_child_to_canonical_name()
