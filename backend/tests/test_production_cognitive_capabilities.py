"""End-to-end proof for the first non-fixture cognitive capability set."""

from app.cognition import (
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveKernel,
    CognitiveModelGateway,
    CognitiveRunStatus,
    CognitiveRuntime,
    calculator_capability,
    constraint_discovery_capability,
    human_input_capability,
    model_reasoning_capabilities,
    problem_representation_capability,
)
from app.engines import ConstraintDiscoveryEngine, ProblemRepresentationEngine
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.models.contracts import PlanTask, ProductMode, ReasoningMode
from app.problem_understanding import ProblemUnderstandingOutput


def _response(text: str) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="fake-cognitive-model",
        text=text,
        finish_reason="stop",
        usage=LLMTokenUsage(input_tokens=40, output_tokens=20),
    )


def test_deterministic_procedures_and_real_calculator_reach_verified_stop() -> None:
    representation = ProblemUnderstandingOutput(
        literal_framing="Evaluate 17 * 6.",
        deeper_framing="Calculate the exact result and verify it independently.",
        goal="Calculate and verify 17 * 6.",
        problem_type="simple_arithmetic",
        domain="mathematics",
        selected_mode=ProductMode.EXPLORE,
        mode_confidence=1.0,
        mode_selection_reason="The expression is fully specified.",
        given=["Expression: 17 * 6."],
        unknown=["The numeric result."],
        constraints=["Use exact arithmetic."],
        success_criteria=["The numeric result is independently checked."],
        required_data_sources=["deterministic calculator"],
    )
    client = FakeLLMClient([_response(representation.model_dump_json())])
    representation_engine = ProblemRepresentationEngine(
        client=client,
        model="fake-cognitive-model",
        fallback=lambda *args, **kwargs: None,
    )
    gateway = CognitiveModelGateway(client, "fake-cognitive-model")
    registry = CapabilityRegistry()
    registry.register(problem_representation_capability(representation_engine))
    registry.register(constraint_discovery_capability(ConstraintDiscoveryEngine()))
    registry.register(calculator_capability())
    registry.register(human_input_capability())
    for capability in model_reasoning_capabilities(gateway):
        registry.register(capability)

    result = CognitiveRuntime(registry).run_problem(
        "17 * 6?",
        session_id="production-capability-arithmetic",
        max_cycles=12,
    )

    assert result.status is CognitiveRunStatus.COMPLETED
    assert result.state["final_answer"] == "17 * 6 = 102."
    assert result.state["verification"] is not None
    assert result.state["verification"].passed
    assert result.state["reflection"] is not None
    assert [decision.selected.action_type for decision in result.decisions] == [
        CognitiveActionType.INTERPRET,
        CognitiveActionType.DISCOVER_CONSTRAINTS,
        CognitiveActionType.DETECT_GAPS,
        CognitiveActionType.CALCULATE,
        CognitiveActionType.HYPOTHESIZE,
        CognitiveActionType.PLAN,
        CognitiveActionType.EXECUTE,
        CognitiveActionType.VERIFY,
        CognitiveActionType.REFLECT,
        CognitiveActionType.STOP,
    ]
    assert len(client.requests) == 1
    assert len(result.state["evidence"]) == 2
    assert all(item.source_type == "deterministic_calculator" for item in result.state["evidence"])


def test_invalid_model_gap_output_fails_closed_without_fake_progress() -> None:
    client = FakeLLMClient([_response("not-json")])
    gateway = CognitiveModelGateway(client, "fake-cognitive-model")
    capability = model_reasoning_capabilities(gateway)[0]
    registry = CapabilityRegistry()
    registry.register(capability)
    state = create_initial_state(
        "unused",
        session_id="unused-state",
        max_iterations=1,
    )
    # Supply the minimum canonical state needed to target gap detection directly.
    state["structured_problem"] = ProblemUnderstandingOutput(
        literal_framing="Find an unknown.",
        deeper_framing="Find and verify an unknown.",
        goal="Find the unknown.",
        problem_type="research",
        selected_mode=ProductMode.EXPLORE,
        mode_confidence=1.0,
        mode_selection_reason="The task is explicit.",
        given=["A fact is missing."],
        unknown=["The missing fact."],
        constraints=["Use evidence."],
        success_criteria=["The fact is verified."],
    ).to_structured_problem()
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints completed.",
            metadata={"status": "ok"},
        )
    ]

    result = CognitiveKernel(registry).run(state, max_cycles=2)

    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert [decision.selected.action_type for decision in result.decisions] == [
        CognitiveActionType.DETECT_GAPS,
        CognitiveActionType.STOP,
    ]
    assert result.observations[0].status.value == "failed"
    assert result.observations[0].failure_kind == "capability_exception"
    assert result.state["gaps"] == []


def test_model_capability_repairs_one_malformed_structured_response() -> None:
    client = FakeLLMClient(
        [
            _response('{"gaps": "not-a-list", "rationale": "Malformed."}'),
            _response(
                """{
                  "gaps": [{
                    "description": "the missing fact",
                    "gap_type": "external_fact",
                    "priority": "high",
                    "why_needed": "The conclusion depends on it.",
                    "suggested_source": "official web source",
                    "filled": false,
                    "evidence_ids": []
                  }],
                  "rationale": "One required external fact is absent."
                }"""
            ),
        ]
    )
    gateway = CognitiveModelGateway(client, "fake-cognitive-model")
    capability = model_reasoning_capabilities(gateway)[0]
    registry = CapabilityRegistry()
    registry.register(capability)
    state = create_initial_state(
        "Find the missing fact.",
        session_id="repair-gap-output",
        max_iterations=1,
    )
    state["structured_problem"] = ProblemUnderstandingOutput(
        literal_framing="Find a fact.",
        deeper_framing="Find and verify a fact.",
        goal="Find the fact.",
        problem_type="research",
        selected_mode=ProductMode.EXPLORE,
        mode_confidence=1.0,
        mode_selection_reason="The task is explicit.",
        given=["A required fact is absent."],
        unknown=["The missing fact."],
        constraints=["Use an authoritative source."],
        success_criteria=["The fact is verified."],
    ).to_structured_problem()
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints completed.",
            metadata={"status": "ok"},
        )
    ]

    result = CognitiveKernel(registry).run(state, max_cycles=1)

    assert result.observations[0].status.value == "succeeded"
    assert len(result.state["gaps"]) == 1
    assert len(client.requests) == 2


def test_calculator_executes_expression_embedded_in_model_plan_text() -> None:
    state: PolyaState = create_initial_state(
        "17 * 6?",
        session_id="calculator-plan-normalization",
    )
    state["plan"] = [
        PlanTask(
            id="recalculate",
            action="Recalculate 17 × 6 independently.",
            tool_name="calculator",
            params={},
            expected_output="102",
        )
    ]
    capability = calculator_capability()
    registry = CapabilityRegistry()
    registry.register(capability)
    execution_action = CognitiveActionCandidate(
        id="execute-recalculate",
        action_type=CognitiveActionType.EXECUTE,
        target="recalculate",
        purpose="Independently recalculate the result.",
        expected_observation="An exact result.",
        expected_usefulness=1.0,
        estimated_cost=0.0,
        capability="calculator",
        success_condition="The calculator returns an exact result.",
        failure_condition="The expression cannot be parsed or calculated.",
    )

    observation = registry.execute(execution_action, state)

    assert observation.status.value == "succeeded"
    assert observation.proposed_update.execution_outputs_to_add[0].output == {
        "expression": "17 * 6",
        "result": "102",
    }
