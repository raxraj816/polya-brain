"""Secret redaction for persisted and logged trace data."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from pydantic import JsonValue

REDACTED = "[REDACTED]"

SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
)

SECRET_VALUE_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b"),
)


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in SECRET_KEY_PARTS:
        return True
    return normalized.endswith(
        ("_api_key", "_apikey", "_authorization", "_cookie", "_password", "_secret", "_token")
    )


def sanitize_text(value: str) -> str:
    """Redact obvious secret-bearing substrings from free text."""
    sanitized = value
    for pattern in SECRET_VALUE_PATTERNS:
        sanitized = pattern.sub(REDACTED, sanitized)
    return sanitized


def sanitize_json_value(value: JsonValue) -> JsonValue:
    """Return a JSON-compatible value with secret-like strings redacted."""
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, Mapping):
        return sanitize_json_mapping(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [sanitize_json_value(item) for item in value]
    return value


def sanitize_json_mapping(metadata: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Recursively redact secret-like metadata keys and values."""
    sanitized: dict[str, JsonValue] = {}
    for key, value in metadata.items():
        if _is_secret_key(key):
            sanitized[key] = REDACTED
            continue
        sanitized[key] = sanitize_json_value(value)
    return sanitized
