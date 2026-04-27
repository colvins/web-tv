from __future__ import annotations

import html
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import VodSite
from app.services.source_detection import looks_like_direct_maccms_collector_url
from app.services.source_configs import get_source_config
from app.services.vod_categories import list_categories_for_source

REQUEST_TIMEOUT_SECONDS = 10
HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class CollectorSiteCandidate:
    source_config_id: uuid.UUID
    source_name: str
    site_key: str | None
    site_name: str | None
    api_url: str


async def list_categories(
    db: AsyncSession,
    source_config_id: uuid.UUID,
    site_key: str | None,
) -> dict[str, Any]:
    candidate = await _resolve_candidate_site(db, source_config_id, site_key)
    stored_categories = await list_categories_for_source(
        db,
        source_config_id=source_config_id,
        site_key=candidate.site_key or "",
    )
    categories = _category_rows(stored_categories)
    return {
        "site": _serialize_site(candidate),
        "categories": categories,
        "reason": None if categories else "No stored VOD categories are available for this source yet. Re-import the source to sync category metadata.",
    }


async def list_vods(
    db: AsyncSession,
    source_config_id: uuid.UUID,
    site_key: str | None,
    type_id: str | None,
    page: int,
) -> dict[str, Any]:
    candidate = await _resolve_candidate_site(db, source_config_id, site_key)
    params: dict[str, str | int | None] = {"ac": "list", "pg": page}
    if type_id:
        params["t"] = type_id
    payload = await _fetch_json(_build_url(candidate.api_url, params))
    payload = await _fill_missing_posters(candidate, payload)
    return _catalog_page(candidate, payload)


async def search_vods(
    db: AsyncSession,
    source_config_id: uuid.UUID,
    site_key: str | None,
    query: str,
    page: int,
) -> dict[str, Any]:
    text = query.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Search query cannot be empty")

    candidate = await _resolve_candidate_site(db, source_config_id, site_key)
    payload = await _fetch_json(_build_url(candidate.api_url, {"ac": "list", "wd": text, "pg": page}))
    payload = await _fill_missing_posters(candidate, payload)
    return _catalog_page(candidate, payload)


async def get_vod_detail(
    db: AsyncSession,
    source_config_id: uuid.UUID,
    site_key: str | None,
    vod_id: str,
) -> dict[str, Any]:
    text = vod_id.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="vod_id cannot be empty")

    candidate = await _resolve_candidate_site(db, source_config_id, site_key)
    payload = await _fetch_json(_build_url(candidate.api_url, {"ac": "detail", "ids": text}))
    return _catalog_detail(candidate, _select_detail_item(payload, text))


async def get_episode_play(
    db: AsyncSession,
    source_config_id: uuid.UUID,
    site_key: str | None,
    vod_id: str,
    source_name: str,
    episode_index: int,
) -> dict[str, Any]:
    text = vod_id.strip()
    selected_source = source_name.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="vod_id cannot be empty")
    if not selected_source:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source_name cannot be empty")
    if episode_index < 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="episode_index must be >= 0")

    candidate = await _resolve_candidate_site(db, source_config_id, site_key)
    payload = await _fetch_json(_build_url(candidate.api_url, {"ac": "detail", "ids": text}))
    item = _select_detail_item(payload, text)
    play_groups = _play_source_groups(item)

    group = next((entry for entry in play_groups if entry["source_name"] == selected_source), None)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requested play source was not found")

    episodes = group["episodes"]
    if episode_index >= len(episodes):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requested episode index was not found")

    episode = episodes[episode_index]
    stream_url = episode["stream_url"]
    parsed = urlparse(stream_url)
    guess = _stream_type_guess(stream_url)
    return {
        "vod_id": item.get("vod_id"),
        "source_name": selected_source,
        "episode_index": episode_index,
        "episode_name": episode["episode_name"],
        "stream_url": stream_url,
        "stream_host": parsed.netloc or None,
        "stream_type_guess": guess,
        "is_hls_like": guess == "hls_m3u8",
        "is_direct_file_like": guess in {"mp4", "mkv", "webm", "mov", "m4v", "direct_file"},
    }


async def _resolve_candidate_site(
    db: AsyncSession,
    source_config_id: uuid.UUID,
    site_key: str | None,
) -> CollectorSiteCandidate:
    source_config = await get_source_config(db, source_config_id)
    if not source_config.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Source config must be enabled for VOD browsing")

    rows = await db.scalars(
        select(VodSite)
        .where(
            VodSite.source_config_id == source_config_id,
            VodSite.enabled.is_(True),
        )
        .order_by(VodSite.sort_order.asc(), VodSite.site_name.asc())
    )
    for site in rows:
        if site_key and site.site_key != site_key:
            continue
        api_url = _http_url(site.api)
        if not api_url or not looks_like_direct_maccms_collector_url(api_url):
            continue
        return CollectorSiteCandidate(
            source_config_id=source_config.id,
            source_name=source_config.name,
            site_key=site.site_key,
            site_name=site.site_name,
            api_url=api_url,
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No enabled indexed VOD collector site is synced for this source.",
    )


async def _fetch_json(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS),
        ) as client:
            response = await client.get(url, headers={"User-Agent": "web-tv-vod-browser/1.0"})
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream VOD collector request failed: {exc}",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream VOD collector returned HTTP {response.status_code}",
        )

    payload = _parse_json_body(response.content)
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream VOD collector response was not a JSON object",
        )
    return payload


def _parse_json_body(content: bytes) -> Any:
    text = content.decode("utf-8", errors="replace")
    stripped = text.lstrip("\ufeff\r\n\t ")
    if not stripped.startswith(("{", "[")):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream VOD collector did not return JSON content",
        )
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream VOD collector returned malformed JSON: {exc.msg}",
        ) from exc


def _build_url(url: str, updates: dict[str, str | int | None]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in updates.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _catalog_page(candidate: CollectorSiteCandidate, payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("list")
    if not isinstance(items, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream VOD collector JSON had no list array",
        )

    return {
        "site": _serialize_site(candidate),
        "page": _int_value(payload.get("page"), default=1),
        "pagecount": _int_value(payload.get("pagecount"), default=1),
        "total": _int_value(payload.get("total"), default=len(items)),
        "limit": _int_value(payload.get("limit")),
        "items": [_catalog_item(candidate, item) for item in items if isinstance(item, dict)],
    }


def _catalog_item(candidate: CollectorSiteCandidate, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "vod_id": item.get("vod_id"),
        "name": _string_or_none(item.get("vod_name")) or "Untitled",
        "category_id": item.get("type_id"),
        "category_name": _string_or_none(item.get("type_name")),
        "poster": _normalize_media_url(item.get("vod_pic"), candidate.api_url),
        "year": _string_or_none(item.get("vod_year")),
        "area": _string_or_none(item.get("vod_area")),
        "remarks": _string_or_none(item.get("vod_remarks") or item.get("vod_remark")),
    }


def _catalog_detail(candidate: CollectorSiteCandidate, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "site": _serialize_site(candidate),
        "vod_id": item.get("vod_id"),
        "name": _string_or_none(item.get("vod_name")) or "Untitled",
        "category_id": item.get("type_id"),
        "category_name": _string_or_none(item.get("type_name")),
        "poster": _normalize_media_url(item.get("vod_pic"), candidate.api_url),
        "year": _string_or_none(item.get("vod_year")),
        "area": _string_or_none(item.get("vod_area")),
        "language": _string_or_none(item.get("vod_lang")),
        "remarks": _string_or_none(item.get("vod_remarks") or item.get("vod_remark")),
        "actor": _string_or_none(item.get("vod_actor")),
        "director": _string_or_none(item.get("vod_director")),
        "description": _description(item),
        "play_sources": _play_sources_summary(item),
    }


def _serialize_site(candidate: CollectorSiteCandidate) -> dict[str, Any]:
    parsed = urlparse(candidate.api_url)
    return {
        "source_config_id": candidate.source_config_id,
        "source_name": candidate.source_name,
        "site_key": candidate.site_key,
        "site_name": candidate.site_name,
        "api_host": parsed.netloc or None,
        "api_path": parsed.path or None,
        "api_query_keys": sorted({key for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}),
    }


def _play_sources_summary(item: dict[str, Any]) -> list[dict[str, Any]]:
    groups = _play_source_groups(item)
    summaries: list[dict[str, Any]] = []
    for group in groups:
        episode_names = [episode["episode_name"] for episode in group["episodes"]]
        summaries.append(
            {
                "source_name": group["source_name"],
                "episode_count": len(episode_names),
                "episode_names": episode_names,
                "sample_episode_names": episode_names[:8],
                "has_play_urls": any(bool(episode["stream_url"]) for episode in group["episodes"]),
            }
        )
    return summaries


def _category_rows(categories: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    all_type_ids = {str(category.type_id) for category in categories if category.type_id is not None}
    synthetic_parents: list[dict[str, Any]] = []
    synthetic_parent_ids: set[str] = set()

    for category in categories:
        rows.append(
            {
                "type_id": category.type_id,
                "type_name": category.type_name,
                "parent_type_id": category.parent_type_id,
                "parent_type_name": category.parent_type_name,
                "has_content": True,
            }
        )

        parent_type_id = _string_or_none(category.parent_type_id)
        parent_type_name = _string_or_none(category.parent_type_name)
        if not parent_type_id or not parent_type_name:
            continue
        if parent_type_id in all_type_ids or parent_type_id in synthetic_parent_ids:
            continue
        synthetic_parent_ids.add(parent_type_id)
        synthetic_parents.append(
            {
                "type_id": parent_type_id,
                "type_name": parent_type_name,
                "parent_type_id": None,
                "parent_type_name": None,
                "has_content": True,
            }
        )

    return [*synthetic_parents, *rows]


def _split_sources(value: Any) -> list[str]:
    text = _string_or_none(value)
    if not text:
        return []
    return [segment.strip() for segment in text.split("$$$")]


def _parse_episode_entries(value: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for segment in value.split("#"):
        part = segment.strip()
        if not part:
            continue
        if "$" in part:
            name, url = part.split("$", 1)
            episode_name = name.strip() or f"Episode {len(entries) + 1}"
            stream_url = url.strip()
        else:
            episode_name = part
            stream_url = ""
        if not episode_name:
            episode_name = f"Episode {len(entries) + 1}"
        entries.append(
            {
                "episode_name": episode_name[:80],
                "stream_url": stream_url,
            }
        )
    return entries


def _play_source_groups(item: dict[str, Any]) -> list[dict[str, Any]]:
    source_names = _split_sources(item.get("vod_play_from"))
    source_payloads = _split_sources(item.get("vod_play_url"))
    count = max(len(source_names), len(source_payloads))
    groups: list[dict[str, Any]] = []
    for index in range(count):
        source_name = source_names[index] if index < len(source_names) and source_names[index] else f"Source {index + 1}"
        payload = source_payloads[index] if index < len(source_payloads) else ""
        groups.append(
            {
                "source_name": source_name,
                "episodes": _parse_episode_entries(payload),
            }
        )
    return groups


def _description(item: dict[str, Any]) -> str | None:
    text = _string_or_none(item.get("vod_content")) or _string_or_none(item.get("vod_blurb"))
    if not text:
        return None
    plain = HTML_TAG_RE.sub(" ", html.unescape(text.replace("&nbsp;", " ")))
    compact = " ".join(plain.split())
    return compact[:1200] if len(compact) > 1200 else compact


def _select_detail_item(payload: dict[str, Any], vod_id: str) -> dict[str, Any]:
    items = payload.get("list")
    if not isinstance(items, list) or not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VOD detail was not found in the upstream collector response",
        )

    selected = next(
        (
            item
            for item in items
            if isinstance(item, dict) and str(item.get("vod_id")) == vod_id
        ),
        None,
    )
    if not isinstance(selected, dict):
        selected = next((item for item in items if isinstance(item, dict)), None)
    if not isinstance(selected, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream VOD collector detail response did not contain a usable item",
        )
    return selected


def _stream_type_guess(stream_url: str) -> str:
    lowered = stream_url.lower()
    parsed = urlparse(stream_url)
    path = parsed.path.lower()
    if ".m3u8" in lowered or path.endswith(".m3u8"):
        return "hls_m3u8"
    for ext in (".mp4", ".mkv", ".webm", ".mov", ".m4v"):
        if path.endswith(ext):
            return ext.removeprefix(".")
    if path.endswith(".ts"):
        return "ts"
    if path.endswith(".mp3"):
        return "mp3"
    if parsed.scheme in {"http", "https"}:
        return "direct_file"
    return "unknown"


def _http_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    lowered = value.lower()
    if lowered.startswith(("http://", "https://")):
        return value
    return None


def _normalize_media_url(value: Any, base_url: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith(("http://", "https://")):
        return text
    if text.startswith("//"):
        return f"https:{text}"
    if base_url:
        return urljoin(base_url, text)
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_value(value: Any, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def _fill_missing_posters(candidate: CollectorSiteCandidate, payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("list")
    if not isinstance(items, list):
        return payload

    missing_ids = [
        str(item.get("vod_id"))
        for item in items
        if isinstance(item, dict)
        and item.get("vod_id") not in (None, "")
        and not _normalize_media_url(item.get("vod_pic"), candidate.api_url)
    ]
    if not missing_ids:
        return payload

    detail_payload = await _fetch_json(_build_url(candidate.api_url, {"ac": "detail", "ids": ",".join(missing_ids)}))
    detail_items = detail_payload.get("list")
    if not isinstance(detail_items, list):
        return payload

    posters_by_id = {
        str(item.get("vod_id")): _normalize_media_url(item.get("vod_pic"), candidate.api_url)
        for item in detail_items
        if isinstance(item, dict) and item.get("vod_id") not in (None, "")
    }
    for item in items:
        if not isinstance(item, dict):
            continue
        vod_id = item.get("vod_id")
        if vod_id in (None, "") or _normalize_media_url(item.get("vod_pic"), candidate.api_url):
            continue
        poster = posters_by_id.get(str(vod_id))
        if poster:
            item["vod_pic"] = poster
    return payload
