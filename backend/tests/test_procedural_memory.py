"""Verified procedural-memory transfer tests for Chapter 13-C."""

from __future__ import annotations

from collections.abc import Callable

from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionDecision,
    CognitiveActionType,
    CognitiveController,
    CognitiveObservation,
    CognitiveRunResult,
    CognitiveRunStatus,
    FunctionCapability,
    ObservationStatus,
    ProceduralMemory,
)
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import (
    KnowledgeGap,
    PriorityLevel,
    ReasoningMode,
    Reflection,
    StructuredProblem,
    VerificationReport,
)


def _related_state(*, filled: bool, session_id: str) -> PolyaState:
    state = create_initial_state(
        "Determine current behavior from an authoritative source.",
        session_id=session_id,
    )
    state["structured_problem"] = StructuredProblem(
        core_question="What is the current supported behavior?",
        problem_type="technical_research",
        knowns=["The answer may have changed."],
        unknowns=[] if filled else ["the current supported behavior"],
        success_criteria=["Use an authoritative observation."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description="the current supported behavior",
            gap_type="current_external_fact",
            priority=PriorityLevel.HIGH,
            why_needed="The answer changes over time.",
            suggested_source="official web source",
            filled=filled,
            evidence_ids=["verified-observation"] if filled else [],
        )
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints were discovered in the source case.",
            metadata={"status": "ok"},
        )
    ]
    return state


def _verified_recovery_result() -> CognitiveRunResult:
    state = _related_state(filled=True, session_id="verified-source-run")
    state["verification"] = VerificationReport(
        passed=True,
        checks_run=["Checked the recovered authoritative artifact."],
        confidence_delta=0.2,
    )
    state["reflection"] = Reflection(
        outcome_summary="Inspection succeeded after search failed.",
        what_worked=["Inspect the bundled authoritative artifact."],
        reusable_lessons=["Use inspection when live search fails for this gap."],
    )
    candidate = CognitiveActionCandidate(
        id="inspect-recovery",
        action_type=CognitiveActionType.INSPECT,
        target="the current supported behavior",
        purpose="Recover from unavailable search using an authoritative artifact.",
        expected_observation="The current specification statement.",
        expected_usefulness=0.9,
        estimated_cost=0.1,
        capability="inspector",
        success_condition="The authoritative artifact resolves the gap.",
        failure_condition="The artifact is missing or stale.",
    )
    decision = CognitiveActionDecision(
        policy_version="test-policy",
        state_fingerprint="verified-state",
        selected=candidate,
        rationale="Selected the successful recovery action.",
    )
    observation = CognitiveObservation(
        action_id=candidate.id,
        capability="inspector",
        capability_version="test-v1",
        status=ObservationStatus.SUCCEEDED,
        summary="Inspected the authoritative artifact.",
    )
    return CognitiveRunResult(
        status=CognitiveRunStatus.COMPLETED,
        state=state,
        decisions=(decision,),
        observations=(observation,),
        cycles=1,
    )


def _registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    def executor_for(
        definition: CapabilityDefinition,
    ) -> Callable[[CognitiveActionCandidate, PolyaState], CognitiveObservation]:
        def execute(
            candidate: CognitiveActionCandidate,
            _state: PolyaState,
        ) -> CognitiveObservation:
            return CognitiveObservation(
                action_id=candidate.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.SUCCEEDED,
                summary="Returned a test observation.",
            )

        return execute

    for name, action in (
        ("web_search", CognitiveActionType.SEARCH),
        ("inspector", CognitiveActionType.INSPECT),
    ):
        definition = CapabilityDefinition(
            name=name,
            version="test-v1",
            supported_actions={action},
            estimated_cost=0.1,
        )
        registry.register(
            FunctionCapability(
                definition,
                executor_for(definition),
            )
        )
    return registry


def test_verified_recovery_strategy_changes_later_action_selection() -> None:
    memory = ProceduralMemory()
    learned = memory.learn(_verified_recovery_result())
    related = _related_state(filled=False, session_id="related-run")
    registry = _registry()

    without_memory = CognitiveController().decide(related, registry)
    with_memory = CognitiveController(memory).decide(related, registry)

    assert len(learned) == 1
    assert learned[0].action_type is CognitiveActionType.INSPECT
    assert without_memory.selected.action_type is CognitiveActionType.SEARCH
    assert with_memory.selected.action_type is CognitiveActionType.INSPECT
    assert "verified related run" in with_memory.selected.purpose


def test_unverified_run_cannot_teach_procedural_memory() -> None:
    result = _verified_recovery_result()
    unverified_state = dict(result.state)
    unverified_state["verification"] = None
    unverified = CognitiveRunResult(
        status=CognitiveRunStatus.MAX_CYCLES,
        state=unverified_state,  # type: ignore[arg-type]
        decisions=result.decisions,
        observations=result.observations,
        cycles=result.cycles,
    )
    memory = ProceduralMemory()

    assert memory.learn(unverified) == []
    assert memory.strategies() == []
