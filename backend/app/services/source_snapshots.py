import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportJob, SourceSnapshot
from app.services.source_configs import get_source_config
from app.services.source_detection import recover_json_config

MAX_ROOT_CONFIG_JSON_BYTES = 2 * 1024 * 1024
SPIDER_SUMMARY_CHARS = 500


async def latest_source_snapshot(db: AsyncSession, source_config_id: uuid.UUID) -> SourceSnapshot | None:
    await get_source_config(db, source_config_id)
    return await db.scalar(
        select(SourceSnapshot)
        .where(SourceSnapshot.source_config_id == source_config_id)
        .order_by(SourceSnapshot.created_at.desc(), SourceSnapshot.updated_at.desc())
        .limit(1)
    )


async def require_latest_source_snapshot(db: AsyncSession, source_config_id: uuid.UUID) -> SourceSnapshot:
    snapshot = await latest_source_snapshot(db, source_config_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source snapshot not found")
    return snapshot


async def store_source_snapshot(db: AsyncSession, import_job: ImportJob, content: bytes) -> None:
    if import_job.content_sha256 is None:
        return

    values = _snapshot_values(import_job, content)
    statement = insert(SourceSnapshot).values(**values)
    update_values = {
        "import_job_id": statement.excluded.import_job_id,
        "detected_format": statement.excluded.detected_format,
        "recovered_format": statement.excluded.recovered_format,
        "root_config": statement.excluded.root_config,
        "root_keys": statement.excluded.root_keys,
        "sites_count": statement.excluded.sites_count,
        "lives_count": statement.excluded.lives_count,
        "parses_count": statement.excluded.parses_count,
        "has_spider": statement.excluded.has_spider,
        "spider_summary": statement.excluded.spider_summary,
        "warnings": statement.excluded.warnings,
    }
    await db.execute(
        statement.on_conflict_do_update(
            constraint="uq_source_snapshots_source_sha",
            set_=update_values,
        )
    )


def _snapshot_values(import_job: ImportJob, content: bytes) -> dict[str, Any]:
    warnings: list[str] = []
    root_config: dict[str, Any] | None = None
    recovered_format: str | None = None

    recovered = recover_json_config(content)
    if isinstance(recovered, dict):
        serialized = json.dumps(recovered, ensure_ascii=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) <= MAX_ROOT_CONFIG_JSON_BYTES:
            root_config = recovered
            recovered_format = "json_object"
        else:
            warnings.append("Recovered JSON config exceeded 2MB snapshot limit and was not stored.")
            recovered_format = "json_object_too_large"
    elif recovered is not None:
        warnings.append("Recovered JSON config was not an object and was not stored.")
        recovered_format = "json_non_object"
    else:
        warnings.append("No recoverable root JSON config was found.")

    root_keys = sorted(str(key) for key in root_config.keys()) if root_config else []
    sites_count = _list_count(root_config, "sites")
    lives_count = _list_count(root_config, "lives")
    parses_count = _list_count(root_config, "parses")
    spider = root_config.get("spider") if root_config else None
    has_spider = spider not in (None, "", [], {})

    warnings.append("Snapshot stores metadata only; spider/JAR/JS/Python/ext and nested URLs were not executed or fetched.")

    return {
        "source_config_id": import_job.source_config_id,
        "import_job_id": import_job.id,
        "content_sha256": import_job.content_sha256,
        "detected_format": import_job.detected_format,
        "recovered_format": recovered_format,
        "root_config": root_config,
        "root_keys": root_keys,
        "sites_count": sites_count,
        "lives_count": lives_count,
        "parses_count": parses_count,
        "has_spider": has_spider,
        "spider_summary": _summary(spider) if has_spider else None,
        "warnings": warnings,
    }


def _list_count(root_config: dict[str, Any] | None, key: str) -> int:
    value = root_config.get(key) if root_config else None
    return len(value) if isinstance(value, list) else 0


def _summary(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    compact = " ".join(text.split())
    if len(compact) <= SPIDER_SUMMARY_CHARS:
        return compact
    return f"{compact[: SPIDER_SUMMARY_CHARS - 3]}..."
