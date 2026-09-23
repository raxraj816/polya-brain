"""Chapter 13-I tests for deterministic evidence closure."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from app.cognition import (
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
    CognitiveModelGateway,
    CognitiveResourceBudget,
    CognitiveRunStatus,
    ObservationStatus,
    TrustedEvidenceAttester,
    accumulated_usage,
    apply_cognitive_observation,
    attested_evidence_procedure_capability,
    deterministic_evidence_attestation_event,
    on_demand_cognitive_capabilities,
)
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.llm import FakeLLMClient
from app.models.contracts import EvidenceItem, ReasoningMode, StructuredProblem

ATTESTER = TrustedEvidenceAttester(
    capability="trusted_measurement",
    version="trusted-measurement@1.0.0",
    allowed_source_types={"trusted_measurement_result"},
)
CRITERIA = [
    "Report the baseline and current value.",
    "Report the exact relative change.",
]
CLAIM = "Comparable baseline is 10.0%; current value is 13.0%; the exact relative change is +30.0%."


def _evidence() -> EvidenceItem:
    return EvidenceItem(
        source_type="trusted_measurement_result",
        source_uri="measurement://conversion/comparable-baseline-v1",
        claim=CLAIM,
        raw_excerpt=CLAIM,
        reliability_score=1.0,
        relevance_score=1.0,
    )


def _state() -> PolyaState:
    state = create_initial_state("Compare current conversion with baseline.", max_iterations=6)
    state["structured_problem"] = StructuredProblem(
        core_question="How did conversion change from the comparable baseline?",
        problem_type="data_analysis",
        domain="data_analysis",
        knowns=["The measurement definitions are comparable."],
        unknowns=[],
        constraints=["Use only the admitted deterministic measurement."],
        success_criteria=CRITERIA,
    )
    evidence = _evidence()
    state["evidence"] = [evidence]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints were validated.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="task_gap_detector",
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="No unresolved acquisition gap remains.",
            metadata={"status": "ok"},
        ),
        deterministic_evidence_attestation_event(
            evidence,
            producer_capability=ATTESTER.capability,
            producer_version=ATTESTER.version,
            covered_success_criteria=CRITERIA,
            checks_run=[
                "Recomputed baseline and current values from the trusted measurement.",
                "Recomputed (13.0 - 10.0) / 10.0 = 30.0%.",
            ],
        ),
    ]
    return state


def _action(action_type: CognitiveActionType) -> CognitiveActionCandidate:
    return CognitiveActionCandidate(
        id=f"closure-{action_type.value}",
        action_type=action_type,
        target="How did conversion change from the comparable baseline?",
        purpose="Close only after replaying deterministic evidence bindings.",
        expected_observation="A verified exact evidence claim.",
        expected_usefulness=1.0,
        estimated_cost=0.01,
        capability="attested_evidence_procedure",
        success_condition="Every attestation binding passes.",
        failure_condition="Any trust, integrity, provenance, or coverage binding fails.",
    )


def _registry(client: FakeLLMClient) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    gateway = CognitiveModelGateway(client, "must-not-run")
    for capability in on_demand_cognitive_capabilities(
        gateway,
        trusted_evidence_attesters=(ATTESTER,),
    ):
        registry.register(capability)
    return registry


def test_complete_attestation_closes_with_zero_post_evidence_model_calls() -> None:
    client = FakeLLMClient([])
    result = CognitiveKernel(_registry(client)).run(
        _state(),
        max_cycles=5,
        budget=CognitiveResourceBudget(max_model_calls=0),
    )

    assert result.status is CognitiveRunStatus.COMPLETED
    assert result.state["final_answer"] == CLAIM
    assert result.state["verification"] is not None
    assert result.state["verification"].passed
    assert result.state["reflection"] is not None
    assert accumulated_usage(result.state).model_calls == 0
    assert client.requests == []
    assert [decision.selected.capability for decision in result.decisions] == [
        "attested_evidence_procedure",
        "attested_evidence_procedure",
        "cognitive_controller",
    ]
    closure_events = [
        event
        for event in result.state["events"]
        if event.event_type.startswith("deterministic_evidence_closure_")
    ]
    assert {event.event_type for event in closure_events} == {
        "deterministic_evidence_closure_started",
        "deterministic_evidence_closure_verified",
    }


def _replace_attestation_metadata(
    state: PolyaState,
    update: dict[str, object],
) -> None:
    index = next(
        index
        for index, event in enumerate(state["events"])
        if event.event_type == "deterministic_evidence_attested"
    )
    event = state["events"][index]
    state["events"][index] = event.model_copy(update={"metadata": {**event.metadata, **update}})


def _forged_version(state: PolyaState) -> None:
    _replace_attestation_metadata(state, {"producer_version": "forged@9.9.9"})


def _changed_claim(state: PolyaState) -> None:
    state["evidence"] = [
        state["evidence"][0].model_copy(
            update={"claim": "Changed claim.", "raw_excerpt": "Changed claim."}
        )
    ]


def _partial_coverage(state: PolyaState) -> None:
    _replace_attestation_metadata(state, {"covered_success_criteria": CRITERIA[:1]})


def _multiple_claims(state: PolyaState) -> None:
    state["evidence"].append(
        _evidence().model_copy(
            update={
                "source_uri": "measurement://conversion/second-claim",
                "claim": "A second claim.",
                "raw_excerpt": "A second claim.",
            }
        )
    )


def _missing_provenance(state: PolyaState) -> None:
    state["evidence"] = [state["evidence"][0].model_copy(update={"source_uri": None})]


def _untrusted_source_type(state: PolyaState) -> None:
    state["evidence"] = [
        state["evidence"][0].model_copy(update={"source_type": "web_search_result"})
    ]
    _replace_attestation_metadata(state, {"source_type": "web_search_result"})


@pytest.mark.parametrize(
    "mutate",
    [
        _forged_version,
        _changed_claim,
        _partial_coverage,
        _multiple_claims,
        _missing_provenance,
        _untrusted_source_type,
    ],
    ids=[
        "forged-version",
        "changed-claim",
        "partial-coverage",
        "multiple-claims",
        "missing-provenance",
        "untrusted-source-type",
    ],
)
def test_invalid_attestation_cannot_construct_a_candidate(
    mutate: Callable[[PolyaState], None],
) -> None:
    state = _state()
    mutate(state)

    with pytest.raises(ValueError):
        attested_evidence_procedure_capability((ATTESTER,)).execute(
            _action(CognitiveActionType.HYPOTHESIZE),
            state,
        )

    assert state["final_answer"] is None
    assert state["verification"] is None


def test_verify_rechecks_replay_output_before_finalization() -> None:
    state = _state()
    capability = attested_evidence_procedure_capability((ATTESTER,))
    hypothesis = capability.execute(_action(CognitiveActionType.HYPOTHESIZE), state)
    state = apply_cognitive_observation(state, hypothesis)
    state["execution_outputs"] = [
        state["execution_outputs"][0].model_copy(update={"output": {"claim_sha256": "0" * 64}})
    ]

    with pytest.raises(ValueError, match="replay output"):
        capability.execute(_action(CognitiveActionType.VERIFY), state)

    assert state["final_answer"] is None


def test_failed_closure_candidate_falls_back_to_semantic_deliberation() -> None:
    state = _state()
    registry = _registry(FakeLLMClient([]))
    controller = CognitiveController()
    first = controller.decide(state, registry)
    assert first.selected.capability == "attested_evidence_procedure"
    state["events"].append(
        StateEvent(
            engine_name="attested_evidence_procedure",
            event_type="capability_observation",
            reasoning_mode=ReasoningMode.EXECUTE,
            summary="The attestation failed validation.",
            metadata={
                "action_type": CognitiveActionType.HYPOTHESIZE.value,
                "target": first.selected.target,
                "capability": "attested_evidence_procedure",
                "status": ObservationStatus.FAILED.value,
            },
        )
    )

    second = controller.decide(state, registry)

    assert second.selected.capability == "deliberator"


def test_task_without_attestation_uses_ordinary_semantic_route() -> None:
    state = _state()
    state["events"] = [
        event for event in state["events"] if event.event_type != "deterministic_evidence_attested"
    ]
    candidates = CognitiveController().generate_candidates(
        state,
        _registry(FakeLLMClient([])),
    )

    assert [candidate.capability for candidate in candidates] == ["deliberator"]
