import base64
import binascii
import json
import re
from dataclasses import dataclass
from typing import Any
CATVOD_KEYS = {"sites", "lives", "parses", "flags", "spider", "wallpaper", "logo", "rules", "hosts"}
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=\s_-]{24,}$")
BASE64_BLOCK_RE = re.compile(rb"[A-Za-z0-9+/=_-]{80,}")


@dataclass(frozen=True)
class DetectionResult:
    detected_format: str
    detection_confidence: float
    detection_note: str


@dataclass(frozen=True)
class RecoveryResult:
    recovered_value: Any
    source_format: str
    note: str


def detect_source_content(content: bytes) -> DetectionResult:
    text = _decode_text(content)
    stripped = text.lstrip("\ufeff\r\n\t ")

    if stripped.startswith("#EXTM3U"):
        return DetectionResult("m3u", 0.99, "Text starts with #EXTM3U.")

    recovery = recover_root_config(content)
    if recovery is not None:
        if recovery.source_format == "plain_json":
            return _json_detection(recovery.recovered_value)
        if recovery.source_format == "base64_json":
            return DetectionResult("base64_json", 0.92, recovery.note)
        return DetectionResult("binary_wrapped", 0.93, recovery.note)

    if _readable_ratio(text) >= 0.75:
        return DetectionResult("txt", 0.65, "Content is mostly readable text but is not JSON or M3U.")

    return DetectionResult("unknown", 0.2, "Content format was not recognized.")


def recover_json_config(content: bytes) -> Any | None:
    recovery = recover_root_config(content)
    return recovery.recovered_value if recovery is not None else None


def recover_root_config(content: bytes) -> RecoveryResult | None:
    text = _decode_text(content).lstrip("\ufeff\r\n\t ")
    parsed = _parse_json_like(text)
    if parsed is not None:
        return RecoveryResult(parsed, "plain_json", "Content is valid JSON-like root config.")

    decoded = _decode_base64_text(text)
    if decoded is not None:
        parsed = _parse_json_like(decoded.lstrip("\ufeff\r\n\t "))
        if parsed is not None:
            return RecoveryResult(parsed, "base64_json", "Text is base64 and decodes to a JSON-like root config.")

    for match in BASE64_BLOCK_RE.finditer(content):
        block = match.group(0).decode("ascii", errors="ignore")
        decoded = _decode_base64_text(block)
        if decoded is None:
            continue
        parsed = _parse_json_like(decoded.lstrip("\ufeff\r\n\t "))
        if parsed is None:
            continue
        if _looks_like_jpeg(content):
            return RecoveryResult(
                parsed,
                "image_base64_wrapped",
                "JPEG-like binary contains an embedded base64-wrapped JSON-like CatVod/FongMi root config.",
            )
        return RecoveryResult(
            parsed,
            "binary_wrapped",
            "Binary/text response contains an embedded base64-wrapped JSON-like root config.",
        )
    return None


def _decode_text(content: bytes) -> str:
    return content.decode("utf-8", errors="replace").replace("\x00", "\uFFFD")


def _parse_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _parse_json_like(text: str) -> Any | None:
    candidates = [text.strip().rstrip(";")]
    uncommented = _strip_js_line_comments(text).strip().rstrip(";")
    if uncommented not in candidates:
        candidates.append(uncommented)

    for candidate in candidates:
        parsed = _parse_json(candidate)
        if parsed is not None:
            return parsed
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
    return recover_root_config(content) is not None


def _readable_ratio(text: str) -> float:
    if not text:
        return 0.0
    sample = text[:4000]
    readable = sum(1 for char in sample if char.isprintable() or char in "\r\n\t")
    return readable / len(sample)


def _looks_like_jpeg(content: bytes) -> bool:
    return content.startswith(b"\xff\xd8\xff")


def _strip_js_line_comments(text: str) -> str:
    output: list[str] = []
    in_string = False
    string_delimiter = ""
    escaped = False
    i = 0

    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == string_delimiter:
                in_string = False
            i += 1
            continue

        if char in {'"', "'"}:
            in_string = True
            string_delimiter = char
            output.append(char)
            i += 1
            continue

        if char == "/" and nxt == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue

        output.append(char)
        i += 1

    return "".join(output)
