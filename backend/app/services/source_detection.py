import base64
import binascii
import json
import re
from dataclasses import dataclass
from typing import Any


CATVOD_KEYS = {"sites", "lives", "parses", "flags", "spider", "wallpaper", "logo"}
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=\s_-]{24,}$")
BASE64_BLOCK_RE = re.compile(rb"[A-Za-z0-9+/=_-]{80,}")


@dataclass(frozen=True)
class DetectionResult:
    detected_format: str
    detection_confidence: float
    detection_note: str


def detect_source_content(content: bytes) -> DetectionResult:
    text = _decode_text(content)
    stripped = text.lstrip("\ufeff\r\n\t ")

    if stripped.startswith("#EXTM3U"):
        return DetectionResult("m3u", 0.99, "Text starts with #EXTM3U.")

    parsed_json = _parse_json(stripped)
    if parsed_json is not None:
        return _json_detection(parsed_json)

    base64_text = _decode_base64_text(stripped)
    if base64_text is not None and _parse_json(base64_text.lstrip("\ufeff\r\n\t ")) is not None:
        return DetectionResult("base64_json", 0.9, "Text is base64 and decodes to JSON.")

    if _contains_embedded_base64_json(content):
        return DetectionResult("binary_wrapped", 0.82, "Content contains an embedded base64-looking JSON block.")

    if _readable_ratio(text) >= 0.75:
        return DetectionResult("txt", 0.65, "Content is mostly readable text but is not JSON or M3U.")

    return DetectionResult("unknown", 0.2, "Content format was not recognized.")


def recover_json_config(content: bytes) -> Any | None:
    text = _decode_text(content).lstrip("\ufeff\r\n\t ")
    parsed = _parse_json(text)
    if parsed is not None:
        return parsed

    decoded = _decode_base64_text(text)
    if decoded is not None:
        parsed = _parse_json(decoded.lstrip("\ufeff\r\n\t "))
        if parsed is not None:
            return parsed

    for match in BASE64_BLOCK_RE.finditer(content):
        block = match.group(0).decode("ascii", errors="ignore")
        decoded = _decode_base64_text(block)
        if decoded is None:
            continue
        parsed = _parse_json(decoded.lstrip("\ufeff\r\n\t "))
        if parsed is not None:
            return parsed
    return None


def _decode_text(content: bytes) -> str:
    return content.decode("utf-8", errors="replace").replace("\x00", "\uFFFD")


def _parse_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _json_detection(value: Any) -> DetectionResult:
    keys = _collect_top_level_keys(value)
    matched = sorted(keys & CATVOD_KEYS)
    if matched:
        return DetectionResult("catvod_json", 0.96, f"JSON contains CatVod/FongMi keys: {', '.join(matched[:5])}.")
    return DetectionResult("plain_json", 0.9, "Content is valid JSON.")


def _collect_top_level_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key in value.keys()}
    return set()


def _decode_base64_text(text: str) -> str | None:
    compact = "".join(text.split())
    if not BASE64_RE.match(compact):
        return None
    padding = "=" * (-len(compact) % 4)
    for candidate in (compact, compact.replace("-", "+").replace("_", "/")):
        try:
            decoded = base64.b64decode(candidate + padding, validate=True)
        except (binascii.Error, ValueError):
            continue
        return _decode_text(decoded)
    return None


def _contains_embedded_base64_json(content: bytes) -> bool:
    for match in BASE64_BLOCK_RE.finditer(content):
        block = match.group(0).decode("ascii", errors="ignore")
        decoded = _decode_base64_text(block)
        if decoded is not None and _parse_json(decoded.lstrip("\ufeff\r\n\t ")) is not None:
            return True
    return False


def _readable_ratio(text: str) -> float:
    if not text:
        return 0.0
    sample = text[:4000]
    readable = sum(1 for char in sample if char.isprintable() or char in "\r\n\t")
    return readable / len(sample)
