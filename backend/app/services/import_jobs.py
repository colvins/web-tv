import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportJob
from app.services.source_detection import (
    build_direct_collector_root_config,
    detect_source_content,
    looks_like_direct_maccms_collector_url,
    looks_like_maccms_collector_payload,
    recover_json_config,
)
from app.services.source_configs import get_source_config
from app.services.source_snapshots import store_source_snapshot_with_overrides
from app.services.vod_categories import sync_categories_from_root_config

MAX_IMPORT_BYTES = 5 * 1024 * 1024
RAW_PREVIEW_CHARS = 2000
REQUEST_TIMEOUT_SECONDS = 20.0
IMPORT_HEADERS = {
    "User-Agent": "okhttp/4.10.0",
    "Accept": "*/*",
}


async def list_import_jobs(db: AsyncSession) -> list[ImportJob]:
    result = await db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc()))
    return list(result)


async def get_import_job(db: AsyncSession, job_id: uuid.UUID) -> ImportJob:
    job = await db.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return job


async def import_source_config(db: AsyncSession, source_config_id: uuid.UUID) -> ImportJob:
    source_config = await get_source_config(db, source_config_id)
    job = ImportJob(
        source_config_id=source_config.id,
        status="pending",
        source_url=source_config.url,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    now = datetime.now(UTC)
    job.status = "running"
    job.started_at = now
    source_config.last_import_at = now
    source_config.last_error = None
    await db.commit()

    try:
        result = await _download_source(source_config.name, source_config.url)
    except Exception as exc:
        finished_at = datetime.now(UTC)
        message = str(exc)
        job.status = "failed"
        job.error_message = message
        job.finished_at = finished_at
        source_config.last_import_at = finished_at
        source_config.last_error = message
        await db.commit()
        await db.refresh(job)
        return job

    finished_at = datetime.now(UTC)
    job.status = "success"
    job.content_type = result["content_type"]
    job.content_length = result["content_length"]
    job.content_sha256 = result["content_sha256"]
    job.raw_preview = result["raw_preview"]
    job.detected_format = result["detected_format"]
    job.detection_confidence = result["detection_confidence"]
    job.detection_note = result["detection_note"]
    job.finished_at = finished_at
    source_config.source_type = _detected_source_type(result["detected_format"])
    source_config.last_import_at = finished_at
    source_config.last_success_at = finished_at
    source_config.last_error = None
    await store_source_snapshot_with_overrides(
        db,
        job,
        result["content"],
        root_config_override=result["root_config_override"],
        recovered_format_override=result["recovered_format_override"],
        extra_warnings=result["snapshot_warnings"],
    )
    snapshot_root_config = result["root_config_override"]
    if snapshot_root_config is None:
        recovered = recover_json_config(result["content"])
        snapshot_root_config = recovered if isinstance(recovered, dict) else None
    if isinstance(snapshot_root_config, dict):
        from app.services.vod_sites import sync_sites_from_root_config

        await sync_sites_from_root_config(
            db,
            source_config_id=source_config.id,
            import_job_id=job.id,
            root_config=snapshot_root_config,
        )
        await sync_categories_from_root_config(
            db,
            source_config_id=source_config.id,
            root_config=snapshot_root_config,
            preloaded_categories_by_site_key=result["categories_by_site_key"],
        )
    await db.commit()
    await db.refresh(job)
    return job


async def _download_source(
    source_name: str,
    url: str,
) -> dict[str, str | int | float | bytes | list[str] | dict[str, Any] | None]:
    hasher = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0

    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        async with client.stream("GET", url, headers=IMPORT_HEADERS) as response:
            response.raise_for_status()
            content_length_header = response.headers.get("content-length")
            if content_length_header and int(content_length_header) > MAX_IMPORT_BYTES:
                raise ValueError("Source response exceeds 5MB limit")

            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > MAX_IMPORT_BYTES:
                    raise ValueError("Source response exceeds 5MB limit")
                hasher.update(chunk)
                chunks.append(chunk)

            content_type = response.headers.get("content-type")

    raw = b"".join(chunks)
    raw_preview = raw.decode("utf-8", errors="replace").replace("\x00", "\uFFFD")[:RAW_PREVIEW_CHARS]
    detection = detect_source_content(raw, source_url=url)
    root_config_override: dict[str, Any] | None = None
    recovered_format_override: str | None = None
    snapshot_warnings: list[str] = []
    detection_note = detection.detection_note
    categories_by_site_key: dict[str, list[dict[str, Any]]] = {}

    collector_probe = await _probe_direct_collector(source_name, url, raw)
    if collector_probe is not None:
        root_config_override = collector_probe["root_config"]
        recovered_format_override = "direct_maccms_collector"
        detection_note = collector_probe["detection_note"]
        categories_by_site_key = collector_probe["categories_by_site_key"]
        snapshot_warnings.append("Direct MacCMS-style collector URL was normalized into a synthetic sites[] root_config.")

    return {
        "content_type": content_type,
        "content_length": total,
        "content_sha256": hasher.hexdigest(),
        "raw_preview": raw_preview,
        "detected_format": detection.detected_format,
        "detection_confidence": detection.detection_confidence,
        "detection_note": detection_note,
        "content": raw,
        "root_config_override": root_config_override,
        "recovered_format_override": recovered_format_override,
        "snapshot_warnings": snapshot_warnings,
        "categories_by_site_key": categories_by_site_key,
    }


async def _probe_direct_collector(
    source_name: str,
    source_url: str,
    raw_content: bytes,
) -> dict[str, Any] | None:
    payload = _parse_json_like(raw_content)
    if not looks_like_direct_maccms_collector_url(source_url) and not looks_like_maccms_collector_payload(payload):
        return None

    metadata = await _fetch_metadata_json(_build_metadata_url(source_url, {"ac": "list", "pg": 1}))
    if not looks_like_maccms_collector_payload(metadata):
        raise ValueError("URL matches a VOD collector pattern, but ac=list did not return MacCMS-style metadata.")

    category_samples = _category_samples(metadata)
    root_config = build_direct_collector_root_config(
        source_name=source_name,
        source_url=source_url,
        category_samples=category_samples,
    )
    site_key = str(root_config["sites"][0]["key"])
    note = "Direct MacCMS-style VOD collector detected and validated with ac=list metadata only."
    if category_samples:
        note = f"{note} Sample categories: {', '.join(category_samples[:5])}."
    return {
        "root_config": root_config,
        "detection_note": note,
        "categories_by_site_key": {
            site_key: _categories_from_metadata(metadata),
        },
    }


async def _fetch_metadata_json(url: str) -> dict[str, Any]:
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        response = await client.get(url, headers=IMPORT_HEADERS)
        response.raise_for_status()

    payload = _parse_json_like(response.content)
    if not isinstance(payload, dict):
        raise ValueError("Metadata probe did not return a JSON object.")
    return payload


def _parse_json_like(content: bytes) -> Any | None:
    text = content.decode("utf-8", errors="replace").replace("\x00", "\uFFFD").lstrip("\ufeff\r\n\t ")
    if not text.startswith(("{", "[")):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _build_metadata_url(url: str, updates: dict[str, str | int | None]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in updates.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _category_samples(payload: dict[str, Any]) -> list[str]:
    categories = payload.get("class")
    if not isinstance(categories, list):
        return []

    samples: list[str] = []
    for item in categories[:8]:
        if not isinstance(item, dict):
            continue
        type_name = item.get("type_name")
        if type_name is None:
            continue
        text = str(type_name).strip()
        if text:
            samples.append(text)
    return samples


def _categories_from_metadata(payload: dict[str, Any]) -> list[dict[str, Any]]:
    categories = payload.get("class")
    if not isinstance(categories, list):
        return []

    parsed: list[dict[str, Any]] = []
    for index, item in enumerate(categories):
        if not isinstance(item, dict):
            continue
        type_id = _string_or_none(item.get("type_id"))
        type_name = _string_or_none(item.get("type_name"))
        if not type_id or not type_name:
            continue
        parsed.append(
            {
                "type_id": type_id,
                "type_name": type_name,
                "parent_type_id": _normalized_parent_type_id(item.get("type_pid", item.get("parent_id", item.get("type_id_1")))),
                "parent_type_name": _string_or_none(item.get("parent_name") or item.get("type_name_1")),
                "sort_order": index,
            }
        )
    return parsed


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


def _detected_source_type(detected_format: str | None) -> str:
    if detected_format in {"m3u"}:
        return "m3u"
    if detected_format == "txt":
        return "txt"
    return "json"
