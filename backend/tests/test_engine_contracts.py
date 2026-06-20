"""Chapter 7 engine interface contract tests."""

import pytest
from pydantic import BaseModel, ValidationError

from app.engines import (
    EngineResult,
    EngineRoute,
    EngineRunOutput,
    EngineStatus,
    EngineVersion,
    TokenUsage,
    engine_event_metadata,
    run_engine,
)
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import ReasoningMode, StructuredProblem


def assert_json_round_trip(model: BaseModel) -> None:
    parsed = type(model).model_validate_json(model.model_dump_json())

    assert parsed == model


def valid_engine_version(**overrides: object) -> EngineVersion:
    payload: dict[str, object] = {
        "engine": "representation@0.1.0",
        "prompt": "representation_prompt@0.1.0",
        "model": "fake-model@0.1.0",
        "tool": None,
        "verifier": "contract_guard@0.1.0",
        "graph": "polya_graph@0.1.0",
    }
    payload.update(overrides)
    return EngineVersion.model_validate(payload)


def valid_engine_result(**overrides: object) -> EngineResult:
    payload: dict[str, object] = {
        "status": EngineStatus.OK,
        "confidence": 0.82,
        "missing_inputs": [],
        "recommended_route": EngineRoute.CONTINUE,
        "duration_ms": 12.5,
        "errors": [],
        "token_usage": {"input_tokens": 12, "output_tokens": 8},
        "versions": valid_engine_version(),
        "summary": "Engine completed with enough confidence to continue.",
    }
    payload.update(overrides)
    return EngineResult.model_validate(payload)


class SuccessfulEngine:
    name = "representation"
    reasoning_mode = ReasoningMode.EXPLORE
    version = valid_engine_version(engine="representation@0.1.0")

    def run(self, state: PolyaState) -> EngineRunOutput:
        structured_problem = StructuredProblem.model_validate(
            {
                "core_question": state["raw_input"],
                "problem_type": "software_debugging",
                "domain": "technical_investigation",
                "knowns": ["The user supplied a debugging problem."],
                "unknowns": ["Root cause is unknown."],
                "constraints": ["Avoid irreversible production changes."],
                "success_criteria": ["Identify the next safest diagnostic step."],
                "affected_entities": ["api"],
                "time_window": {},
                "required_data_sources": ["logs"],
            }
        )
        return EngineRunOutput(
            state_delta={
                "structured_problem": structured_problem,
                "events": {
                    "engine_name": self.name,
                    "event_type": "parsed",
                    "reasoning_mode": self.reasoning_mode,
                    "summary": "Parsed raw input into a structured problem.",
                },
            },
            result=valid_engine_result(versions=self.version),
        )


class FailingEngine:
    name = "representation"
    reasoning_mode = ReasoningMode.EXPLORE
    version = valid_engine_version(engine="representation@0.1.0")

    def run(self, state: PolyaState) -> EngineRunOutput:
        raise RuntimeError(f"cannot parse {state['session_id']}")


class InvalidEventEngine:
    name = "representation"
    reasoning_mode = ReasoningMode.EXPLORE
    version = valid_engine_version(engine="representation@0.1.0")

    def run(self, state: PolyaState) -> EngineRunOutput:
        return EngineRunOutput(
            state_delta={
                "events": {
                    "engine_name": self.name,
                    "event_type": "parsed",
                    "reasoning_mode": self.reasoning_mode,
                    "summary": "",
                }
            },
            result=valid_engine_result(versions=self.version),
        )


class MalformedIdentityEngine:
    name = " "
    reasoning_mode = "not_a_reasoning_mode"
    version = {"engine": ""}

    def run(self, state: PolyaState) -> EngineRunOutput:
        raise RuntimeError(f"malformed identity for {state['session_id']}")


def test_engine_contracts_round_trip_through_json() -> None:
    assert_json_round_trip(TokenUsage(input_tokens=3, output_tokens=5))
    assert_json_round_trip(valid_engine_version())
    assert_json_round_trip(valid_engine_result())
    assert_json_round_trip(
        EngineRunOutput(
            state_delta={"final_answer": "Continue with evidence gathering."},
            result=valid_engine_result(),
        )
    )


def test_token_usage_rejects_negative_counts() -> None:
    with pytest.raises(ValidationError):
        TokenUsage(input_tokens=-1, output_tokens=0)

    with pytest.raises(ValidationError):
        TokenUsage(input_tokens=0, output_tokens=-1)


def test_engine_version_rejects_blank_engine_identifier() -> None:
    with pytest.raises(ValidationError):
        valid_engine_version(engine=" ")


def test_engine_result_rejects_invalid_enum_values() -> None:
    with pytest.raises(ValidationError):
        valid_engine_result(status="done")

    with pytest.raises(ValidationError):
        valid_engine_result(recommended_route="next")


def test_ok_result_requires_confidence_and_continue_route() -> None:
    with pytest.raises(ValidationError, match="ok engine result requires confidence"):
        valid_engine_result(confidence=None)

    with pytest.raises(ValidationError, match="ok engine result must recommend continue"):
        valid_engine_result(recommended_route=EngineRoute.RESEARCH)


def test_needs_input_requires_missing_inputs_and_clarify_route() -> None:
    with pytest.raises(ValidationError, match="requires missing_inputs"):
        valid_engine_result(
            status=EngineStatus.NEEDS_INPUT,
            confidence=None,
            missing_inputs=[],
            recommended_route=EngineRoute.CLARIFY,
        )

    with pytest.raises(ValidationError, match="must recommend clarify"):
        valid_engine_result(
            status=EngineStatus.NEEDS_INPUT,
            confidence=None,
            missing_inputs=["deploy timestamp"],
            recommended_route=EngineRoute.RESEARCH,
        )


def test_needs_evidence_requires_research_route() -> None:
    with pytest.raises(ValidationError, match="must recommend research"):
        valid_engine_result(
            status=EngineStatus.NEEDS_EVIDENCE,
            confidence=None,
            recommended_route=EngineRoute.CONTINUE,
        )


@pytest.mark.parametrize("status", [EngineStatus.LOW_CONFIDENCE, EngineStatus.BLOCKED])
def test_low_confidence_and_blocked_results_cannot_continue(status: EngineStatus) -> None:
    with pytest.raises(ValidationError, match="cannot recommend continue"):
        valid_engine_result(status=status, confidence=0.2, recommended_route=EngineRoute.CONTINUE)


def test_failed_result_requires_error_detail_and_cannot_continue() -> None:
    with pytest.raises(ValidationError, match="requires at least one error"):
        valid_engine_result(
            status=EngineStatus.FAILED,
            confidence=None,
            recommended_route=EngineRoute.FINALIZE,
            errors=[],
        )

    with pytest.raises(ValidationError, match="failed engine result cannot recommend continue"):
        valid_engine_result(
            status=EngineStatus.FAILED,
            confidence=None,
            recommended_route=EngineRoute.CONTINUE,
            errors=["timeout"],
        )


def test_insufficient_evidence_requires_insufficient_evidence_finalize_route() -> None:
    with pytest.raises(ValidationError, match="must recommend finalize_insufficient_evidence"):
        valid_engine_result(
            status=EngineStatus.INSUFFICIENT_EVIDENCE,
            confidence=None,
            recommended_route=EngineRoute.FINALIZE,
        )


def test_engine_event_metadata_is_json_compatible_and_complete() -> None:
    result = valid_engine_result()

    metadata = engine_event_metadata(result)

    assert metadata["status"] == "ok"
    assert metadata["recommended_route"] == "continue"
    assert metadata["confidence"] == 0.82
    assert metadata["token_usage"] == {
        "input_tokens": 12,
        "output_tokens": 8,
        "total_tokens": 20,
    }
    assert metadata["versions"]["engine"] == "representation@0.1.0"


def test_run_engine_wraps_success_with_duration_events_and_versions() -> None:
    state = create_initial_state("Investigate p95 latency after deploy.", session_id="session_123")

    output = run_engine(SuccessfulEngine(), state)

    assert output.result.status is EngineStatus.OK
    assert output.result.duration_ms >= 0
    assert output.result.versions == SuccessfulEngine.version
    assert output.state_delta["structured_problem"] is not None

    events = output.state_delta["events"]
    assert [event.event_type for event in events] == ["started", "parsed", "completed"]
    assert all(isinstance(event, StateEvent) for event in events)
    assert events[0].metadata["versions"]["engine"] == "representation@0.1.0"
    assert events[-1].metadata["status"] == "ok"
    assert events[-1].metadata["recommended_route"] == "continue"

    assert state["events"] == []
    assert state["structured_problem"] is None


def test_run_engine_converts_exceptions_to_failed_result() -> None:
    state = create_initial_state("Investigate an invalid input path.", session_id="session_456")

    output = run_engine(FailingEngine(), state)

    assert output.result.status is EngineStatus.FAILED
    assert output.result.recommended_route is EngineRoute.FINALIZE
    assert output.result.errors == ["RuntimeError: cannot parse session_456"]
    assert output.result.duration_ms >= 0
    assert output.result.versions == FailingEngine.version
    assert output.state_delta.keys() == {"events"}
    assert [event.event_type for event in output.state_delta["events"]] == ["started", "failed"]
    assert output.state_delta["events"][-1].metadata["errors"] == [
        "RuntimeError: cannot parse session_456"
    ]


def test_run_engine_converts_malformed_engine_events_to_failed_result() -> None:
    state = create_initial_state("Investigate malformed trace output.", session_id="session_789")

    output = run_engine(InvalidEventEngine(), state)

    assert output.result.status is EngineStatus.FAILED
    assert output.result.recommended_route is EngineRoute.FINALIZE
    assert output.result.errors
    assert "ValidationError" in output.result.errors[0]
    assert [event.event_type for event in output.state_delta["events"]] == ["started", "failed"]


def test_engine_run_output_rejects_unknown_state_delta_keys() -> None:
    with pytest.raises(ValidationError, match="unknown PolyaState keys"):
        EngineRunOutput(
            state_delta={"structured_problm": None},
            result=valid_engine_result(),
        )


def test_run_engine_fails_closed_for_malformed_engine_identity() -> None:
    state = create_initial_state("Investigate malformed engine identity.", session_id="session_bad")

    output = run_engine(MalformedIdentityEngine(), state)  # type: ignore[arg-type]

    assert output.result.status is EngineStatus.FAILED
    assert output.result.versions.engine == "unknown_engine@unknown"
    assert output.result.errors == ["RuntimeError: malformed identity for session_bad"]
    assert [event.event_type for event in output.state_delta["events"]] == ["started", "failed"]
    assert output.state_delta["events"][0].engine_name == "unknown_engine"
    assert output.state_delta["events"][0].reasoning_mode is ReasoningMode.EXPLORE
    assert (
        output.state_delta["events"][0].metadata["versions"]["engine"] == "unknown_engine@unknown"
    )
