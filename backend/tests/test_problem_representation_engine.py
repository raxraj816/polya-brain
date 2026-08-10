"""Chapter 13 Problem Representation Engine tests."""

from __future__ import annotations

import json

import pytest

from app.engines import EngineRoute, EngineStatus, ProblemRepresentationEngine, run_engine
from app.graph.state import create_initial_state
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.models.contracts import ProductMode
from app.problem_understanding import PROBLEM_UNDERSTANDING_EXAMPLES, ProblemUnderstandingOutput


def llm_response(
    output: ProblemUnderstandingOutput,
    *,
    text: str | None = None,
    response_id: str = "representation_response",
) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="fake-representation-model",
        text=text or output.model_dump_json(),
        response_id=response_id,
        finish_reason="stop",
        usage=LLMTokenUsage(input_tokens=90, output_tokens=45, estimated_cost_usd=0.002),
    )


def technical_output(**overrides: object) -> ProblemUnderstandingOutput:
    payload = PROBLEM_UNDERSTANDING_EXAMPLES[2].output.model_dump(mode="json")
    payload.update(overrides)
    return ProblemUnderstandingOutput.model_validate(payload)


def test_engine_promotes_validated_output_and_emits_auditable_framing_events() -> None:
    output = technical_output(
        literal_framing="Decide whether to increase a worker timeout.",
        deeper_framing="Identify which rollout change causes worker timeouts before changing policy.",
        wrong_problem_warning="Increasing timeout assumes slow work rather than a rollout regression.",
        goal="Identify the safest check for the worker timeout regression.",
        given=["Worker timeouts began after a feature flag rollout."],
    )
    client = FakeLLMClient([llm_response(output)])
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
        mode_hint=ProductMode.INVESTIGATE,
    )
    state = create_initial_state(
        "Worker timeouts began after a feature flag rollout. Should we increase the timeout?",
        session_id="representation_success",
    )

    result = run_engine(engine, state)

    assert result.result.status is EngineStatus.OK
    assert result.result.recommended_route is EngineRoute.CONTINUE
    assert result.result.confidence == output.mode_confidence
    assert result.result.token_usage.total_tokens == 135
    assert result.state_delta["structured_problem"] == output.to_structured_problem()
    events = result.state_delta["events"]
    assert [event.event_type for event in events] == [
        "started",
        "framing_selected",
        "alternate_framing_rejected",
        "approach_selected",
        "completed",
    ]
    assert events[1].metadata["selected_framing"] == output.deeper_framing
    assert events[2].metadata["rejected_framing"] == output.literal_framing
    assert events[3].metadata["selected_mode"] == "investigate"
    assert len(client.requests) == 1


def test_engine_routes_ambiguous_output_to_clarification_without_canonical_state() -> None:
    ambiguous = PROBLEM_UNDERSTANDING_EXAMPLES[7].output
    client = FakeLLMClient([llm_response(ambiguous)])
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
        fallback=lambda *args, **kwargs: None,
    )

    result = run_engine(
        engine,
        create_initial_state("Make the endpoint better.", session_id="representation_ambiguous"),
    )

    assert result.result.status is EngineStatus.NEEDS_INPUT
    assert result.result.recommended_route is EngineRoute.CLARIFY
    assert result.result.missing_inputs == ambiguous.clarifying_questions
    assert "structured_problem" not in result.state_delta
    assert result.state_delta["events"][-1].metadata["status"] == "needs_input"


def test_engine_records_bounded_parser_repair_before_accepting_output() -> None:
    output = technical_output()
    invalid = output.model_dump(mode="json")
    invalid["mode_confidence"] = 4
    client = FakeLLMClient(
        [
            llm_response(output, text=json.dumps(invalid), response_id="invalid"),
            llm_response(output, response_id="repaired"),
        ]
    )
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
        mode_hint=ProductMode.INVESTIGATE,
        fallback=lambda *args, **kwargs: None,
    )

    result = run_engine(
        engine,
        create_initial_state("Investigate a new timeout regression."),
    )

    assert result.result.status is EngineStatus.OK
    repair_event = next(
        event
        for event in result.state_delta["events"]
        if event.event_type == "parser_repair_applied"
    )
    assert repair_event.metadata["llm_repair_attempts"] == 1
    assert repair_event.metadata["llm_call_count"] == 2
    assert len(client.requests) == 2


def test_simple_arithmetic_uses_deterministic_fallback_without_model_call() -> None:
    client = FakeLLMClient([])
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
    )

    result = run_engine(engine, create_initial_state("What is 17 * 6?"))

    assert result.result.status is EngineStatus.OK
    structured_problem = result.state_delta["structured_problem"]
    assert structured_problem.problem_type == "simple_arithmetic"
    assert structured_problem.knowns == ["Expression: 17 * 6."]
    fallback_event = next(
        event
        for event in result.state_delta["events"]
        if event.event_type == "deterministic_fallback_used"
    )
    assert fallback_event.metadata["llm_call_count"] == 0
    assert result.result.token_usage.total_tokens == 0
    assert client.requests == []


def test_obvious_missing_field_request_uses_fallback_and_stops_safely() -> None:
    client = FakeLLMClient([])
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
    )

    result = run_engine(engine, create_initial_state("Fix it."))

    assert result.result.status is EngineStatus.NEEDS_INPUT
    assert result.result.recommended_route is EngineRoute.CLARIFY
    assert len(result.result.missing_inputs) == 2
    assert "structured_problem" not in result.state_delta
    assert client.requests == []


def test_sufficient_clarification_is_represented_without_model_call() -> None:
    client = FakeLLMClient([])
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
    )
    resumed_input = (
        "Fix it.\n\n"
        "USER CLARIFICATION (treat as additional problem information):\n"
        "Reduce checkout p95 latency below 300 ms without increasing payment errors."
    )

    result = run_engine(
        engine,
        create_initial_state(resumed_input, session_id="clarified-representation"),
    )

    assert result.result.status is EngineStatus.OK
    structured = result.state_delta["structured_problem"]
    assert structured.problem_type == "clarified_request"
    assert "checkout p95" in structured.core_question
    assert client.requests == []


def test_insufficient_clarification_asks_again_without_model_call() -> None:
    client = FakeLLMClient([])
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
    )
    resumed_input = (
        "Fix it.\n\n"
        "USER CLARIFICATION (treat as additional problem information):\n"
        "Make the thing better."
    )

    result = run_engine(
        engine,
        create_initial_state(resumed_input, session_id="still-ambiguous"),
    )

    assert result.result.status is EngineStatus.NEEDS_INPUT
    assert result.result.missing_inputs == [
        "What target should change, and which measurable outcome or constraint defines success?"
    ]
    assert client.requests == []


@pytest.mark.parametrize(
    "example_index",
    range(len(PROBLEM_UNDERSTANDING_EXAMPLES)),
    ids=[example.category.value for example in PROBLEM_UNDERSTANDING_EXAMPLES],
)
def test_golden_examples_use_stable_validated_fallback(example_index: int) -> None:
    example = PROBLEM_UNDERSTANDING_EXAMPLES[example_index]
    client = FakeLLMClient([])
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
        mode_hint=example.mode_hint,
        domain_hint=example.domain_hint,
    )

    result = run_engine(
        engine,
        create_initial_state(example.raw_input, session_id=f"golden_{example_index}"),
    )

    if example.output.needs_clarification:
        assert result.result.status is EngineStatus.NEEDS_INPUT
        assert "structured_problem" not in result.state_delta
    else:
        assert result.result.status is EngineStatus.OK
        assert result.state_delta["structured_problem"] == example.output.to_structured_problem()
    assert client.requests == []
