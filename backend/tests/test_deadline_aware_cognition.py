"""Chapter 13-G tests for hard run-duration governance."""

from __future__ import annotations

from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
    CognitiveObservation,
    CognitiveResourceBudget,
    CognitiveRunStatus,
    FunctionCapability,
    ObservationStatus,
    accumulated_usage,
)
from app.cognition.task_model import budget_event
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import (
    KnowledgeGap,
    PriorityLevel,
    ReasoningMode,
    StructuredProblem,
)


def _state() -> PolyaState:
    state = create_initial_state(
        "Find the current supported API behavior.",
        session_id="deadline-aware-case",
    )
    state["structured_problem"] = StructuredProblem(
        core_question="What is the current supported API behavior?",
        problem_type="technical_research",
        knowns=["The answer may have changed."],
        unknowns=["the current supported API behavior"],
        constraints=["Use inspectable evidence."],
        success_criteria=["Resolve the current behavior from a source."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description="the current supported API behavior",
            gap_type="current_external_fact",
            priority=PriorityLevel.HIGH,
            why_needed="The current fact blocks a verified answer.",
            suggested_source="official web source",
        )
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints were supplied.",
            metadata={"status": "ok"},
        )
    ]
    return state


def _registry(counter: dict[str, int] | None = None) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    web = CapabilityDefinition(
        name="web_search",
        version="slow-web-v1",
        supported_actions={CognitiveActionType.SEARCH},
        timeout_seconds=120.0,
        estimated_cost=0.05,
    )
    inspector = CapabilityDefinition(
        name="inspector",
        version="fast-inspector-v1",
        supported_actions={CognitiveActionType.INSPECT},
        timeout_seconds=5.0,
        estimated_cost=0.2,
    )

    def execute(
        definition: CapabilityDefinition,
        action: CognitiveActionCandidate,
    ) -> CognitiveObservation:
        if counter is not None:
            counter[definition.name] = counter.get(definition.name, 0) + 1
        # Make a small amount of deterministic work visible to the timer.
        sum(index * index for index in range(1_000))
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary="Produced a bounded test observation.",
        )

    registry.register(FunctionCapability(web, lambda action, _state: execute(web, action)))
    registry.register(
        FunctionCapability(inspector, lambda action, _state: execute(inspector, action))
    )
    return registry


def test_controller_selects_route_whose_timeout_fits_remaining_deadline() -> None:
    state = _state()
    state["events"].append(budget_event(CognitiveResourceBudget(max_duration_ms=20_000.0)))

    decision = CognitiveController().decide(state, _registry())

    assert decision.selected.action_type is CognitiveActionType.INSPECT
    assert any("duration requires" in item.rationale for item in decision.rejected)


def test_exhausted_deadline_stops_without_executing_or_forcing_answer() -> None:
    counter: dict[str, int] = {}

    result = CognitiveKernel(_registry(counter)).run(
        _state(),
        max_cycles=1,
        budget=CognitiveResourceBudget(max_duration_ms=0.0),
    )

    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert result.observations == ()
    assert result.decisions == ()
    assert counter == {}
    assert result.state["final_answer"] is None
    assert any(
        event.event_type == "cognitive_run_deadline_exhausted" for event in result.state["events"]
    )


def test_executed_capability_charges_measured_duration() -> None:
    counter: dict[str, int] = {}

    result = CognitiveKernel(_registry(counter)).run(
        _state(),
        max_cycles=1,
        budget=CognitiveResourceBudget(max_duration_ms=20_000.0),
    )
    usage = accumulated_usage(result.state)
    usage_events = [
        event for event in result.state["events"] if event.event_type == "cognitive_resource_usage"
    ]

    assert result.observations
    assert counter == {"inspector": 1}
    assert usage.duration_ms > 0
    assert usage_events
    assert float(usage_events[0].metadata["duration_ms"]) == usage.duration_ms
