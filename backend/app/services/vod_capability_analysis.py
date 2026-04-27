import json
import re
import uuid
from typing import Any
from urllib.parse import parse_qsl, urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import source_snapshots

EXT_SUMMARY_CHARS = 240
API_SUMMARY_CHARS = 160
SECRET_QUERY_KEYS = {
    "token",
    "auth",
    "authorization",
    "key",
    "api_key",
    "apikey",
    "pwd",
    "pass",
    "password",
    "sign",
    "sig",
    "md5",
}
SPIDER_API_PATTERNS = (
    "csp_",
    "com.github.catvod",
    "github.catvod",
    ".spider",
    "$",
)
SPIDER_EXECUTION_HINTS = (
    ".jar",
    ".dex",
    ".class",
    ".js",
    ".py",
    "quickjs",
    "python",
    "py_exec",
    "nodejs",
)
UNSUPPORTED_SPECIAL_HINTS = (
    ".so",
    ".dll",
    ".dylib",
    "plugin",
    "native",
    "lib/",
    "assets://",
    "file://",
    "content://",
)
SPECIAL_SCHEMES = {"assets", "file", "content", "clan", "push", "proxy", "jar"}


async def latest_vod_capability_analysis(db: AsyncSession, source_config_id: uuid.UUID) -> dict[str, Any] | None:
    snapshot = await source_snapshots.latest_source_snapshot(db, source_config_id)
    if snapshot is None:
        return None

    root_config = snapshot.root_config if isinstance(snapshot.root_config, dict) else {}
    sites = root_config.get("sites")
    site_analyses = analyze_vod_sites(sites if isinstance(sites, list) else [])

    return {
        "source_config_id": source_config_id,
        "source_snapshot_id": snapshot.id,
        "source_snapshot_created_at": snapshot.created_at,
        "summary": _summary(site_analyses),
        "site_analyses": site_analyses,
    }


def analyze_vod_sites(sites: list[Any]) -> list[dict[str, Any]]:
    analyses: list[dict[str, Any]] = []
    for entry in sites:
        if not isinstance(entry, dict):
            analyses.append(
                {
                    "key": None,
                    "name": None,
                    "type": None,
                    "api": None,
                    "api_host": None,
                    "searchable": None,
                    "quickSearch": None,
                    "filterable": None,
                    "has_ext": False,
                    "ext_type": None,
                    "ext_summary": None,
                    "capability_level": "missing_or_invalid",
                    "capability_reason": "Site entry is not an object in root_config.sites.",
                }
            )
            continue

        analyses.append(_analyze_site(entry))
    return analyses


def _analyze_site(entry: dict[str, Any]) -> dict[str, Any]:
    api_value = entry.get("api")
    ext_value = entry.get("ext")
    api_string = _string_or_none(api_value)
    api_url = _http_url(api_string)
    api_host = api_url.netloc if api_url else None
    ext_type = _detect_ext_type(ext_value)
    has_ext = ext_value not in (None, "", [], {})
    capability_level, capability_reason = _classify_site(entry, api_string, ext_type)

    return {
        "key": _string_or_none(entry.get("key")),
        "name": _string_or_none(entry.get("name")),
        "type": _type_value(entry.get("type")),
        "api": _safe_api_summary(api_string),
        "api_host": api_host,
        "searchable": _bool_int_or_none(entry.get("searchable")),
        "quickSearch": _bool_int_or_none(entry.get("quickSearch", entry.get("quick_search"))),
        "filterable": _bool_int_or_none(entry.get("filterable", entry.get("filter"))),
        "has_ext": has_ext,
        "ext_type": ext_type,
        "ext_summary": _ext_summary(ext_value),
        "capability_level": capability_level,
        "capability_reason": capability_reason,
    }


def _classify_site(entry: dict[str, Any], api_string: str | None, ext_type: str | None) -> tuple[str, str]:
    site_type = entry.get("type")
    if site_type in (None, "") or not api_string:
        return "missing_or_invalid", "Site is missing a usable type or api field in the stored root config."

    lowered_api = api_string.strip().lower()
    ext_text = _normalized_text(entry.get("ext"))
    combined = f"{lowered_api} {ext_text}".strip()

    if _looks_like_spider_api(api_string):
        return "spider_required", "API looks like a CatVod/FongMi spider class reference instead of a direct HTTP API."

    if _contains_hint(combined, UNSUPPORTED_SPECIAL_HINTS) or _has_special_scheme(api_string):
        return "unsupported_special", "API or ext suggests native/plugin/local runtime behavior not supported by a generic web VOD client."

    if _contains_hint(combined, SPIDER_EXECUTION_HINTS):
        return "spider_required", "API or ext suggests JS/Python/JAR/dex/class execution, which requires spider runtime support."

    if _http_url(api_string):
        return "generic_candidate", "API is an HTTP(S) endpoint and does not look like a spider class reference."

    if ext_type in {"json_object", "json_array"} and lowered_api in {"json", "cms", "app", "v1"}:
        return "unknown", "Site uses a non-URL api marker with structured ext metadata; generic support is not clear from snapshot data alone."

    return "unknown", "Stored metadata does not clearly match a direct generic HTTP API or a known spider-only pattern."


def _summary(site_analyses: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total_sites": len(site_analyses),
        "generic_candidate_count": 0,
        "spider_required_count": 0,
        "unsupported_special_count": 0,
        "missing_or_invalid_count": 0,
        "unknown_count": 0,
    }
    for site in site_analyses:
        level = site["capability_level"]
        key = f"{level}_count"
        if key in counts:
            counts[key] += 1
    return counts


def _looks_like_spider_api(api_string: str) -> bool:
    lowered = api_string.strip().lower()
    if lowered.startswith("csp_"):
        return True
    if any(pattern in lowered for pattern in SPIDER_API_PATTERNS if pattern != "$"):
        return True
    return "$" in api_string and "." in api_string


def _has_special_scheme(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme.lower() in SPECIAL_SCHEMES if parsed.scheme else False


def _contains_hint(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint in text for hint in hints)


def _safe_api_summary(api_string: str | None) -> str | None:
    if not api_string:
        return None
    parsed = _http_url(api_string)
    if parsed:
        path = parsed.path or ""
        compact = f"{parsed.scheme}://{parsed.netloc}{_truncate(path, API_SUMMARY_CHARS - len(parsed.scheme) - len(parsed.netloc) - 3)}"
        return compact
    return _sanitize_text(api_string, API_SUMMARY_CHARS)


def _http_url(value: str | None):
    if not value:
        return None
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed


def _detect_ext_type(value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, dict):
        return "json_object"
    if isinstance(value, list):
        return "json_array"
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered.startswith(("http://", "https://")):
            return "url"
        if lowered.endswith(".js"):
            return "js"
        if lowered.endswith(".py"):
            return "python"
        if lowered.endswith(".jar"):
            return "jar"
        if lowered.endswith(".dex"):
            return "dex"
        if lowered.endswith((".so", ".dll", ".dylib")):
            return "native"
        if lowered.startswith(("clan://", "push://", "proxy://", "file://", "assets://", "content://")):
            return "special_scheme"
        return "string"
    return type(value).__name__


def _ext_summary(value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, str):
        if _http_url(value):
            parsed = urlparse(value)
            return _truncate(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", EXT_SUMMARY_CHARS)
        return _sanitize_text(value, EXT_SUMMARY_CHARS)
    try:
        text = json.dumps(_sanitize_jsonish(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except TypeError:
        text = str(value)
    return _sanitize_text(text, EXT_SUMMARY_CHARS)


def _sanitize_jsonish(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            sanitized[str(key)] = _sanitize_jsonish(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_jsonish(item) for item in value[:20]]
    if isinstance(value, str):
        return _sanitize_text(value, EXT_SUMMARY_CHARS)
    return value


def _sanitize_text(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    compact = _strip_query_strings(compact)
    compact = re.sub(r"(?i)\b(token|auth|authorization|api[_-]?key|apikey|password|pass|pwd|sign|sig|md5)=([^&\\s]+)", r"\1=<redacted>", compact)
    return _truncate(compact, limit)


def _strip_query_strings(value: str) -> str:
    def replace_url(match: re.Match[str]) -> str:
        url = match.group(0)
        try:
            parsed = urlparse(url)
        except ValueError:
            return url
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return url
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        query_items = []
        for key, item in parse_qsl(parsed.query, keep_blank_values=True):
            safe_value = "<redacted>" if key.lower() in SECRET_QUERY_KEYS else "..."
            query_items.append(f"{key}={safe_value}")
        if not query_items:
            return base
        return f"{base}?{'&'.join(query_items[:3])}"

    return re.sub(r"https?://[^\s\"'<>]+", replace_url, value)


def _normalized_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(value)
    return text.lower()


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _type_value(value: Any) -> int | str | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        text = str(value).strip()
        return text or None


def _bool_int_or_none(value: Any) -> bool | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        try:
            return int(lowered)
        except ValueError:
            return None
    return None
