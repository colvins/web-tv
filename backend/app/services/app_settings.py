import base64
import binascii
import json
import re
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting, ImportJob, SourceConfig, VodSite

CURRENT_VOD_SITE_KEY = "current_vod_site_id"
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=\s_-]+$")


async def get_current_vod_site(db: AsyncSession) -> VodSite | None:
    setting = await db.scalar(select(AppSetting).where(AppSetting.key == CURRENT_VOD_SITE_KEY))
    if setting is None:
        return None

    site_id = setting.value.get("vod_site_id")
    if not site_id:
        return None

    try:
        parsed_site_id = uuid.UUID(str(site_id))
    except ValueError:
        return None

    return await _get_site_with_source(db, parsed_site_id)


async def set_current_vod_site(db: AsyncSession, vod_site_id: uuid.UUID) -> VodSite:
    site = await _get_site_with_source(db, vod_site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VOD site not found")
    if not site.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Disabled VOD site cannot be selected")
    if site.source_config is None or not site.source_config.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="VOD site parent source must be enabled",
        )

    statement = insert(AppSetting).values(key=CURRENT_VOD_SITE_KEY, value={"vod_site_id": str(site.id)})
    await db.execute(
        statement.on_conflict_do_update(
            index_elements=[AppSetting.key],
            set_={"value": statement.excluded.value},
        )
    )
    await db.commit()
    return site


async def clear_current_vod_site_if_matches(db: AsyncSession, vod_site_id: uuid.UUID) -> bool:
    setting = await db.scalar(select(AppSetting).where(AppSetting.key == CURRENT_VOD_SITE_KEY))
    if setting is None or str(setting.value.get("vod_site_id")) != str(vod_site_id):
        return False

    await db.delete(setting)
    return True


async def clear_current_vod_site_if_source_matches(db: AsyncSession, source_config_id: uuid.UUID) -> bool:
    site = await get_current_vod_site(db)
    if site is None or site.source_config_id != source_config_id:
        return False

    setting = await db.scalar(select(AppSetting).where(AppSetting.key == CURRENT_VOD_SITE_KEY))
    if setting is None:
        return False
    await db.delete(setting)
    return True


def current_vod_site_response(site: VodSite | None) -> dict | None:
    if site is None:
        return None
    return {
        "id": site.id,
        "source_config_id": site.source_config_id,
        "site_key": site.site_key,
        "site_name": site.site_name,
        "site_type": site.site_type,
        "api": site.api,
        "enabled": site.enabled,
        "source_name": site.source_config.name if site.source_config else None,
    }


async def get_current_vod_site_analysis(db: AsyncSession) -> dict | None:
    site = await get_current_vod_site(db)
    if site is None or not site.enabled:
        return None
    if site.source_config is None or not site.source_config.enabled:
        return None

    raw_config = site.raw_config if isinstance(site.raw_config, dict) else {}
    ext_analysis = _analyze_ext(raw_config.get("ext"))
    support_assessment = _assess_support(site, ext_analysis)
    warnings = _analysis_warnings(site, ext_analysis)

    return {
        "site_id": site.id,
        "site_name": site.site_name,
        "site_key": site.site_key,
        "site_type": site.site_type,
        "api": site.api,
        "source_name": site.source_config.name,
        "enabled": site.enabled,
        "raw_keys": sorted(str(key) for key in raw_config.keys()),
        "known_flags": _known_flags(raw_config),
        "ext_analysis": ext_analysis,
        "support_assessment": support_assessment,
        "warnings": warnings,
    }


async def get_current_vod_site_spider_analysis(db: AsyncSession) -> dict | None:
    site = await get_current_vod_site(db)
    if site is None or not site.enabled:
        return None
    if site.source_config is None or not site.source_config.enabled:
        return None

    raw_config = site.raw_config if isinstance(site.raw_config, dict) else {}
    latest_job = await _latest_successful_import_job(db, site.source_config_id)
    stored_text = " ".join(
        part
        for part in (
            _safe_json(raw_config),
            latest_job.raw_preview if latest_job and latest_job.raw_preview else "",
        )
        if part
    )
    api = (site.api or "").strip()
    root_config_keys = _root_config_keys(raw_config, latest_job)
    api_locations = _api_reference_locations(api, raw_config, latest_job)
    spider_summary = _spider_field_summary(raw_config, latest_job)
    reference_type = _possible_reference_type(api, stored_text, spider_summary)
    reference_summary = _possible_reference_summary(api, reference_type, raw_config, spider_summary)
    warnings = _spider_analysis_warnings(site, latest_job, spider_summary)
    support_strategy = _spider_support_strategy(site, reference_type, spider_summary)

    return {
        "site_id": site.id,
        "site_key": site.site_key,
        "site_name": site.site_name,
        "site_type": site.site_type,
        "api": site.api,
        "source_name": site.source_config.name,
        "root_config_keys": root_config_keys,
        "spider_field_present": bool(spider_summary),
        "spider_field_summary": _truncate(spider_summary, 300),
        "api_reference_found": bool(api_locations),
        "api_reference_locations": api_locations,
        "possible_reference_type": reference_type,
        "possible_reference_summary": _truncate(reference_summary, 500),
        "support_strategy": support_strategy,
        "warnings": warnings,
    }


async def _get_site_with_source(db: AsyncSession, site_id: uuid.UUID) -> VodSite | None:
    result = await db.execute(
        select(VodSite, SourceConfig)
        .join(SourceConfig, VodSite.source_config_id == SourceConfig.id, isouter=True)
        .where(VodSite.id == site_id)
    )
    row = result.first()
    if row is None:
        return None

    site, source_config = row
    site.source_config = source_config
    return site


async def _latest_successful_import_job(db: AsyncSession, source_config_id: uuid.UUID | None) -> ImportJob | None:
    if source_config_id is None:
        return None
    return await db.scalar(
        select(ImportJob)
        .where(ImportJob.source_config_id == source_config_id, ImportJob.status == "success")
        .order_by(ImportJob.finished_at.desc().nullslast(), ImportJob.created_at.desc())
        .limit(1)
    )


def _known_flags(raw_config: dict[str, Any]) -> dict[str, Any]:
    return {
        "searchable": raw_config.get("searchable"),
        "changeable": raw_config.get("changeable"),
        "quickSearch": raw_config.get("quickSearch", raw_config.get("quick_search")),
        "filterable": raw_config.get("filterable", raw_config.get("filter")),
        "categories": raw_config.get("categories", raw_config.get("class")),
        "style": raw_config.get("style"),
        "playerType": raw_config.get("playerType", raw_config.get("player_type")),
    }


def _analyze_ext(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "present": False,
            "value_type": None,
            "summary": "",
            "looks_like_url": False,
            "looks_like_json": False,
            "looks_like_base64": False,
            "looks_like_executable_or_opaque": False,
        }

    text = value if isinstance(value, str) else _safe_json(value)
    looks_like_url = _looks_like_url(text)
    looks_like_json = _looks_like_json(text)
    looks_like_base64 = _looks_like_base64(text)
    looks_like_opaque = not looks_like_url and not looks_like_json

    return {
        "present": True,
        "value_type": _value_type(value),
        "summary": _short_summary(value),
        "looks_like_url": looks_like_url,
        "looks_like_json": looks_like_json,
        "looks_like_base64": looks_like_base64,
        "looks_like_executable_or_opaque": looks_like_opaque,
    }


def _assess_support(site: VodSite, ext_analysis: dict[str, Any]) -> dict[str, str]:
    api = (site.api or "").strip()
    lowered_api = api.lower()
    site_type = site.site_type

    if not api:
        return {
            "level": "unsupported_unknown",
            "reason": "The site has no API value to classify.",
            "next_step": "Keep this site as catalog metadata until a concrete adapter shape is known.",
        }
    if site_type == 3 or lowered_api.startswith("csp_"):
        return {
            "level": "requires_spider",
            "reason": "This site references a CatVod spider-style API and must not be executed directly.",
            "next_step": "Design a sandboxed adapter strategy before enabling any browsing behavior.",
        }
    if site_type in {0, 1} and _looks_like_url(api):
        return {
            "level": "possible_http",
            "reason": "The site type and API shape look compatible with a future HTTP adapter.",
            "next_step": "Add a read-only adapter contract before fetching categories or lists.",
        }
    if ext_analysis["present"]:
        return {
            "level": "metadata_only",
            "reason": "The site has extra configuration, but its runnable behavior is not supported yet.",
            "next_step": "Document the stored raw_config fields before adding any adapter.",
        }
    return {
        "level": "unsupported_unknown",
        "reason": "The site API shape is not recognized by the current safe analysis rules.",
        "next_step": "Keep this entry disabled for browsing until its protocol is understood.",
    }


def _analysis_warnings(site: VodSite, ext_analysis: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    api = (site.api or "").strip().lower()
    if site.site_type == 3 or api.startswith("csp_"):
        warnings.append("Spider-style API detected; no spider/JAR/JS/Python/ext code was executed.")
    if ext_analysis["present"] and ext_analysis["looks_like_executable_or_opaque"]:
        warnings.append("ext is opaque or non-JSON and was left inert.")
    if ext_analysis["present"] and ext_analysis["looks_like_base64"]:
        warnings.append("ext resembles base64; it was not decoded for execution.")
    return warnings


def _root_config_keys(raw_config: dict[str, Any], latest_job: ImportJob | None) -> list[str]:
    preview = latest_job.raw_preview if latest_job and latest_job.raw_preview else ""
    root_keys = [key for key in ("spider", "wallpaper", "logo", "sites", "lives", "parses", "rules", "flags") if key in preview]
    if root_keys:
        return sorted(set(root_keys))
    return sorted(str(key) for key in raw_config.keys())


def _api_reference_locations(api: str, raw_config: dict[str, Any], latest_job: ImportJob | None) -> list[str]:
    if not api:
        return []
    locations: list[str] = []
    for key, value in raw_config.items():
        if api in _safe_json(value):
            locations.append(f"site.raw_config.{key}")
    if latest_job and latest_job.raw_preview and api in latest_job.raw_preview:
        locations.append(f"import_job.raw_preview:{latest_job.id}")
    return locations


def _spider_field_summary(raw_config: dict[str, Any], latest_job: ImportJob | None) -> str:
    if "spider" in raw_config:
        return _short_summary(raw_config["spider"])
    preview = latest_job.raw_preview if latest_job and latest_job.raw_preview else ""
    marker = '"spider"'
    index = preview.find(marker)
    if index < 0:
        marker = "spider"
        index = preview.find(marker)
    if index < 0:
        return ""
    return _truncate(preview[index : index + 300], 300)


def _possible_reference_type(api: str, stored_text: str, spider_summary: str) -> str:
    lowered_api = api.lower()
    lowered_text = stored_text.lower()
    lowered_spider = spider_summary.lower()
    joined = " ".join((lowered_api, lowered_text, lowered_spider))

    if lowered_api.endswith(".js") or ".js" in lowered_spider:
        return "js_reference"
    if lowered_api.endswith(".py") or ".py" in lowered_spider:
        return "py_reference"
    if ".jar" in joined or ";md5;" in joined:
        return "jar_reference"
    if _looks_like_url(api) or "http://" in lowered_spider or "https://" in lowered_spider:
        return "remote_url_reference"
    if api and api in stored_text:
        return "inline_name_only"
    if not api:
        return "none"
    return "unknown"


def _possible_reference_summary(
    api: str,
    reference_type: str,
    raw_config: dict[str, Any],
    spider_summary: str,
) -> str:
    if spider_summary:
        return spider_summary
    if api and raw_config:
        return f"API name {api!r} is present in the stored site raw_config only."
    if reference_type == "none":
        return "No API or spider reference was found in stored metadata."
    return "No concrete spider package URL or executable body is stored for this site."


def _spider_support_strategy(site: VodSite, reference_type: str, spider_summary: str) -> dict[str, str]:
    api = (site.api or "").strip()
    lowered_api = api.lower()
    if not api:
        return {
            "level": "unsupported_unknown",
            "reason": "The selected site has no API reference to analyze.",
            "recommended_next_step": "Keep this site as metadata until a supported adapter target is known.",
        }
    if lowered_api.endswith(".js") or reference_type == "js_reference":
        return {
            "level": "possible_js_runtime",
            "reason": "The stored metadata points to a JavaScript-style reference, but it was not executed.",
            "recommended_next_step": "Define a sandboxed JavaScript adapter policy before any runtime support.",
        }
    if site.site_type in {0, 1} and _looks_like_url(api):
        return {
            "level": "possible_http_adapter",
            "reason": "The site type and API look like a future HTTP adapter candidate.",
            "recommended_next_step": "Add a read-only HTTP adapter contract before fetching remote VOD metadata.",
        }
    if site.site_type == 3 or lowered_api.startswith("csp_") or spider_summary:
        return {
            "level": "needs_spider_runtime",
            "reason": "The site references CatVod spider behavior and cannot be browsed by metadata inspection alone.",
            "recommended_next_step": "Design a sandboxed spider runtime boundary before enabling this source.",
        }
    return {
        "level": "unsupported_unknown",
        "reason": "Stored metadata does not identify a supported runtime or HTTP adapter.",
        "recommended_next_step": "Collect more source metadata through existing imports before adding browsing support.",
    }


def _spider_analysis_warnings(site: VodSite, latest_job: ImportJob | None, spider_summary: str) -> list[str]:
    warnings = ["Analysis used stored database metadata only; no spider, API, or package URL was executed."]
    api = (site.api or "").strip().lower()
    if site.site_type == 3 or api.startswith("csp_"):
        warnings.append("Type 3/csp_ source requires a spider runtime for real browsing behavior.")
    if spider_summary:
        warnings.append("A root spider reference appears in stored import metadata, but it was not downloaded.")
    if latest_job and latest_job.raw_preview:
        warnings.append("Only ImportJob.raw_preview is stored, so root package analysis may be partial.")
    return warnings


def _value_type(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    return type(value).__name__


def _short_summary(value: Any) -> str:
    text = value if isinstance(value, str) else _safe_json(value)
    compact = " ".join(text.split())
    return _truncate(compact, 300)


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _looks_like_url(value: str) -> bool:
    return value.strip().lower().startswith(("http://", "https://"))


def _looks_like_json(value: str) -> bool:
    stripped = value.strip()
    if not stripped.startswith(("{", "[")):
        return False
    try:
        json.loads(stripped)
    except json.JSONDecodeError:
        return False
    return True


def _looks_like_base64(value: str) -> bool:
    compact = "".join(value.strip().split())
    if len(compact) < 16 or not BASE64_RE.match(compact):
        return False
    padding = "=" * (-len(compact) % 4)
    try:
        base64.b64decode(compact + padding, validate=False)
    except (binascii.Error, ValueError):
        return False
    return True
