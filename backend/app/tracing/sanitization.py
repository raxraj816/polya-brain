"""Secret redaction for persisted and logged trace data."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import JsonValue

REDACTED = "[REDACTED]"

SECRET_KEY_PARTS = (
    "access_key",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "database_url",
    "db_url",
    "dsn",
    "password",
    "private_key",
    "secret",
    "secret_access_key",
    "token",
    "webhook_url",
)

SECRET_VALUE_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[aboprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s@]+@[^\s]+", re.IGNORECASE),
    re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+", re.IGNORECASE),
)


@dataclass(frozen=True)
class SanitizedText:
    """Sanitized text plus the number of redaction replacements made."""

    value: str
    redaction_count: int


@dataclass(frozen=True)
class SanitizedJson:
    """Sanitized JSON-compatible value plus redaction count."""

    value: JsonValue
    redaction_count: int


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in SECRET_KEY_PARTS:
        return True
    return normalized.endswith(
        (
            "_access_key",
            "_api_key",
            "_apikey",
            "_authorization",
            "_client_secret",
            "_cookie",
            "_database_url",
            "_db_url",
            "_dsn",
            "_password",
            "_private_key",
            "_secret",
            "_secret_access_key",
            "_token",
            "_webhook_url",
        )
    )


def sanitize_text_with_count(value: str) -> SanitizedText:
    """Redact obvious secret-bearing substrings from free text."""
    # PostgreSQL text/JSONB cannot represent U+0000. Keep a visible escape in
    # persisted presentation without interpreting it as a scientific symbol or
    # deleting the surrounding claim. This is representation, not secret redaction.
    sanitized = value.replace("\x00", r"\u0000")
    redaction_count = 0
    for pattern in SECRET_VALUE_PATTERNS:
        sanitized, replacements = pattern.subn(REDACTED, sanitized)
        redaction_count += replacements
    return SanitizedText(value=sanitized, redaction_count=redaction_count)


def sanitize_text(value: str) -> str:
    """Redact obvious secret-bearing substrings from free text."""
    return sanitize_text_with_count(value).value


def sanitize_json_value_with_count(value: JsonValue) -> SanitizedJson:
    """Return a JSON-compatible value with secret-like strings redacted."""
    if isinstance(value, str):
        sanitized_text = sanitize_text_with_count(value)
        return SanitizedJson(
            value=sanitized_text.value,
            redaction_count=sanitized_text.redaction_count,
        )
    if isinstance(value, Mapping):
        sanitized_mapping, redaction_count = sanitize_json_mapping_with_count(value)
        return SanitizedJson(value=sanitized_mapping, redaction_count=redaction_count)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sanitized_items: list[JsonValue] = []
        redaction_count = 0
        for item in value:
            sanitized_item = sanitize_json_value_with_count(item)
            sanitized_items.append(sanitized_item.value)
            redaction_count += sanitized_item.redaction_count
        return SanitizedJson(value=sanitized_items, redaction_count=redaction_count)
    return SanitizedJson(value=value, redaction_count=0)


def sanitize_json_value(value: JsonValue) -> JsonValue:
    """Return a JSON-compatible value with secret-like strings redacted."""
    return sanitize_json_value_with_count(value).value


def sanitize_json_mapping_with_count(
    metadata: Mapping[str, JsonValue],
) -> tuple[dict[str, JsonValue], int]:
    """Recursively redact secret-like metadata keys and values with a count."""
    sanitized: dict[str, JsonValue] = {}
    redaction_count = 0
    for key, value in metadata.items():
        if _is_secret_key(key):
            sanitized[key] = REDACTED
            redaction_count += 1
            continue
        sanitized_value = sanitize_json_value_with_count(value)
        sanitized[key] = sanitized_value.value
        redaction_count += sanitized_value.redaction_count
    return sanitized, redaction_count


def sanitize_json_mapping(metadata: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Recursively redact secret-like metadata keys and values."""
    return sanitize_json_mapping_with_count(metadata)[0]
