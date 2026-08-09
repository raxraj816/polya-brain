"""Chapter 11 strict parsing and deterministic JSON-repair tests."""

import json

import pytest

from app.problem_understanding import (
    PROBLEM_UNDERSTANDING_EXAMPLES,
    ProblemUnderstandingParseError,
    parse_problem_understanding,
)
from app.tracing.sanitization import REDACTED


def valid_json() -> str:
    return PROBLEM_UNDERSTANDING_EXAMPLES[0].output.model_dump_json()


def test_parser_accepts_strict_json_without_repair() -> None:
    result = parse_problem_understanding(valid_json())

    assert result.output == PROBLEM_UNDERSTANDING_EXAMPLES[0].output
    assert result.local_repair_steps == []


def test_parser_removes_markdown_fence() -> None:
    result = parse_problem_understanding(f"```json\n{valid_json()}\n```")

    assert result.output == PROBLEM_UNDERSTANDING_EXAMPLES[0].output
    assert result.local_repair_steps == ["removed_markdown_fence"]


def test_parser_extracts_balanced_object_from_surrounding_prose() -> None:
    result = parse_problem_understanding(f"Here is the result:\n{valid_json()}\nDone.")

    assert result.output == PROBLEM_UNDERSTANDING_EXAMPLES[0].output
    assert result.local_repair_steps == ["extracted_json_object"]


def test_parser_removes_trailing_commas_without_changing_string_content() -> None:
    payload = PROBLEM_UNDERSTANDING_EXAMPLES[0].output.model_dump(mode="json")
    payload["given"] = ['The literal characters ",}" must remain.']
    malformed = json.dumps(payload).replace(
        '"required_data_sources": []}',
        '"required_data_sources": [],}',
    )

    result = parse_problem_understanding(malformed)

    assert result.local_repair_steps == ["removed_trailing_commas"]
    assert result.output.given == ['The literal characters ",}" must remain.']


def test_parser_rejects_empty_non_object_and_invalid_json() -> None:
    with pytest.raises(ProblemUnderstandingParseError, match="response is empty"):
        parse_problem_understanding(" ")
    with pytest.raises(ProblemUnderstandingParseError, match="must be a JSON object"):
        parse_problem_understanding("[]")
    with pytest.raises(ProblemUnderstandingParseError, match="invalid JSON"):
        parse_problem_understanding('{"goal": }')


def test_parser_reports_contract_paths_without_raw_secret() -> None:
    secret = "sk-or-v1-abcdefghijklmnopqrstuvwxyz123456"
    payload = PROBLEM_UNDERSTANDING_EXAMPLES[0].output.model_dump(mode="json")
    payload["mode_confidence"] = 3
    payload["wrong_problem_warning"] = secret

    with pytest.raises(ProblemUnderstandingParseError) as exc_info:
        parse_problem_understanding(json.dumps(payload))

    assert "mode_confidence" in str(exc_info.value)
    assert secret not in str(exc_info.value)
    assert REDACTED not in str(exc_info.value)
