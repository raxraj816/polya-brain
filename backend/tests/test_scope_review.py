"""Scope recovery preserves uncertainty, provenance and the original deliverable."""

import json

import pytest

from app.cognition import (
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
)
from app.cognition.kernel import apply_cognitive_observation
from app.cognition.model_gateway import CognitiveModelGateway
from app.cognition.report_metadata import scope_limitations
from app.cognition.scope_review import scope_review_available, scope_review_capability
from app.graph.state import StateEvent, create_initial_state
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.models.contracts import (
    EvidenceItem,
    KnowledgeGap,
    ReasoningMode,
    StructuredProblem,
    VerificationReport,
)

QUESTIONS = ["What is the documented lifetime?", "What is the actual incident cause?"]
TARGET = "Grouped public questions"
BOUNDARY = (
    "Explain the mechanism and propose a diagnostic; do not claim to have observed this incident."
)
EXCERPT = "A negative response is cached until its stated lifetime expires."


def state_with_stalled_research():
    state = create_initial_state(BOUNDARY)
    state["structured_problem"] = StructuredProblem(
        core_question="Explain and propose a check.",
        problem_type="research",
        knowns=["No incident observation is supplied."],
        unknowns=[TARGET],
        constraints=["Do not claim an actual diagnosis."],
        success_criteria=["Cite the documented rule.", "Propose a discriminating check."],
        required_data_sources=["official protocol documentation"],
    )
    state["gaps"] = [
        KnowledgeGap(
            description=TARGET,
            gap_type="current_external_fact",
            why_needed="Need facts.",
            suggested_source="official web source",
        )
    ]
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_web_source",
            source_uri="https://official.example.org/rule",
            claim=EXCERPT,
            raw_excerpt=EXCERPT,
            reliability_score=0.95,
            relevance_score=0.95,
        )
    ]
    for kind, metadata in [
        ("completed", {"status": "ok"}),
        (
            "gap_detection_completed",
            {"status": "ok", "public_question_groups": {TARGET: QUESTIONS}},
        ),
        ("evidence_candidates_acquired", {"acquisition_id": "a", "target_gap": TARGET}),
        ("evidence_evaluation_completed", {"acquisition_id": "a", "gap_resolved": False}),
    ]:
        state["events"].append(
            StateEvent(
                engine_name="constraint_discovery" if kind == "completed" else "test",
                event_type=kind,
                reasoning_mode=ReasoningMode.EXPLORE,
                summary="Fixture",
                metadata=metadata,
            )
        )
    return state


def proposal():
    return {
        "questions": [
            {
                "question_index": 0,
                "disposition": "supported",
                "reason": "Documented rule.",
                "evidence_index": 0,
                "evidence_quote": EXCERPT,
            },
            {
                "question_index": 1,
                "disposition": "nonblocking",
                "reason": "Actual cause remains unknown; only a proposed diagnostic is requested.",
                "user_scope_index": 0,
            },
        ]
    }


def capability(output):
    client = FakeLLMClient(
        [
            LLMResponse(
                provider="fake",
                model="fake",
                text=json.dumps(output),
                finish_reason="stop",
                usage=LLMTokenUsage(input_tokens=100, output_tokens=50),
            )
        ]
    )
    return scope_review_capability(CognitiveModelGateway(client, "fake")), client


def action():
    return CognitiveActionCandidate(
        id="review",
        action_type=CognitiveActionType.REFRAME,
        target=TARGET,
        purpose="Review scope",
        expected_observation="Scoped gaps",
        expected_usefulness=0.9,
        estimated_cost=0.1,
        capability="scope_reviewer",
        success_condition="Explicit scope",
        failure_condition="Invalid scope",
    )


def test_deferral_does_not_become_a_fact_or_weaken_success_criteria():
    state = state_with_stalled_research()
    cap, _ = capability(proposal())
    observation = cap.execute(action(), state)
    revised = apply_cognitive_observation(state, observation)
    assert revised["structured_problem"].core_question == state["structured_problem"].core_question
    assert (
        revised["structured_problem"].success_criteria
        == state["structured_problem"].success_criteria
    )
    assert revised["structured_problem"].knowns == state["structured_problem"].knowns
    assert revised["structured_problem"].unknowns == []
    assert len(revised["gaps"]) == 1 and revised["gaps"][0].description == QUESTIONS[0]
    assert revised["gaps"][0].filled and revised["gaps"][0].evidence_ids == ["state:evidence:0"]
    assert QUESTIONS[1] in scope_limitations(revised["structured_problem"].constraints)[0]
    assert not state["gaps"][0].filled  # Superseded, never marked solved.
    assert revised["events"][-1].metadata["original_gap"]["filled"] is False
    assert revised["verification"] is None and revised["final_answer"] is None
    assert not scope_review_available(revised, TARGET)


@pytest.mark.parametrize(
    "defect",
    [
        "missing_question",
        "duplicate_question",
        "invented_question",
        "bad_source",
        "invented_quote",
        "invented_scope",
    ],
)
def test_bad_scope_proposals_fail_closed_with_known_usage(defect):
    output = proposal()
    if defect == "missing_question":
        output["questions"].pop()
    elif defect == "duplicate_question":
        output["questions"].append(output["questions"][0])
    elif defect == "invented_question":
        output["questions"][1]["question_index"] = 9
    elif defect == "bad_source":
        output["questions"][0]["evidence_index"] = 99
    elif defect == "invented_quote":
        output["questions"][0]["evidence_quote"] = "This text never appeared in the source."
    else:
        output["questions"][1]["user_scope_index"] = 5
    cap, _ = capability(output)
    registry = CapabilityRegistry()
    registry.register(cap)
    state = state_with_stalled_research()
    result = CognitiveKernel(registry).run(state, max_cycles=1)
    assert result.observations[-1].payload["usage"]["input_tokens"] == 100
    if defect in {"missing_question", "duplicate_question", "invented_question"}:
        assert result.observations[-1].failure_kind == "invalid_scope_review"
        assert result.state["gaps"] == state["gaps"]
    else:
        event = next(
            e for e in result.state["events"] if e.event_type == "knowledge_scope_reviewed"
        )
        assert len(event.metadata["rejected_dispositions"]) == 1
        if defect in {"bad_source", "invented_quote"}:
            assert not result.state["gaps"][0].filled
            assert result.state["gaps"][0].description == QUESTIONS[0]
            assert result.state["structured_problem"].unknowns == [QUESTIONS[0]]
        else:
            assert result.state["gaps"][0].filled
            assert not result.state["gaps"][1].filled
            assert result.state["gaps"][1].description == QUESTIONS[1]
            assert (
                result.state["structured_problem"].constraints
                == state["structured_problem"].constraints
            )
    assert not scope_review_available(result.state, TARGET)


def test_needed_facts_remain_blocking_and_no_second_review_is_attempted():
    output = proposal()
    output["questions"][1] = {
        "question_index": 1,
        "disposition": "still_needed",
        "reason": "User requests actual proof.",
    }
    cap, _ = capability(output)
    state = state_with_stalled_research()
    revised = apply_cognitive_observation(state, cap.execute(action(), state))
    assert (
        revised["structured_problem"].success_criteria
        == state["structured_problem"].success_criteria
    )
    assert revised["structured_problem"].constraints == state["structured_problem"].constraints
    assert revised["structured_problem"].unknowns == [QUESTIONS[1]]
    assert revised["gaps"][0].filled
    assert revised["gaps"][1].description == QUESTIONS[1]
    assert not revised["gaps"][1].filled
    assert revised["events"][-1].metadata["scope_changed"] is False
    assert revised["events"][-1].metadata["coverage_changed"] is True
    assert not scope_review_available(revised, TARGET)


def test_still_needed_facts_survive_a_partial_deferral():
    output = proposal()
    output["questions"][0] = {
        "question_index": 0,
        "disposition": "still_needed",
        "reason": "Not fully supported.",
    }
    cap, _ = capability(output)
    state = state_with_stalled_research()
    revised = apply_cognitive_observation(state, cap.execute(action(), state))
    assert revised["structured_problem"].unknowns == [QUESTIONS[0]]
    assert not revised["gaps"][0].filled
    assert revised["gaps"][0].evidence_ids == []


def test_reframing_invalidates_previous_verification():
    state = state_with_stalled_research()
    state["verification"] = VerificationReport(
        passed=True,
        checks_run=["Previous check"],
        failed_checks=[],
        contradictions=[],
    )
    state["final_answer"] = "Old verdict"
    cap, _ = capability(proposal())
    revised = apply_cognitive_observation(state, cap.execute(action(), state))
    assert revised["verification"] is None and revised["final_answer"] is None


def test_controller_checks_privacy_and_budget_before_scope_review():
    from app.cognition.task_model import CognitiveResourceBudget, budget_event

    cap, _ = capability(proposal())
    registry = CapabilityRegistry()
    registry.register(cap)
    state = state_with_stalled_research()
    assert CognitiveController().decide(state, registry).selected.capability == "scope_reviewer"
    state["events"].append(budget_event(CognitiveResourceBudget(max_model_calls=0)))
    assert CognitiveController().decide(state, registry).selected.capability != "scope_reviewer"
    state = state_with_stalled_research()
    state["structured_problem"].constraints.append("Private data must remain private.")
    assert CognitiveController().decide(state, registry).selected.capability != "scope_reviewer"


def test_cli_report_preserves_deferred_questions_without_a_verdict():
    from app.cognition.contracts import CognitiveRunStatus
    from app.cognition.kernel import CognitiveRunResult
    from app.investigator.artifacts import report_from_result

    state = state_with_stalled_research()
    cap, _ = capability(proposal())
    revised = apply_cognitive_observation(state, cap.execute(action(), state))
    report = report_from_result(
        CognitiveRunResult(
            state=revised,
            status=CognitiveRunStatus.INSUFFICIENT_EVIDENCE,
            decisions=(),
            observations=(),
            cycles=1,
        )
    )
    assert any(QUESTIONS[1] in question for question in report.open_questions)
    assert report.confidence_level == "insufficient_evidence"
    assert report.checks_performed == []


def test_multiple_remaining_questions_stay_batched_and_keep_navigation_guidance():
    from app.acquisition.capabilities import _bounded_query, _evaluations_for_target
    from app.acquisition.page_reader import page_read_target

    state = state_with_stalled_research()
    questions = [QUESTIONS[0], "Published applicability limits?", "Published follow-up methods?"]
    state["events"][1].metadata["public_question_groups"] = {TARGET: questions}
    state["events"][-1].metadata.update(
        {
            "next_query": "Protocol applicability limits follow-up methods",
            "continuation": {
                "source_uri": None,
                "reason": "The current document covers only lifetime.",
            },
        }
    )
    output = proposal()
    output["questions"] = [
        output["questions"][0],
        *[
            {"question_index": i, "disposition": "still_needed", "reason": "Public facts missing."}
            for i in (1, 2)
        ],
    ]
    cap, _ = capability(output)
    revised = apply_cognitive_observation(state, cap.execute(action(), state))
    unresolved = [gap for gap in revised["gaps"] if not gap.filled]
    assert len(unresolved) == 1
    residual = unresolved[0].description
    assert questions[0] not in residual
    assert all(q in residual for q in questions[1:])
    assert _evaluations_for_target(revised, residual) == []  # No inherited coverage verdict.
    query, _, _ = _bounded_query(action().model_copy(update={"target": residual}), revised)
    assert query.startswith("Protocol applicability limits follow-up methods")
    assert page_read_target(revised, residual) is None  # Discovery hint survives regrouping.


def test_all_needed_review_does_not_rewrite_or_close_gaps():
    state = state_with_stalled_research()
    output = {
        "questions": [
            {"question_index": i, "disposition": "still_needed", "reason": "No adequate source."}
            for i in range(2)
        ]
    }
    cap, _ = capability(output)
    revised = apply_cognitive_observation(state, cap.execute(action(), state))
    assert revised["gaps"] == state["gaps"]
    assert revised["structured_problem"] == state["structured_problem"]
