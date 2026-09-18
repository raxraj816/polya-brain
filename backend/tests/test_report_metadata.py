"""Residual uncertainty remains visible without changing a conditional outcome."""

import pytest
from pydantic import ValidationError

from app.cognition.contracts import CognitiveRunStatus
from app.cognition.kernel import CognitiveRunResult
from app.cognition.report_metadata import (
    ConclusionReportMetadata,
    report_metadata_event,
    report_questions,
)
from app.graph.state import create_initial_state
from app.investigator.artifacts import report_from_result
from app.models.contracts import VerificationReport


def _event(answer="Conditional proposal based on supplied evidence.", questions=None):
    return report_metadata_event(
        answer=answer,
        metadata=ConclusionReportMetadata(
            open_questions=questions
            if questions is not None
            else ["Which target environments apply?"]
        ),
        engine_name="conclusion_checker",
    )


def test_questions_are_bound_to_the_exact_answer_and_deduplicated():
    event = _event(
        questions=[" Which target environments apply? ", "Which target environments apply?"]
    )
    assert report_questions(event.metadata, "Conditional proposal based on supplied evidence.") == [
        "Which target environments apply?"
    ]
    assert report_questions(event.metadata, "A later answer with different conditions.") == []
    assert report_questions(event.metadata, None) == []
    assert (
        report_questions(
            {**event.metadata, "version": "unknown"},
            "Conditional proposal based on supplied evidence.",
        )
        == []
    )


@pytest.mark.parametrize(
    "questions", [[""], ["x" * 501], ["Question?"] * 9, "not a question list", None]
)
def test_invalid_metadata_cannot_enter_the_report(questions):
    with pytest.raises(ValidationError):
        ConclusionReportMetadata(open_questions=questions)
    event = _event()
    assert (
        report_questions(
            {**event.metadata, "open_questions": questions},
            "Conditional proposal based on supplied evidence.",
        )
        == []
    )


def test_completed_cli_report_retains_nonblocking_questions_and_latest_metadata_wins():
    state = create_initial_state("Propose a conditional plan.")
    state["final_answer"] = "Conditional proposal based on supplied evidence."
    state["verification"] = VerificationReport(
        passed=True, checks_run=["Checked the proposal scope."]
    )
    state["events"] = [_event()]
    result = CognitiveRunResult(
        state=state, status=CognitiveRunStatus.COMPLETED, decisions=[], observations=[], cycles=1
    )
    report = report_from_result(result)
    assert report.verification_status == "passed"
    assert report.open_questions == ["Which target environments apply?"]
    assert state["gaps"] == []
    state["events"].append(_event(questions=[]))
    assert report_from_result(result).open_questions == []


def test_failed_cli_outcome_does_not_reuse_completed_answer_metadata():
    state = create_initial_state("Verify a proposal.")
    state["events"] = [_event()]
    state["verification"] = VerificationReport(
        passed=False, checks_run=["Evidence missing."], failed_checks=["Need observed results."]
    )
    result = CognitiveRunResult(
        state=state,
        status=CognitiveRunStatus.INSUFFICIENT_EVIDENCE,
        decisions=[],
        observations=[],
        cycles=1,
    )
    assert report_from_result(result).open_questions == []
