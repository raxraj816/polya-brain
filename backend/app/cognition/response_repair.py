"""Bounded explicit edits to an unadmitted response, never canonical state."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from pydantic import Field, JsonValue, StrictInt, StrictStr

from app.models.contracts import ContractModel
from app.tracing.sanitization import sanitize_text

VERSION = "structured_response_edits@0.1.0"


class ResponseEdit(ContractModel):
    """Set an object field or replace an existing list element at an exact path."""

    path: list[StrictStr | StrictInt] = Field(min_length=1, max_length=12)
    value: JsonValue


class ResponseEdits(ContractModel):
    """Only changed fields; the full reconstructed object must still validate."""

    edits: list[ResponseEdit] = Field(min_length=1, max_length=16)


def _digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def apply_response_edits(
    original: dict[str, object], payload: dict[str, object]
) -> tuple[dict[str, object], dict[str, JsonValue]]:
    if len(json.dumps(payload, ensure_ascii=False).encode()) > 64_000:
        raise ValueError("Structured response edits exceed the 64000-byte allowance.")
    edits = ResponseEdits.model_validate(payload).edits
    paths = [edit.path for edit in edits]
    for index, path in enumerate(paths):
        if any(
            path[: min(len(path), len(other))] == other[: min(len(path), len(other))]
            for other in paths[:index]
        ):
            raise ValueError("Structured response edit paths must not overlap.")
    result = deepcopy(original)
    for edit in edits:
        target: object = result
        for part in edit.path[:-1]:
            if isinstance(target, dict) and isinstance(part, str) and part in target:
                target = target.get(part)
            elif isinstance(target, list) and isinstance(part, int) and 0 <= part < len(target):
                target = target[part]
            else:
                raise ValueError("Structured response edit parent path does not exist.")
        last = edit.path[-1]
        if isinstance(target, dict) and isinstance(last, str):
            target.update({last: deepcopy(edit.value)})
        elif isinstance(target, list) and isinstance(last, int) and 0 <= last < len(target):
            target[last] = deepcopy(edit.value)
        else:
            raise ValueError(
                "Structured response edit target is not an object field or list element."
            )
    return result, {
        "version": VERSION,
        "response_form": "edits",
        "original_sha256": _digest(original),
        "reconstructed_sha256": _digest(result),
        "paths": [[part for part in path] for path in paths],
    }


def full_response_metadata(
    original: dict[str, object] | None, repaired: dict[str, object]
) -> dict[str, JsonValue]:
    return {
        "version": VERSION,
        "response_form": "full",
        "original_sha256": _digest(original) if original is not None else None,
        "reconstructed_sha256": _digest(repaired),
    }


def safe_repair_metadata(value: JsonValue) -> dict[str, JsonValue] | None:
    """Retain bounded identities and paths, never repaired content."""
    if not isinstance(value, dict) or value.get("version") != VERSION:
        return None
    if value.get("response_form") not in ("edits", "full"):
        return None
    result: dict[str, JsonValue] = {"version": VERSION, "response_form": value["response_form"]}
    for key in ("original_sha256", "reconstructed_sha256"):
        digest = value.get(key)
        if digest is None and key == "original_sha256":
            result[key] = None
        elif (
            isinstance(digest, str)
            and len(digest) == 64
            and all(c in "0123456789abcdef" for c in digest)
        ):
            result[key] = digest
        else:
            return None
    paths = value.get("paths")
    if isinstance(paths, list):
        result["paths"] = [
            [sanitize_text(part)[:200] if isinstance(part, str) else part for part in path]
            for path in paths[:16]
            if isinstance(path, list)
            and 1 <= len(path) <= 12
            and all(isinstance(part, str) or (type(part) is int and part >= 0) for part in path)
        ]
    return result
