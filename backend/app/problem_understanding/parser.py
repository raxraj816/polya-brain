"""Strict parsing and bounded deterministic JSON repair for Chapter 11."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.problem_understanding.contracts import (
    ProblemUnderstandingOutput,
    ProblemUnderstandingParseResult,
)
from app.tracing.sanitization import sanitize_text

_OPENING_FENCE = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_CLOSING_FENCE = re.compile(r"\s*```$", re.IGNORECASE)


class ProblemUnderstandingParseError(ValueError):
    """Safe parser failure that never includes the raw model response."""

    def __init__(self, message: str) -> None:
        self.safe_message = sanitize_text(message)
        super().__init__(self.safe_message)


def _extract_balanced_object(value: str) -> str | None:
    start = value.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(value)):
        character = value[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return value[start : index + 1]
    return None


def _remove_trailing_commas(value: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(value):
        character = value[index]
        if in_string:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == '"':
            in_string = True
            output.append(character)
            index += 1
            continue
        if character == ",":
            lookahead = index + 1
            while lookahead < len(value) and value[lookahead].isspace():
                lookahead += 1
            if lookahead < len(value) and value[lookahead] in "}]":
                index += 1
                continue
        output.append(character)
        index += 1
    return "".join(output)


def _json_candidate(raw_text: str) -> tuple[str, list[str]]:
    candidate = raw_text.strip()
    repair_steps: list[str] = []
    without_opening_fence = _OPENING_FENCE.sub("", candidate)
    without_fences = _CLOSING_FENCE.sub("", without_opening_fence).strip()
    if without_fences != candidate:
        candidate = without_fences
        repair_steps.append("removed_markdown_fence")

    balanced = _extract_balanced_object(candidate)
    if balanced is not None and balanced != candidate:
        candidate = balanced
        repair_steps.append("extracted_json_object")
    return candidate, repair_steps


def _decode_object(candidate: str) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(candidate)
        repair_steps: list[str] = []
    except json.JSONDecodeError as initial_error:
        repaired = _remove_trailing_commas(candidate)
        if repaired == candidate:
            raise ProblemUnderstandingParseError(
                f"invalid JSON at line {initial_error.lineno}, column {initial_error.colno}"
            ) from initial_error
        try:
            payload = json.loads(repaired)
        except json.JSONDecodeError as repaired_error:
            raise ProblemUnderstandingParseError(
                f"invalid JSON after local repair at line {repaired_error.lineno}, "
                f"column {repaired_error.colno}"
            ) from repaired_error
        repair_steps = ["removed_trailing_commas"]

    if not isinstance(payload, dict):
        raise ProblemUnderstandingParseError("problem-understanding response must be a JSON object")
    return payload, repair_steps


def _validation_error_summary(error: ValidationError) -> str:
    issues: list[str] = []
    for item in error.errors(include_url=False):
        location = ".".join(str(part) for part in item["loc"]) or "root"
        issues.append(f"{location}: {item['msg']}")
    return "; ".join(issues)


def parse_problem_understanding(raw_text: str) -> ProblemUnderstandingParseResult:
    """Parse, locally repair, and contract-validate one model response."""
    if not raw_text.strip():
        raise ProblemUnderstandingParseError("problem-understanding response is empty")
    candidate, extraction_steps = _json_candidate(raw_text)
    payload, syntax_steps = _decode_object(candidate)
    try:
        output = ProblemUnderstandingOutput.model_validate(payload)
    except ValidationError as exc:
        raise ProblemUnderstandingParseError(_validation_error_summary(exc)) from exc
    return ProblemUnderstandingParseResult(
        output=output,
        local_repair_steps=[*extraction_steps, *syntax_steps],
    )
