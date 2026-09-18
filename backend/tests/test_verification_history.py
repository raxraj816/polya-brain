"""Failed checks remain inspectable after recovery invalidates the old verdict."""

import pytest

from app.cognition.contracts import (
    CognitiveObservation,
    CognitiveRunStatus,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.cognition.kernel import CognitiveRunResult, apply_cognitive_observation
from app.cognition.verification_history import (
    HISTORICAL_CHECK_PREFIX,
    HISTORICAL_NEXT_ACTION,
    historical_failure,
    verification_invalidated_event,
)
from app.graph.state import create_initial_state
from app.investigator.artifacts import report_from_result
from app.models.contracts import PlanTask, VerificationReport


def failed_report():
    return VerificationReport(
        passed=False,
        checks_run=["Looked for observed test execution."],
        failed_checks=["No test command, result, or code-state attribution was supplied."],
        recommended_route="Request actual test evidence.",
    )


def invalidated_state():
    state = create_initial_state("Verify that the tests passed.")
    state["verification"] = failed_report()
    observation = CognitiveObservation(
        action_id="recovery-plan",
        capability="planner",
        capability_version="test@1.0.0",
        status=ObservationStatus.SUCCEEDED,
        summary="Proposed a different way to acquire execution evidence.",
        proposed_update=CognitiveStateUpdate(
            plan_tasks_to_add=[PlanTask(id="recover", action="Acquire test execution evidence.")]
        ),
    )
    updated = apply_cognitive_observation(state, observation)
    assert state["verification"] is not None
    assert state["events"] == []
    assert updated["verification"] is None
    assert updated["final_answer"] is None
    assert updated["reflection"] is None
    return updated


def test_recovery_stop_reports_prior_failure_without_restoring_verification():
    state = invalidated_state()
    result = CognitiveRunResult(
        state=state,
        status=CognitiveRunStatus.INSUFFICIENT_EVIDENCE,
        decisions=(),
        observations=(),
        cycles=2,
    )
    report = report_from_result(result)
    assert report.failed_checks == [HISTORICAL_CHECK_PREFIX + failed_report().failed_checks[0]]
    assert report.checks_performed == [HISTORICAL_CHECK_PREFIX + failed_report().checks_run[0]]
    assert report.verification_status == "insufficient_evidence"
    assert report.confidence_level == "insufficient_evidence"
    assert report.recommended_next_action == HISTORICAL_NEXT_ACTION
    assert report.final_conclusion == "No verified conclusion is available."
    assert report.reflection is None
    assert state["verification"] is None


def test_current_verification_overrides_old_failure_diagnostics():
    state = invalidated_state()
    state["verification"] = VerificationReport(
        passed=True, checks_run=["Observed current test exit 0."]
    )
    state["final_answer"] = "The current test passed."
    report = report_from_result(
        CognitiveRunResult(
            state=state,
            status=CognitiveRunStatus.COMPLETED,
            decisions=(),
            observations=(),
            cycles=3,
        )
    )
    assert report.failed_checks == []
    assert report.checks_performed == ["Observed current test exit 0."]
    assert report.verification_status == "passed"


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {},
        {"version": "unknown"},
        {"version": "verification_history@0.1.0", "report": {"passed": False}},
    ],
)
def test_malformed_history_is_not_a_report(metadata):
    assert historical_failure(metadata) is None


def test_invalidated_pass_cannot_be_reused_or_replaced_with_older_failure():
    state = invalidated_state()
    event = verification_invalidated_event(
        VerificationReport(passed=True, checks_run=["Old check passed."]), action_id="later-change"
    )
    assert historical_failure(event.metadata) is None
    state["events"].append(event)
    report = report_from_result(
        CognitiveRunResult(
            state=state,
            status=CognitiveRunStatus.INSUFFICIENT_EVIDENCE,
            decisions=(),
            observations=(),
            cycles=3,
        )
    )
    assert report.failed_checks == []
    assert report.checks_performed == []
    assert report.verification_status == "insufficient_evidence"
