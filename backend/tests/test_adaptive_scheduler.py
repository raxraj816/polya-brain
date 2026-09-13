"""Chapter 13-F tests for bounded, version-scoped adaptive routing."""

from __future__ import annotations

from collections.abc import Callable

from app.cognition import (
    CapabilityDefinition,
    CapabilityKind,
    CapabilityPerformanceLedger,
    CapabilityPerformanceSample,
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
)
from app.cognition.task_model import CognitiveResourceBudget, budget_event
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import (
    KnowledgeGap,
    PriorityLevel,
    ReasoningMode,
    Reflection,
    StructuredProblem,
    VerificationReport,
)


def _research_state(*, sensitive: bool = False) -> PolyaState:
    state = create_initial_state(
        "Find the current supported API behavior and verify it.",
        session_id="adaptive-routing-case",
    )
    constraints = ["Use inspectable evidence."]
    if sensitive:
        constraints.append("Do not send confidential data to an unapproved capability.")
    state["structured_problem"] = StructuredProblem(
        core_question="What is the current supported API behavior?",
        problem_type="technical_research",
        knowns=["The question concerns a current behavior."],
        unknowns=["the current supported API behavior"],
        constraints=constraints,
        success_criteria=["Support the answer with inspectable evidence."],
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
            summary="Constraints were discovered.",
            metadata={"status": "ok"},
        )
    ]
    return state


def _executor(
    definition: CapabilityDefinition,
    status: ObservationStatus = ObservationStatus.SUCCEEDED,
) -> Callable[[CognitiveActionCandidate, PolyaState], CognitiveObservation]:
    def execute(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=status,
            summary=f"{definition.name} returned {status.value}.",
            failure_kind="test_failure" if status is ObservationStatus.FAILED else None,
        )

    return execute


def _research_registry(*, web_version: str = "web-v1") -> CapabilityRegistry:
    registry = CapabilityRegistry()
    web = CapabilityDefinition(
        name="web_search",
        version=web_version,
        supported_actions={CognitiveActionType.SEARCH},
        kind=CapabilityKind.EXTERNAL,
        max_external_calls=1,
        estimated_cost=0.05,
    )
    inspector = CapabilityDefinition(
        name="inspector",
        version="inspector-v1",
        supported_actions={CognitiveActionType.INSPECT},
        approved_for_sensitive_data=True,
        estimated_cost=0.2,
    )
    registry.register(FunctionCapability(web, _executor(web)))
    registry.register(FunctionCapability(inspector, _executor(inspector)))
    return registry


def _record_web_sample(
    ledger: CapabilityPerformanceLedger,
    *,
    operational_success: bool,
    verified: bool,
    version: str = "web-v1",
    duration_ms: float = 100.0,
) -> None:
    ledger.record(
        CapabilityPerformanceSample(
            session_id=f"sample-{ledger.sample_count() + 1}",
            task_family="technical_research",
            action_type=CognitiveActionType.SEARCH,
            capability="web_search",
            capability_version=version,
            capability_kind=CapabilityKind.EXTERNAL,
            operational_success=operational_success,
            contributed_to_verified_outcome=verified,
            duration_ms=duration_ms,
            external_calls=1,
            normalized_cost=0.05,
        )
    )


def test_repeated_degradation_changes_route_but_one_failure_does_not_blacklist() -> None:
    state = _research_state()
    registry = _research_registry()
    ledger = CapabilityPerformanceLedger()

    static = CognitiveController().decide(state, registry)
    assert static.selected.action_type is CognitiveActionType.SEARCH

    _record_web_sample(ledger, operational_success=False, verified=False)
    sparse = CognitiveController(performance_policy=ledger).decide(state, registry)
    assert sparse.selected.action_type is CognitiveActionType.SEARCH

    for _ in range(7):
        _record_web_sample(ledger, operational_success=False, verified=False)
    degraded = CognitiveController(performance_policy=ledger).decide(state, registry)

    assert degraded.selected.action_type is CognitiveActionType.INSPECT
    assert any("samples=8" in item.rationale for item in degraded.rejected)
    assert any("Adaptive estimate" in item.rationale for item in degraded.rejected)


def test_recovered_capability_can_be_selected_again() -> None:
    state = _research_state()
    registry = _research_registry()
    ledger = CapabilityPerformanceLedger()
    for _ in range(8):
        _record_web_sample(ledger, operational_success=False, verified=False)
    assert (
        CognitiveController(performance_policy=ledger).decide(state, registry).selected.action_type
        is CognitiveActionType.INSPECT
    )

    for _ in range(20):
        _record_web_sample(ledger, operational_success=True, verified=True)
    recovered = CognitiveController(performance_policy=ledger).decide(state, registry)

    assert recovered.selected.action_type is CognitiveActionType.SEARCH


def test_capability_version_change_starts_with_a_fresh_profile() -> None:
    state = _research_state()
    ledger = CapabilityPerformanceLedger()
    for _ in range(8):
        _record_web_sample(ledger, operational_success=False, verified=False)

    old_route = CognitiveController(performance_policy=ledger).decide(
        state,
        _research_registry(web_version="web-v1"),
    )
    new_route = CognitiveController(performance_policy=ledger).decide(
        state,
        _research_registry(web_version="web-v2"),
    )

    assert old_route.selected.action_type is CognitiveActionType.INSPECT
    assert new_route.selected.action_type is CognitiveActionType.SEARCH
    assert "samples=0" in new_route.rationale


def test_adversarial_health_cannot_override_privacy_or_hard_budget() -> None:
    ledger = CapabilityPerformanceLedger()
    for _ in range(20):
        _record_web_sample(ledger, operational_success=True, verified=True)
    controller = CognitiveController(performance_policy=ledger)
    registry = _research_registry()

    private_decision = controller.decide(_research_state(sensitive=True), registry)
    assert private_decision.selected.action_type is CognitiveActionType.INSPECT
    assert any("privacy constraint" in item.rationale for item in private_decision.rejected)

    budgeted_state = _research_state()
    budgeted_state["events"].append(budget_event(CognitiveResourceBudget(max_external_calls=0)))
    budget_decision = controller.decide(budgeted_state, registry)
    assert budget_decision.selected.action_type is CognitiveActionType.INSPECT
    assert any("hard cognitive budget" in item.rationale for item in budget_decision.rejected)


def _observed_result(
    *,
    session_id: str,
    completed_and_verified: bool,
) -> CognitiveRunResult:
    state = _research_state()
    state["session_id"] = session_id
    candidate = CognitiveActionCandidate(
        id="action-observed-search",
        action_type=CognitiveActionType.SEARCH,
        target="the current supported API behavior",
        purpose="Acquire current evidence.",
        expected_observation="A sourced fact.",
        expected_usefulness=0.9,
        estimated_cost=0.05,
        capability="web_search",
        success_condition="A source is returned.",
        failure_condition="No source is returned.",
    )
    decision = CognitiveActionDecision(
        policy_version="test-policy",
        state_fingerprint="test-fingerprint",
        selected=candidate,
        rationale="Selected for a trace-derived performance test.",
    )
    observation = CognitiveObservation(
        action_id=candidate.id,
        capability="web_search",
        capability_version="web-v1",
        status=ObservationStatus.SUCCEEDED,
        summary="The provider returned an operational response.",
    )
    state["events"].extend(
        [
            StateEvent(
                engine_name="web_search",
                event_type="capability_observation",
                reasoning_mode=ReasoningMode.EXECUTE,
                summary="Observed provider response.",
                metadata={
                    "action_id": candidate.id,
                    "duration_ms": 125.0,
                    "status": "succeeded",
                },
            ),
            StateEvent(
                engine_name="cognitive_kernel",
                event_type="cognitive_resource_usage",
                reasoning_mode=ReasoningMode.EXECUTE,
                summary="Recorded provider resource use.",
                metadata={
                    "action_id": candidate.id,
                    "capability_kind": "external",
                    "external_calls": 1,
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "normalized_cost": 0.05,
                },
            ),
        ]
    )
    if completed_and_verified:
        state["verification"] = VerificationReport(
            passed=True,
            checks_run=["Checked the sourced fact."],
        )
        state["reflection"] = Reflection(
            outcome_summary="The current fact was verified.",
            what_worked=["The source resolved the task."],
            what_failed=[],
            reusable_lessons=["Verify current claims against a source."],
        )
        state["final_answer"] = "The verified answer."
    return CognitiveRunResult(
        status=(
            CognitiveRunStatus.COMPLETED
            if completed_and_verified
            else CognitiveRunStatus.MAX_CYCLES
        ),
        state=state,
        decisions=(decision,),
        observations=(observation,),
        cycles=1,
    )


def test_trace_learning_separates_operational_success_from_verified_contribution() -> None:
    ledger = CapabilityPerformanceLedger()

    first = ledger.observe_run(
        _observed_result(session_id="verified-run", completed_and_verified=True)
    )
    second = ledger.observe_run(
        _observed_result(session_id="unverified-run", completed_and_verified=False)
    )
    profile = ledger.profile(
        "technical_research",
        CognitiveActionType.SEARCH,
        "web_search",
        "web-v1",
    )

    assert first[0].operational_success is True
    assert first[0].contributed_to_verified_outcome is True
    assert second[0].operational_success is True
    assert second[0].contributed_to_verified_outcome is False
    assert second[0].duration_ms == 125.0
    assert second[0].external_calls == 1
    assert second[0].input_tokens + second[0].output_tokens == 30
    assert profile.sample_count == 2
    assert profile.operational_successes == 2
    assert profile.verified_contributions == 1
