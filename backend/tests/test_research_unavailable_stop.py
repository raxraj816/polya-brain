"""Unavailable public research is not missing user-owned information."""

import pytest
from test_research_budget_stop import public_state, registry

from app.cognition import (
    CapabilityDefinition,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
    CognitiveObservation,
    CognitiveRunStatus,
    FunctionCapability,
    ObservationStatus,
)
from app.cognition.contracts import CapabilityKind
from app.cognition.task_model import accumulated_usage
from app.investigator.artifacts import report_from_result


def blocked_research(cause):
    state = public_state(used=0)
    capabilities = registry(search=False)
    calls = []
    if cause != "missing":
        definition = CapabilityDefinition(
            name="web_search",
            version="failure-fixture",
            kind=CapabilityKind.EXTERNAL,
            supported_actions={CognitiveActionType.SEARCH},
            max_external_calls=1,
        )

        def execute(action, _state):
            assert cause != "privacy", "Privacy-blocked research must never dispatch"
            calls.append(action)
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus(cause),
                summary="The fixture did not supply usable public evidence.",
                failure_kind="fixture_research_failure",
                payload={"external_calls": 1},
            )

        capabilities.register(FunctionCapability(definition, execute))
    if cause == "privacy":
        state["structured_problem"].constraints.append("Keep private information local.")
    return state, capabilities, calls


@pytest.mark.parametrize("cause", ["missing", "failed", "inconclusive", "blocked", "privacy"])
def test_unavailable_research_stops_without_human_request_or_retry(cause):
    state, capabilities, calls = blocked_research(cause)
    result = CognitiveKernel(capabilities).run(state)
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert len(calls) == (0 if cause in {"missing", "privacy"} else 1)
    assert result.state["evidence"] == state["evidence"]
    assert result.state["gaps"] == state["gaps"]
    assert result.state["final_answer"] is None
    assert result.state["reflection"] is None
    assert result.state["verification"] is None
    assert not any(o.proposed_update.questions_to_ask for o in result.observations)
    assert accumulated_usage(result.state).external_calls == len(calls)
    report = report_from_result(result)
    assert report.verification_status == "insufficient_evidence"
    assert "no safe research route" in report.recommended_next_action
    assert "budget" not in report.recommended_next_action
    assert report.open_questions == [state["gaps"][0].description]
    assert any("user-owned" in r.rationale for r in result.decisions[-1].rejected)
    if cause == "privacy":
        assert any("sensitive" in r.rationale for r in result.decisions[-1].rejected)
    if calls:
        assert any(o.failure_kind == "fixture_research_failure" for o in result.observations)


@pytest.mark.parametrize("private_first", [False, True])
def test_unavailable_public_research_preserves_real_private_clarification(private_first):
    state, capabilities, _ = blocked_research("missing")
    private_gap = state["gaps"][0].model_copy(
        update={"gap_type": "user_owned_information", "description": "Which private log applies?"}
    )
    state["gaps"].insert(0 if private_first else 1, private_gap)
    result = CognitiveKernel(capabilities).run(state)
    assert result.status is CognitiveRunStatus.NEEDS_INPUT
    assert result.decisions[-1].selected.action_type is CognitiveActionType.CLARIFY
    assert result.observations[-1].proposed_update.questions_to_ask == [
        "Please provide the missing information: Which private log applies?"
    ]


def test_missing_search_still_allows_inspection():
    decision = CognitiveController().decide(
        public_state(used=0), registry(search=False, inspect=True)
    )
    assert decision.selected.action_type is CognitiveActionType.INSPECT


def test_untyped_public_wording_still_allows_existing_human_fallback():
    state = public_state(used=0)
    state["gaps"][0].gap_type = "unspecified"
    result = CognitiveKernel(registry(search=False)).run(state)
    assert result.status is CognitiveRunStatus.NEEDS_INPUT
    assert result.decisions[-1].selected.action_type is CognitiveActionType.ASK_HUMAN
