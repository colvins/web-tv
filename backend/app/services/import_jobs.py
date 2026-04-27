import hashlib
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportJob
from app.services.source_detection import detect_source_content
from app.services.source_configs import get_source_config
from app.services.source_snapshots import store_source_snapshot

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
        result = await _download_source(source_config.url)
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
    source_config.last_import_at = finished_at
    source_config.last_success_at = finished_at
    source_config.last_error = None
    await store_source_snapshot(db, job, result["content"])
    await db.commit()
    await db.refresh(job)
    return job


async def _download_source(url: str) -> dict[str, str | int | float | bytes | None]:
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
    detection = detect_source_content(raw)
    return {
        "content_type": content_type,
        "content_length": total,
        "content_sha256": hasher.hexdigest(),
        "raw_preview": raw_preview,
        "detected_format": detection.detected_format,
        "detection_confidence": detection.detection_confidence,
        "detection_note": detection.detection_note,
        "content": raw,
    }
