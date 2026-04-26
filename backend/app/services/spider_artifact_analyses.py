import hashlib
import io
import posixpath
import zipfile

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SpiderArtifact, SpiderArtifactAnalysis, VodSite
from app.services import app_settings
from app.services.spider_artifacts import MAX_ARTIFACT_BYTES, PROBE_TIMEOUT_SECONDS

SUSPICIOUS_ENTRY_BYTES = 20 * 1024 * 1024


async def latest_current_entry_analysis(db: AsyncSession) -> SpiderArtifactAnalysis | None:
    site = await _current_enabled_site(db)
    if site is None or site.source_config_id is None:
        return None
    return await db.scalar(
        select(SpiderArtifactAnalysis)
        .where(SpiderArtifactAnalysis.source_config_id == site.source_config_id)
        .order_by(SpiderArtifactAnalysis.created_at.desc())
        .limit(1)
    )


async def analyze_current_artifact_entries(db: AsyncSession) -> SpiderArtifactAnalysis | None:
    site = await _current_enabled_site(db)
    if site is None or site.source_config_id is None:
        return None

    artifact = await _latest_successful_artifact(db, site.source_config_id)
    if artifact is None:
        return None

    try:
        content = await _download_artifact(artifact.artifact_url)
        if artifact.expected_md5:
            actual_md5 = hashlib.md5(content, usedforsecurity=False).hexdigest()
            if actual_md5 != artifact.expected_md5.lower():
                raise ValueError("Spider artifact MD5 no longer matches expected hash")
        values = _analyze_zip_entries(artifact, site, content)
    except Exception as exc:
        values = _failed_values(artifact, str(exc))

    analysis = SpiderArtifactAnalysis(**values)
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def _current_enabled_site(db: AsyncSession) -> VodSite | None:
    site = await app_settings.get_current_vod_site(db)
    if site is None or not site.enabled:
        return None
    if site.source_config is None or not site.source_config.enabled:
        return None
    return site


async def _latest_successful_artifact(db: AsyncSession, source_config_id) -> SpiderArtifact | None:
    return await db.scalar(
        select(SpiderArtifact)
        .where(SpiderArtifact.source_config_id == source_config_id, SpiderArtifact.probe_status == "success")
        .order_by(SpiderArtifact.probed_at.desc().nullslast(), SpiderArtifact.created_at.desc())
        .limit(1)
    )


async def _download_artifact(url: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(PROBE_TIMEOUT_SECONDS)) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            length = response.headers.get("content-length")
            if length and int(length) > MAX_ARTIFACT_BYTES:
                raise ValueError("Spider artifact exceeds 30MB analysis limit")
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > MAX_ARTIFACT_BYTES:
                    raise ValueError("Spider artifact exceeds 30MB analysis limit")
                chunks.append(chunk)
    return b"".join(chunks)


def _analyze_zip_entries(artifact: SpiderArtifact, site: VodSite, content: bytes) -> dict:
    api_terms = _api_terms(site.api)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        extension_counts: dict[str, int] = {}
        top_level_dirs: set[str] = set()
        matching_api_entries: list[str] = []
        total_compressed = 0
        total_uncompressed = 0
        suspicious_large_entries = 0

        for entry in entries:
            normalized = entry.filename.strip("/")
            total_compressed += entry.compress_size
            total_uncompressed += entry.file_size
            if entry.file_size > SUSPICIOUS_ENTRY_BYTES:
                suspicious_large_entries += 1
            first_part = normalized.split("/", 1)[0]
            if "/" in normalized and first_part:
                top_level_dirs.add(first_part)
            if not entry.is_dir():
                extension = posixpath.splitext(normalized)[1].lower().lstrip(".") or "[none]"
                extension_counts[extension] = extension_counts.get(extension, 0) + 1
            lowered = normalized.lower()
            if api_terms and any(term in lowered for term in api_terms):
                matching_api_entries.append(normalized)

    lowered_names = [name.lower() for name in names]
    return {
        "spider_artifact_id": artifact.id,
        "source_config_id": artifact.source_config_id,
        "source_snapshot_id": artifact.source_snapshot_id,
        "analysis_status": "success",
        "error_message": None,
        "total_entries": len(entries),
        "total_compressed_size": total_compressed,
        "total_uncompressed_size": total_uncompressed,
        "top_level_dirs": sorted(top_level_dirs)[:100],
        "extension_counts": dict(sorted(extension_counts.items())),
        "matching_api_entries": matching_api_entries[:100],
        "sample_entries": names[:100],
        "has_class": any(name.endswith(".class") for name in lowered_names),
        "has_dex": any(name.endswith(".dex") for name in lowered_names),
        "has_js": any(name.endswith(".js") for name in lowered_names),
        "has_json": any(name.endswith(".json") for name in lowered_names),
        "has_assets": any(name.startswith("assets/") or "/assets/" in name for name in lowered_names),
        "has_catvod_package": any("com/github/catvod" in name or "catvod" in name for name in lowered_names),
        "suspicious_large_entries": suspicious_large_entries,
    }


def _failed_values(artifact: SpiderArtifact, error_message: str) -> dict:
    return {
        "spider_artifact_id": artifact.id,
        "source_config_id": artifact.source_config_id,
        "source_snapshot_id": artifact.source_snapshot_id,
        "analysis_status": "failed",
        "error_message": error_message,
        "top_level_dirs": [],
        "extension_counts": {},
        "matching_api_entries": [],
        "sample_entries": [],
        "has_class": False,
        "has_dex": False,
        "has_js": False,
        "has_json": False,
        "has_assets": False,
        "has_catvod_package": False,
        "suspicious_large_entries": 0,
    }


def _api_terms(api: str | None) -> list[str]:
    if not api:
        return []
    lowered = api.lower()
    terms = {lowered}
    if lowered.startswith("csp_"):
        terms.add(lowered.removeprefix("csp_"))
    return sorted(term for term in terms if term)
