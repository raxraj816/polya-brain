"""Chapter 11 prompt-layer contract tests."""

import pytest
from pydantic import ValidationError

from app.models.contracts import ProductMode
from app.problem_understanding import (
    ParserRetryPolicy,
    ProblemUnderstandingOutput,
    problem_understanding_json_schema,
)


def valid_output(**overrides: object) -> ProblemUnderstandingOutput:
    payload: dict[str, object] = {
        "literal_framing": "Investigate an API latency regression.",
        "deeper_framing": "Identify the measured bottleneck before selecting a fix.",
        "wrong_problem_warning": "Adding cache first may solve the wrong problem.",
        "goal": "Identify the safest next diagnostic.",
        "problem_type": "software_root_cause_investigation",
        "domain": "software_debugging",
        "selected_mode": ProductMode.INVESTIGATE,
        "mode_confidence": 0.92,
        "mode_selection_reason": "The input describes an anomaly and asks what to investigate.",
        "needs_clarification": False,
        "clarifying_questions": [],
        "given": ["Latency increased after a deploy."],
        "unknown": ["Dominant latency component."],
        "constraints": ["Use reversible diagnostics first."],
        "success_criteria": ["A check distinguishes query, application, and dependency latency."],
        "affected_entities": ["API", "deployment"],
        "time_window": {"relative": "after deploy"},
        "required_data_sources": ["distributed traces"],
    }
    payload.update(overrides)
    return ProblemUnderstandingOutput.model_validate(payload)


def test_output_round_trips_and_maps_to_canonical_structured_problem() -> None:
    output = valid_output()

    round_tripped = ProblemUnderstandingOutput.model_validate_json(output.model_dump_json())
    structured = output.to_structured_problem()

    assert round_tripped == output
    assert structured.core_question == output.goal
    assert structured.knowns == output.given
    assert structured.unknowns == output.unknown
    assert structured.constraints == output.constraints
    assert structured.success_criteria == output.success_criteria
    assert structured.model_dump().keys() == {
        "core_question",
        "problem_type",
        "domain",
        "knowns",
        "unknowns",
        "constraints",
        "success_criteria",
        "affected_entities",
        "time_window",
        "required_data_sources",
    }


def test_low_mode_confidence_requires_clarification() -> None:
    with pytest.raises(ValidationError, match="below clarification threshold"):
        valid_output(mode_confidence=0.4)


def test_clarification_flag_requires_questions() -> None:
    with pytest.raises(ValidationError, match="requires at least one clarifying question"):
        valid_output(needs_clarification=True, clarifying_questions=[])


def test_clarifying_questions_require_flag() -> None:
    with pytest.raises(ValidationError, match="clarifying questions require"):
        valid_output(clarifying_questions=["Which endpoint is slow?"])


def test_success_criteria_are_required() -> None:
    with pytest.raises(ValidationError, match="at least one success criterion"):
        valid_output(success_criteria=[])


def test_output_rejects_extra_fields_and_invalid_modes() -> None:
    payload = valid_output().model_dump()
    payload["reasoning_chain"] = "hidden reasoning must not become a contract"
    with pytest.raises(ValidationError):
        ProblemUnderstandingOutput.model_validate(payload)

    with pytest.raises(ValidationError):
        valid_output(selected_mode="brainstorm")


def test_json_schema_exposes_exact_polya_and_approach_fields() -> None:
    schema = problem_understanding_json_schema()
    properties = schema["properties"]
    required = schema["required"]
    assert isinstance(properties, dict)
    assert isinstance(required, list)

    for field in [
        "given",
        "unknown",
        "constraints",
        "goal",
        "success_criteria",
        "literal_framing",
        "deeper_framing",
        "wrong_problem_warning",
        "selected_mode",
        "mode_confidence",
        "mode_selection_reason",
        "needs_clarification",
        "clarifying_questions",
    ]:
        assert field in properties

    assert {"given", "unknown", "constraints", "goal", "success_criteria"} <= set(required)


def test_parser_retry_policy_is_bounded() -> None:
    assert ParserRetryPolicy().max_llm_repair_attempts == 1
    assert ParserRetryPolicy(max_llm_repair_attempts=2).max_llm_repair_attempts == 2
    with pytest.raises(ValidationError):
        ParserRetryPolicy(max_llm_repair_attempts=3)
