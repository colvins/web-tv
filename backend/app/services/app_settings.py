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

from app.db.models import AppSetting, SourceConfig, VodSite

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
    if len(compact) <= 300:
        return compact
    return f"{compact[:297]}..."


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
