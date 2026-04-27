import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportJob, LiveChannel, LiveChannelGroup, SourceSnapshot
from app.services.source_configs import get_source_config

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
SUPPORTED_SNAPSHOT_FORMATS = {"m3u_text"}
PREVIEW_LIMIT = 2048
SEGMENT_PREVIEW_LIMIT = 256
DIAGNOSTIC_TIMEOUT = httpx.Timeout(connect=4.0, read=4.0, write=4.0, pool=4.0)
DIAGNOSTIC_HEADERS = {
    "User-Agent": "web-tv-diagnostics/1.0",
    "Range": f"bytes=0-{PREVIEW_LIMIT - 1}",
}


@dataclass(frozen=True)
class FetchPreview:
    status_code: int
    content_type: str | None
    content_length: int | None
    final_url: str
    final_host: str | None
    redirect_count: int
    preview_bytes: bytes


@dataclass(frozen=True)
class ParsedChannel:
    name: str
    stream_url: str
    tvg_id: str | None
    tvg_name: str | None
    tvg_logo: str | None
    group_title: str | None
    raw_extinf: dict[str, Any]
    sort_order: int


async def extract_live_channels(db: AsyncSession, source_config_id: uuid.UUID) -> dict[str, Any]:
    await get_source_config(db, source_config_id)
    snapshot = await _latest_snapshot(db, source_config_id)
    latest_job = await _latest_successful_import(db, source_config_id)
    if snapshot is None or not isinstance(snapshot.root_config, dict) or snapshot.recovered_format not in SUPPORTED_SNAPSHOT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Latest successful import does not have a stored M3U snapshot; import the source again",
        )

    raw_m3u = snapshot.root_config.get("raw_m3u")
    if not isinstance(raw_m3u, str):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Stored snapshot has no M3U text")

    channels, warnings = parse_m3u(raw_m3u)
    existing_urls = set(
        await db.scalars(select(LiveChannel.stream_url).where(LiveChannel.source_config_id == source_config_id))
    )
    seen_urls = {channel.stream_url for channel in channels}

    groups_by_name = await _upsert_groups(db, source_config_id, channels)
    created_count = 0
    updated_count = 0
    for channel in channels:
        group = groups_by_name.get(channel.group_title or "")
        values = {
            "source_config_id": source_config_id,
            "group_id": group.id if group else None,
            "name": channel.name,
            "tvg_id": channel.tvg_id,
            "tvg_name": channel.tvg_name,
            "tvg_logo": channel.tvg_logo,
            "group_title": channel.group_title,
            "stream_url": channel.stream_url,
            "raw_extinf": channel.raw_extinf,
            "enabled": True,
            "sort_order": channel.sort_order,
        }
        statement = insert(LiveChannel).values(**values)
        await db.execute(
            statement.on_conflict_do_update(
                constraint="uq_live_channels_source_stream",
                set_={key: statement.excluded[key] for key in values if key not in {"source_config_id", "stream_url"}},
            )
        )
        if channel.stream_url in existing_urls:
            updated_count += 1
        else:
            created_count += 1

    disabled_missing_count = 0
    if seen_urls:
        result = await db.execute(
            update(LiveChannel)
            .where(
                LiveChannel.source_config_id == source_config_id,
                LiveChannel.stream_url.not_in(seen_urls),
                LiveChannel.enabled.is_(True),
            )
            .values(enabled=False)
        )
        disabled_missing_count = result.rowcount or 0

    await _refresh_group_counts(db, source_config_id)
    await db.commit()
    return {
        "groups_count": len(groups_by_name),
        "channels_count": len(channels),
        "created_count": created_count,
        "updated_count": updated_count,
        "disabled_missing_count": disabled_missing_count,
        "warnings": warnings
        + [
            "Only the imported M3U source text was parsed; channel stream URLs were not requested.",
            f"Extraction used import job {latest_job.id}.",
        ],
    }


async def list_groups(db: AsyncSession) -> list[LiveChannelGroup]:
    result = await db.scalars(
        select(LiveChannelGroup).order_by(LiveChannelGroup.sort_order.asc(), LiveChannelGroup.name.asc())
    )
    return list(result)


async def list_channels(
    db: AsyncSession,
    group_id: uuid.UUID | None = None,
    q: str | None = None,
) -> list[LiveChannel]:
    statement = select(LiveChannel).order_by(LiveChannel.sort_order.asc(), LiveChannel.name.asc())
    if group_id is not None:
        statement = statement.where(LiveChannel.group_id == group_id)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                LiveChannel.name.ilike(pattern),
                LiveChannel.tvg_name.ilike(pattern),
                LiveChannel.group_title.ilike(pattern),
            )
        )
    result = await db.scalars(statement.limit(500))
    return list(result)


async def update_channel_enabled(db: AsyncSession, channel_id: uuid.UUID, enabled: bool) -> LiveChannel:
    channel = await db.get(LiveChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live channel not found")
    channel.enabled = enabled
    await db.commit()
    await db.refresh(channel)
    return channel


async def diagnose_channel(db: AsyncSession, channel_id: uuid.UUID) -> dict[str, Any]:
    channel = await db.get(LiveChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live channel not found")

    stream_host = _host_for_url(channel.stream_url)
    warnings: list[str] = ["Diagnostics used lightweight preview requests only."]
    m3u8_info: dict[str, Any] | None = None
    sample_segment_check: dict[str, Any] | None = None

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=DIAGNOSTIC_TIMEOUT) as client:
            preview = await _fetch_preview(client, channel.stream_url, PREVIEW_LIMIT)
            stream_type_guess = _guess_stream_type(channel.stream_url, preview.content_type, preview.preview_bytes)
            body_preview = _format_preview(preview.preview_bytes, preview.content_type)

            if stream_type_guess == "hls_m3u8":
                m3u8_info = _inspect_m3u8_preview(preview.preview_bytes, preview.final_url)
                if m3u8_info["preview_text"]:
                    warnings.append("Playlist inspection used a limited text preview.")
                sample_segment_url = m3u8_info.pop("sample_segment_url", None)
                if sample_segment_url:
                    sample_segment_check = await _check_sample_segment(client, sample_segment_url)
                elif m3u8_info["playlist_kind"] == "master":
                    warnings.append("Master playlist preview found; no segment request was made.")

            diagnosis_level, diagnosis_summary, suggested_next_step = _classify_diagnosis(
                http_status=preview.status_code,
                stream_type_guess=stream_type_guess,
                content_type=preview.content_type,
                m3u8_info=m3u8_info,
                sample_segment_check=sample_segment_check,
                playback_failed=True,
            )

            return {
                "channel_id": channel.id,
                "channel_name": channel.name,
                "group_name": channel.group_title,
                "stream_host": stream_host,
                "final_host": preview.final_host,
                "http_status": preview.status_code,
                "content_type": preview.content_type,
                "content_length": preview.content_length,
                "redirect_count": preview.redirect_count,
                "stream_type_guess": stream_type_guess,
                "body_preview": body_preview,
                "m3u8_info": m3u8_info,
                "sample_segment_check": sample_segment_check,
                "diagnosis_level": diagnosis_level,
                "diagnosis_summary": diagnosis_summary,
                "suggested_next_step": suggested_next_step,
                "warnings": warnings,
            }
    except httpx.TimeoutException:
        return _build_failure_diagnosis(
            channel=channel,
            stream_host=stream_host,
            diagnosis_level="upstream_unreachable",
            diagnosis_summary="The upstream stream endpoint timed out during a small preview request.",
            suggested_next_step="Verify the source is reachable from the server and retry the selected channel later.",
            warnings=warnings,
        )
    except httpx.HTTPError as error:
        return _build_failure_diagnosis(
            channel=channel,
            stream_host=stream_host,
            diagnosis_level="upstream_unreachable",
            diagnosis_summary="The server could not reach the upstream stream endpoint.",
            suggested_next_step="Check DNS, network access, or whether the upstream source is offline.",
            warnings=warnings + [str(error)],
        )


async def count_live_channels_by_source(db: AsyncSession) -> dict[uuid.UUID, int]:
    rows = await db.execute(
        select(LiveChannel.source_config_id, func.count(LiveChannel.id))
        .where(LiveChannel.source_config_id.is_not(None))
        .group_by(LiveChannel.source_config_id)
    )
    return {source_id: count for source_id, count in rows if source_id is not None}


async def _fetch_preview(client: httpx.AsyncClient, url: str, max_bytes: int) -> FetchPreview:
    headers = DIAGNOSTIC_HEADERS.copy()
    headers["Range"] = f"bytes=0-{max_bytes - 1}"

    async with client.stream("GET", url, headers=headers) as response:
        preview = bytearray()
        async for chunk in response.aiter_bytes():
            if not chunk:
                continue
            remaining = max_bytes - len(preview)
            preview.extend(chunk[:remaining])
            if len(preview) >= max_bytes:
                break

        return FetchPreview(
            status_code=response.status_code,
            content_type=_normalize_content_type(response.headers.get("content-type")),
            content_length=_parse_content_length(response.headers.get("content-length")),
            final_url=str(response.url),
            final_host=response.url.host,
            redirect_count=len(response.history),
            preview_bytes=bytes(preview),
        )


def _normalize_content_type(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[0].strip().lower() or None


def _parse_content_length(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _host_for_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    return parsed.netloc or None


def _guess_stream_type(url: str, content_type: str | None, preview_bytes: bytes) -> str:
    normalized_url = url.lower()
    preview_text = preview_bytes.decode("utf-8", errors="replace")

    if ".m3u8" in normalized_url or content_type in {
        "application/vnd.apple.mpegurl",
        "application/x-mpegurl",
        "audio/mpegurl",
        "audio/x-mpegurl",
    } or preview_text.lstrip().startswith("#EXTM3U"):
        return "hls_m3u8"
    if ".ts" in normalized_url or content_type in {"video/mp2t", "application/octet-stream"}:
        if preview_bytes[:1] == b"\x47" or ".ts" in normalized_url or content_type == "video/mp2t":
            return "mpeg_ts"
    if ".mp4" in normalized_url or content_type == "video/mp4" or b"ftyp" in preview_bytes[:32]:
        return "mp4"
    if ".flv" in normalized_url or content_type == "video/x-flv" or preview_bytes.startswith(b"FLV"):
        return "flv"
    return "unknown"


def _format_preview(preview_bytes: bytes, content_type: str | None) -> str | None:
    if not preview_bytes:
        return None
    if content_type and any(token in content_type for token in {"mpegurl", "text", "json", "xml"}):
        return preview_bytes.decode("utf-8", errors="replace")[:PREVIEW_LIMIT]
    if preview_bytes[:1] == b"\x47":
        return "47 " + preview_bytes[1:24].hex(" ")
    return preview_bytes[:48].hex(" ")


def _inspect_m3u8_preview(preview_bytes: bytes, base_url: str) -> dict[str, Any]:
    preview_text = preview_bytes.decode("utf-8", errors="replace")[:PREVIEW_LIMIT]
    lines = [line.strip() for line in preview_text.splitlines() if line.strip()]
    uri_lines = [line for line in lines if not line.startswith("#")]
    is_master = any(line.startswith("#EXT-X-STREAM-INF") for line in lines)
    is_media = any(line.startswith("#EXTINF") or line.startswith("#EXT-X-TARGETDURATION") for line in lines)
    segment_candidate = next((line for line in uri_lines if not line.lower().endswith(".m3u8")), None)

    return {
        "playlist_kind": "master" if is_master else "media" if is_media else "unknown",
        "has_media_segments": bool(segment_candidate),
        "sample_segment_path": segment_candidate,
        "sample_segment_url": urljoin(base_url, segment_candidate) if segment_candidate else None,
        "preview_text": preview_text,
    }


async def _check_sample_segment(client: httpx.AsyncClient, segment_url: str) -> dict[str, Any]:
    preview = await _fetch_preview(client, segment_url, SEGMENT_PREVIEW_LIMIT)
    return {
        "status_code": preview.status_code,
        "content_type": preview.content_type,
        "content_length": preview.content_length,
        "final_host": preview.final_host,
        "warning": None if 200 <= preview.status_code < 400 else "Segment preview request did not return success.",
    }


def _classify_diagnosis(
    *,
    http_status: int | None,
    stream_type_guess: str,
    content_type: str | None,
    m3u8_info: dict[str, Any] | None,
    sample_segment_check: dict[str, Any] | None,
    playback_failed: bool,
) -> tuple[str, str, str]:
    if http_status is None:
        return (
            "unknown",
            "The server could not determine an HTTP response from the stream source.",
            "Retry the selected channel and verify the upstream source is still available.",
        )
    if http_status in {401, 403}:
        return (
            "upstream_error",
            f"The upstream server responded with HTTP {http_status}, which suggests authentication or access restrictions.",
            "Verify that the source allows this server and browser to access the stream.",
        )
    if http_status >= 500:
        return (
            "upstream_error",
            f"The upstream server returned HTTP {http_status}.",
            "Retry later or replace the source if the upstream remains unstable.",
        )
    if http_status >= 400:
        return (
            "upstream_error",
            f"The upstream stream URL returned HTTP {http_status}.",
            "Verify the channel URL is still valid in the imported source.",
        )
    if stream_type_guess in {"mpeg_ts", "flv"}:
        return (
            "browser_format_unsupported",
            "The stream looks reachable, but the format is likely not directly supported by the browser player.",
            "Use a browser-friendly HLS or MP4 source for this channel if one is available.",
        )
    if stream_type_guess == "hls_m3u8" and sample_segment_check and (sample_segment_check.get("status_code") or 0) >= 400:
        return (
            "segment_error",
            "The HLS playlist was reachable, but a sample media segment request failed.",
            "Check whether the playlist references expired, blocked, or geo-restricted segment URLs.",
        )
    if stream_type_guess == "hls_m3u8" and m3u8_info and m3u8_info.get("playlist_kind") == "media":
        return (
            "playable_likely",
            "The HLS playlist looks reachable and contains media segments.",
            "If browser playback still fails, check for CORS, codec support, or transient upstream issues.",
        )
    if stream_type_guess == "mp4":
        return (
            "playable_likely",
            "The MP4 stream looks reachable from the server.",
            "If browser playback still fails, check browser codec support or access restrictions on the upstream host.",
        )
    if playback_failed and 200 <= http_status < 400:
        return (
            "cors_or_browser_block_likely",
            "The server could reach the stream, so the failure may be caused by browser access rules, codecs, or player compatibility.",
            "Compare browser console errors with this diagnosis and verify CORS or codec support for the selected stream.",
        )
    return (
        "unknown",
        "The lightweight preview did not produce a confident diagnosis.",
        "Inspect the upstream response manually and compare it with the browser playback error details.",
    )


def _build_failure_diagnosis(
    *,
    channel: LiveChannel,
    stream_host: str | None,
    diagnosis_level: str,
    diagnosis_summary: str,
    suggested_next_step: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "channel_id": channel.id,
        "channel_name": channel.name,
        "group_name": channel.group_title,
        "stream_host": stream_host,
        "final_host": None,
        "http_status": None,
        "content_type": None,
        "content_length": None,
        "redirect_count": 0,
        "stream_type_guess": _guess_stream_type(channel.stream_url, None, b""),
        "body_preview": None,
        "m3u8_info": None,
        "sample_segment_check": None,
        "diagnosis_level": diagnosis_level,
        "diagnosis_summary": diagnosis_summary,
        "suggested_next_step": suggested_next_step,
        "warnings": warnings,
    }


def parse_m3u(text: str) -> tuple[list[ParsedChannel], list[str]]:
    stripped = text.lstrip("\ufeff\r\n\t ")
    if not stripped.startswith("#EXTM3U"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Source is not an M3U playlist")

    channels: list[ParsedChannel] = []
    warnings: list[str] = []
    pending: dict[str, Any] | None = None
    for line in text.splitlines():
        value = line.strip()
        if not value:
            continue
        if value.startswith("#EXTINF"):
            pending = _parse_extinf(value)
            continue
        if value.startswith("#"):
            continue
        if pending is None:
            continue
        if not value.lower().startswith(("http://", "https://")):
            warnings.append(f"Ignored non-http stream URL for {pending['name']}.")
            pending = None
            continue
        channels.append(
            ParsedChannel(
                name=pending["name"],
                stream_url=value,
                tvg_id=pending["attrs"].get("tvg-id") or None,
                tvg_name=pending["attrs"].get("tvg-name") or None,
                tvg_logo=pending["attrs"].get("tvg-logo") or None,
                group_title=pending["attrs"].get("group-title") or None,
                raw_extinf={"line": pending["line"], "attrs": pending["attrs"]},
                sort_order=len(channels),
            )
        )
        pending = None

    if not channels:
        warnings.append("No valid http/https M3U channels were found.")
    return channels, warnings


def _parse_extinf(line: str) -> dict[str, Any]:
    attrs = {match.group(1): match.group(2) for match in ATTR_RE.finditer(line)}
    name = line.rsplit(",", 1)[-1].strip() if "," in line else attrs.get("tvg-name", "Untitled Channel")
    return {"line": line, "attrs": attrs, "name": name or "Untitled Channel"}


async def _latest_snapshot(db: AsyncSession, source_config_id: uuid.UUID) -> SourceSnapshot | None:
    return await db.scalar(
        select(SourceSnapshot)
        .where(SourceSnapshot.source_config_id == source_config_id)
        .order_by(SourceSnapshot.created_at.desc(), SourceSnapshot.updated_at.desc())
        .limit(1)
    )


async def _latest_successful_import(db: AsyncSession, source_config_id: uuid.UUID) -> ImportJob:
    job = await db.scalar(
        select(ImportJob)
        .where(ImportJob.source_config_id == source_config_id, ImportJob.status == "success")
        .order_by(ImportJob.finished_at.desc().nullslast(), ImportJob.created_at.desc())
        .limit(1)
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Source has no successful import job")
    return job


async def _upsert_groups(
    db: AsyncSession,
    source_config_id: uuid.UUID,
    channels: list[ParsedChannel],
) -> dict[str, LiveChannelGroup]:
    group_names = sorted({channel.group_title or "" for channel in channels if channel.group_title})
    for index, group_name in enumerate(group_names):
        statement = insert(LiveChannelGroup).values(
            source_config_id=source_config_id,
            name=group_name,
            sort_order=index,
            channel_count=sum(1 for channel in channels if channel.group_title == group_name),
        )
        await db.execute(
            statement.on_conflict_do_update(
                constraint="uq_live_channel_groups_source_name",
                set_={
                    "sort_order": statement.excluded.sort_order,
                    "channel_count": statement.excluded.channel_count,
                },
            )
        )
    result = await db.scalars(select(LiveChannelGroup).where(LiveChannelGroup.source_config_id == source_config_id))
    return {group.name: group for group in result}


async def _refresh_group_counts(db: AsyncSession, source_config_id: uuid.UUID) -> None:
    groups = await db.scalars(select(LiveChannelGroup).where(LiveChannelGroup.source_config_id == source_config_id))
    for group in groups:
        group.channel_count = await db.scalar(
            select(func.count(LiveChannel.id)).where(
                LiveChannel.source_config_id == source_config_id,
                LiveChannel.group_id == group.id,
            )
        ) or 0
