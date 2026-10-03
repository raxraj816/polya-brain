"""Cross-domain tests for the experimental cognitive controller."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveController,
    CognitiveObservation,
    FunctionCapability,
    ObservationStatus,
)
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import (
    KnowledgeGap,
    PriorityLevel,
    ReasoningMode,
    StructuredProblem,
)


def _state_with_gap(
    *,
    problem_type: str,
    gap_type: str,
    description: str,
    source: str,
) -> PolyaState:
    state = create_initial_state(
        f"Solve the {problem_type} problem.",
        session_id=f"case-{problem_type}",
    )
    state["structured_problem"] = StructuredProblem(
        core_question=f"What resolves this {problem_type} problem?",
        problem_type=problem_type,
        knowns=["The goal is explicit."],
        unknowns=[description],
        constraints=["Use inspectable evidence."],
        success_criteria=["Resolve the important unknown."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description=description,
            gap_type=gap_type,
            priority=PriorityLevel.HIGH,
            why_needed="This unknown blocks a verified solution.",
            suggested_source=source,
        )
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints were already discovered for this controller unit case.",
            metadata={"status": "ok"},
        )
    ]
    return state


def _noop_executor(
    definition: CapabilityDefinition,
) -> Callable[[CognitiveActionCandidate, PolyaState], CognitiveObservation]:
    def execute(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary="Produced an inspectable observation.",
        )

    return execute


def _registry_for(action_type: CognitiveActionType, capability_name: str) -> CapabilityRegistry:
    definition = CapabilityDefinition(
        name=capability_name,
        version="test-v1",
        supported_actions={action_type},
        estimated_cost=0.1,
    )
    registry = CapabilityRegistry()
    registry.register(FunctionCapability(definition, _noop_executor(definition)))
    return registry


@pytest.mark.parametrize(
    ("problem_type", "gap_type", "description", "source", "action", "capability"),
    [
        (
            "ambiguous_input",
            "missing_user_input",
            "which outcome the user values",
            "human input",
            CognitiveActionType.CLARIFY,
            "human_input",
        ),
        (
            "logic",
            "contradiction",
            "the premises conflict",
            "reframe",
            CognitiveActionType.REFRAME,
            "reasoner",
        ),
        (
            "mathematics",
            "numeric_computation",
            "the exact derived value",
            "calculator",
            CognitiveActionType.CALCULATE,
            "calculator",
        ),
        (
            "scientific_reasoning",
            "controlled_experiment",
            "which mechanism predicts the observation",
            "controlled test",
            CognitiveActionType.EXPERIMENT,
            "experiment",
        ),
        (
            "planning",
            "simulation",
            "whether the plan survives peak demand",
            "simulate alternatives",
            CognitiveActionType.SIMULATE,
            "simulator",
        ),
        (
            "data_analysis",
            "missing_baseline",
            "the historical metric baseline",
            "dataset measurement",
            CognitiveActionType.MEASURE,
            "measurement",
        ),
        (
            "software_debugging",
            "missing_code_context",
            "the failing code path",
            "repository and logs",
            CognitiveActionType.INSPECT,
            "inspector",
        ),
        (
            "technical_research",
            "current_external_fact",
            "the current supported API behavior",
            "official web source",
            CognitiveActionType.SEARCH,
            "web_search",
        ),
        (
            "analogical_transfer",
            "prior_case",
            "a structurally similar solved problem",
            "episodic memory",
            CognitiveActionType.RETRIEVE_MEMORY,
            "memory",
        ),
    ],
)
def test_same_controller_selects_state_appropriate_actions_across_domains(
    problem_type: str,
    gap_type: str,
    description: str,
    source: str,
    action: CognitiveActionType,
    capability: str,
) -> None:
    state = _state_with_gap(
        problem_type=problem_type,
        gap_type=gap_type,
        description=description,
        source=source,
    )
    registry = _registry_for(action, capability)

    decision = CognitiveController().decide(state, registry)

    assert decision.selected.action_type is action
    assert decision.selected.capability == capability
    assert decision.selected.target == description
    assert decision.state_fingerprint
    assert "explicit state" in decision.rationale


def test_controller_stops_when_required_capability_is_unavailable() -> None:
    state = _state_with_gap(
        problem_type="technical_research",
        gap_type="current_external_fact",
        description="the current specification",
        source="official web source",
    )

    decision = CognitiveController().decide(state, CapabilityRegistry())

    assert decision.selected.action_type is CognitiveActionType.STOP
    assert decision.rejected
    assert "unavailable" in decision.rejected[0].rationale


def test_privacy_constraint_rejects_unapproved_search_and_selects_approved_inspection() -> None:
    state = _state_with_gap(
        problem_type="technical_research",
        gap_type="current_external_fact",
        description="the current behavior affecting confidential customer records",
        source="official web source or local document",
    )
    problem = state["structured_problem"]
    assert problem is not None
    state["structured_problem"] = problem.model_copy(
        update={
            "constraints": [
                *problem.constraints,
                "Do not send sensitive data to an unapproved capability.",
            ]
        }
    )
    registry = CapabilityRegistry()
    web = CapabilityDefinition(
        name="web_search",
        version="test-v1",
        supported_actions={CognitiveActionType.SEARCH},
        estimated_cost=0.05,
    )
    inspector = CapabilityDefinition(
        name="inspector",
        version="test-v1",
        supported_actions={CognitiveActionType.INSPECT},
        approved_for_sensitive_data=True,
        estimated_cost=0.1,
    )
    registry.register(FunctionCapability(web, _noop_executor(web)))
    registry.register(FunctionCapability(inspector, _noop_executor(inspector)))

    decision = CognitiveController().decide(state, registry)

    assert decision.selected.action_type is CognitiveActionType.INSPECT
    assert decision.selected.capability == "inspector"
    assert any("privacy constraint" in item.rationale for item in decision.rejected)


def test_action_candidates_require_auditable_success_and_failure_conditions() -> None:
    with pytest.raises(ValueError):
        CognitiveActionCandidate.model_validate(
            {
                "id": "candidate-1",
                "action_type": "search",
                "target": "missing fact",
                "purpose": "Resolve a blocking fact.",
                "expected_observation": "An authoritative statement.",
                "expected_usefulness": 0.8,
                "estimated_cost": 0.1,
                "capability": "web_search",
            }
        )


@pytest.mark.parametrize("blocked", [None, "missing", "failed", "privacy", "budget"])
def test_external_gap_tries_feasible_acquisition_before_cheap_human_fallback(
    blocked: str | None,
) -> None:
    from app.cognition.contracts import CapabilityKind
    from app.cognition.task_model import CognitiveResourceBudget, budget_event

    state = _state_with_gap(
        problem_type="research",
        gap_type="current_external_fact",
        description="What did the mission measure?",
        source="official web source",
    )
    registry = CapabilityRegistry()
    human = CapabilityDefinition(
        name="human_input",
        version="test",
        kind=CapabilityKind.HUMAN,
        supported_actions={CognitiveActionType.ASK_HUMAN, CognitiveActionType.CLARIFY},
        estimated_cost=0.001,
        approved_for_sensitive_data=True,
    )
    registry.register(FunctionCapability(human, _noop_executor(human)))
    if blocked != "missing":
        search = CapabilityDefinition(
            name="web_search",
            version="test",
            kind=CapabilityKind.EXTERNAL,
            supported_actions={CognitiveActionType.SEARCH},
            estimated_cost=0.9,
            max_external_calls=1,
        )
        registry.register(FunctionCapability(search, _noop_executor(search)))
    if blocked == "failed":
        state["events"].append(
            StateEvent(
                engine_name="web_search",
                event_type="capability_observation",
                reasoning_mode=ReasoningMode.EXPLORE,
                summary="Provider failed.",
                metadata={
                    "action_type": "search",
                    "target": state["gaps"][0].description,
                    "capability": "web_search",
                    "status": "failed",
                },
            )
        )
    elif blocked == "privacy":
        assert state["structured_problem"] is not None
        state["structured_problem"].constraints.append("Keep private information local.")
    elif blocked == "budget":
        state["events"].append(budget_event(CognitiveResourceBudget(max_external_calls=0)))
    decision = CognitiveController().decide(state, registry)
    assert decision.selected.action_type is (
        CognitiveActionType.SEARCH if blocked is None else CognitiveActionType.STOP
    )
    if blocked is None:
        assert any("Deferred fallback" in item.rationale for item in decision.rejected)


def test_user_owned_information_remains_an_immediate_clarification() -> None:
    state = _state_with_gap(
        problem_type="planning",
        gap_type="user_owned_information",
        description="What is your spending limit?",
        source="user",
    )
    registry = _registry_for(CognitiveActionType.CLARIFY, "human_input")
    assert (
        CognitiveController().decide(state, registry).selected.action_type
        is CognitiveActionType.CLARIFY
    )
