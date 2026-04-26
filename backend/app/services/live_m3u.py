import re
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportJob, LiveChannel, LiveChannelGroup, SourceSnapshot
from app.services.source_configs import get_source_config

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
SUPPORTED_SNAPSHOT_FORMATS = {"m3u_text"}


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


async def count_live_channels_by_source(db: AsyncSession) -> dict[uuid.UUID, int]:
    rows = await db.execute(
        select(LiveChannel.source_config_id, func.count(LiveChannel.id))
        .where(LiveChannel.source_config_id.is_not(None))
        .group_by(LiveChannel.source_config_id)
    )
    return {source_id: count for source_id, count in rows if source_id is not None}


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
