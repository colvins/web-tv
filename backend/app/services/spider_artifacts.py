import hashlib
import re
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SpiderArtifact, SourceSnapshot, VodSite
from app.services import app_settings

PROBE_TIMEOUT_SECONDS = 15.0
MAX_ARTIFACT_BYTES = 30 * 1024 * 1024
MD5_RE = re.compile(r"^[a-fA-F0-9]{32}$")


async def latest_current_spider_artifact(db: AsyncSession) -> SpiderArtifact | None:
    site = await _current_enabled_site(db)
    if site is None or site.source_config_id is None:
        return None
    return await db.scalar(
        select(SpiderArtifact)
        .where(SpiderArtifact.source_config_id == site.source_config_id)
        .order_by(SpiderArtifact.probed_at.desc().nullslast(), SpiderArtifact.created_at.desc())
        .limit(1)
    )


async def probe_current_spider_artifact(db: AsyncSession) -> SpiderArtifact:
    site = await _current_enabled_site(db)
    if site is None or site.source_config_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No current VOD site selected")

    snapshot = await _latest_snapshot(db, site.source_config_id)
    if snapshot is None or not isinstance(snapshot.root_config, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current source has no stored snapshot")

    artifact_url, expected_md5 = _parse_spider_value(snapshot.root_config.get("spider"))
    if not artifact_url:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Current source snapshot has no spider URL")

    now = datetime.now(UTC)
    values = {
        "source_config_id": site.source_config_id,
        "source_snapshot_id": snapshot.id,
        "artifact_url": artifact_url,
        "expected_md5": expected_md5,
        "probe_status": "pending",
        "probed_at": now,
    }
    artifact = await _upsert_artifact(db, values)

    try:
        metadata = await _download_artifact_metadata(artifact_url)
    except Exception as exc:
        artifact.probe_status = "failed"
        artifact.error_message = str(exc)
        artifact.probed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(artifact)
        return artifact

    artifact.content_type = metadata["content_type"]
    artifact.content_length = metadata["content_length"]
    artifact.sha256 = metadata["sha256"]
    artifact.md5 = metadata["md5"]
    artifact.md5_matches = metadata["md5"] == expected_md5.lower() if expected_md5 else None
    artifact.magic_hex = metadata["magic_hex"]
    artifact.detected_kind = metadata["detected_kind"]
    artifact.probe_status = "success"
    artifact.error_message = None
    artifact.probed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(artifact)
    return artifact


async def _current_enabled_site(db: AsyncSession) -> VodSite | None:
    site = await app_settings.get_current_vod_site(db)
    if site is None or not site.enabled:
        return None
    if site.source_config is None or not site.source_config.enabled:
        return None
    return site


async def _latest_snapshot(db: AsyncSession, source_config_id: uuid.UUID) -> SourceSnapshot | None:
    return await db.scalar(
        select(SourceSnapshot)
        .where(SourceSnapshot.source_config_id == source_config_id)
        .order_by(SourceSnapshot.created_at.desc(), SourceSnapshot.updated_at.desc())
        .limit(1)
    )


async def _upsert_artifact(db: AsyncSession, values: dict) -> SpiderArtifact:
    statement = insert(SpiderArtifact).values(**values)
    result = await db.execute(
        statement.on_conflict_do_update(
            constraint="uq_spider_artifacts_source_url_md5",
            set_={
                "source_snapshot_id": statement.excluded.source_snapshot_id,
                "probe_status": statement.excluded.probe_status,
                "error_message": None,
                "probed_at": statement.excluded.probed_at,
            },
        ).returning(SpiderArtifact)
    )
    await db.commit()
    return result.scalar_one()


def _parse_spider_value(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, None
    parts = [part.strip() for part in value.split(";") if part.strip()]
    if not parts or not parts[0].lower().startswith(("http://", "https://")):
        return None, None
    expected_md5 = None
    for index, part in enumerate(parts):
        if part.lower() == "md5" and index + 1 < len(parts) and MD5_RE.match(parts[index + 1]):
            expected_md5 = parts[index + 1].lower()
            break
        if MD5_RE.match(part):
            expected_md5 = part.lower()
            break
    return parts[0], expected_md5


async def _download_artifact_metadata(url: str) -> dict[str, str | int | None]:
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    chunks: list[bytes] = []
    total = 0
    content_type: str | None = None

    async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(PROBE_TIMEOUT_SECONDS)) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type")
            length = response.headers.get("content-length")
            if length and int(length) > MAX_ARTIFACT_BYTES:
                raise ValueError("Spider artifact exceeds 30MB probe limit")
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > MAX_ARTIFACT_BYTES:
                    raise ValueError("Spider artifact exceeds 30MB probe limit")
                sha256.update(chunk)
                md5.update(chunk)
                chunks.append(chunk)

    content = b"".join(chunks)
    return {
        "content_type": content_type,
        "content_length": total,
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "magic_hex": content[:16].hex(),
        "detected_kind": _detect_kind(content),
    }


def _detect_kind(content: bytes) -> str:
    if content.startswith(b"PK"):
        return "zip_or_jar"
    if content.startswith(b"dex\n"):
        return "dex"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"\x89PNG"):
        return "png"
    if content.startswith(b"\x1f\x8b"):
        return "gzip"

    text = content[:4096].decode("utf-8", errors="replace")
    stripped = text.lstrip("\ufeff\r\n\t ")
    if _readable_ratio(text) >= 0.8:
        if stripped.startswith(("{", "[")):
            return "text_json"
        if any(token in text for token in ("function", "class ", "module.exports", "import ", "export ")):
            return "text_js"
    return "binary_unknown"


def _readable_ratio(text: str) -> float:
    if not text:
        return 0.0
    readable = sum(1 for char in text if char.isprintable() or char in "\r\n\t")
    return readable / len(text)
