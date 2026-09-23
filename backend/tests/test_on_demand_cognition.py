"""Chapter 13-D task-model, budget, and fused-cognition tests."""

from __future__ import annotations

from app.cognition import (
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveKernel,
    CognitiveModelGateway,
    CognitiveResourceBudget,
    CognitiveRunStatus,
    accumulated_usage,
    derive_task_model,
    on_demand_cognitive_capabilities,
    task_gap_detector_capability,
)
from app.cognition.capabilities import CapabilityRegistry
from app.graph.state import StateEvent, create_initial_state
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.models.contracts import (
    EvidenceItem,
    KnowledgeGap,
    ReasoningMode,
    StructuredProblem,
)


def _response(text: str) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="same-fake-model",
        text=text,
        finish_reason="stop",
        usage=LLMTokenUsage(input_tokens=60, output_tokens=30),
    )


def _ready_state():
    state = create_initial_state(
        "Use the supplied fictional manual evidence to determine the Zephyra timeout.",
        session_id="unfamiliar-zephyra",
        max_iterations=4,
    )
    state["structured_problem"] = StructuredProblem(
        core_question="What timeout does Zephyra protocol revision 7 require?",
        problem_type="unfamiliar_manual_lookup",
        domain="fictional_protocol",
        knowns=["The Zephyra protocol is fictional and revision 7 is in scope."],
        unknowns=[],
        constraints=["Use only supplied revision-7 evidence."],
        success_criteria=["State the timeout and cite the supplied revision-7 rule."],
    )
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_local_artifact",
            source_uri="fixture://zephyra/revision-7",
            claim="Zephyra revision 7 requires a 37-tick request timeout.",
            raw_excerpt="Rule Z7.4: request_timeout_ticks = 37.",
            reliability_score=1.0,
            relevance_score=1.0,
        )
    ]
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
            summary="No blocking gap remains after supplied evidence.",
            metadata={"status": "ok", "gap_count": 0},
        ),
    ]
    return state


def _deliberation_json() -> str:
    return """{
      "hypotheses": [{
        "statement": "Zephyra revision 7 requires a 37-tick timeout.",
        "mechanism": "Apply rule Z7.4 from the supplied fictional manual.",
        "origin": "direct_reasoning",
        "analogical_source_ids": [],
        "expected_signals": ["Rule Z7.4 states 37 ticks."],
        "evidence_for": ["fixture://zephyra/revision-7"],
        "evidence_against": [],
        "verification_checks": ["Compare the conclusion with rule Z7.4."],
        "falsification_criteria": ["Revision 7 states a value other than 37."],
        "confidence": 0.9,
        "selection_rationale": null,
        "status": "candidate"
      }],
      "tasks": [{
        "id": "check-z7-4",
        "action": "Compare the candidate timeout with supplied rule Z7.4.",
        "tool_name": "deliberator",
        "params": {},
        "depends_on": [],
        "expected_output": "The value and source agree.",
        "risk_level": "low"
      }],
      "execution_outputs": [{
        "task_id": "check-z7-4",
        "summary": "The candidate matches the supplied revision-7 rule.",
        "output": {"value": 37, "source_uri": "fixture://zephyra/revision-7"},
        "artifact_ids": [],
        "error": null
      }]
    }"""


def _conclusion_json() -> str:
    return """{
      "report": {
        "passed": true,
        "checks_run": ["Checked the sole success criterion against rule Z7.4 and its source URI."],
        "failed_checks": [],
        "contradictions": [],
        "confidence_delta": 0.2,
        "recommended_route": "finalize"
      },
      "final_answer": "Zephyra revision 7 requires a 37-tick request timeout (rule Z7.4).",
      "reflection": {
        "outcome_summary": "Resolved the fictional protocol lookup from supplied evidence.",
        "what_worked": ["Used the revision-scoped manual rule."],
        "what_failed": [],
        "reusable_lessons": ["For versioned fictional protocols, bind the answer to the requested revision."],
        "memory_updates": [],
        "strategy_notes": ["revision_scoped_authoritative_lookup"],
        "follow_up_actions": []
      }
    }"""


def test_explicit_unknowns_become_gaps_without_a_model_call() -> None:
    state = create_initial_state("Read fictional.txt.", session_id="explicit-gap")
    state["structured_problem"] = StructuredProblem(
        core_question="What value does the fictional manual specify?",
        problem_type="unfamiliar_manual_lookup",
        unknowns=["the revision-7 timeout in fictional.txt"],
        success_criteria=["State the revision-7 timeout."],
        required_data_sources=["local manual artifact"],
    )
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints completed.",
            metadata={"status": "ok"},
        )
    ]
    registry = CapabilityRegistry()
    registry.register(task_gap_detector_capability())

    result = CognitiveKernel(registry).run(
        state,
        max_cycles=1,
        budget=CognitiveResourceBudget(max_model_calls=0),
    )

    assert result.decisions[0].selected.action_type is CognitiveActionType.DETECT_GAPS
    assert result.observations[0].payload == {"procedure": "deterministic", "model_calls": 0}
    assert result.state["gaps"][0].suggested_source == "local artifact"
    assert accumulated_usage(result.state).model_calls == 0


def test_local_artifact_unknowns_share_one_deterministic_acquisition_gap() -> None:
    state = create_initial_state("Inspect issue.md and worker.py.", session_id="batched-gap")
    original_unknowns = [
        "The failing function in worker.py.",
        "The expected behavior declared in issue.md.",
        "The regression condition in worker.py.",
    ]
    state["structured_problem"] = StructuredProblem(
        core_question="Why does the worker fail?",
        problem_type="technical_investigation",
        unknowns=original_unknowns,
        success_criteria=["Identify and verify the failure mechanism."],
        required_data_sources=["explicit local artifact issue.md and worker.py"],
    )
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints completed.",
            metadata={"status": "ok"},
        )
    ]
    registry = CapabilityRegistry()
    registry.register(task_gap_detector_capability())

    result = CognitiveKernel(registry).run(
        state,
        max_cycles=1,
        budget=CognitiveResourceBudget(max_model_calls=0),
    )

    assert len(result.state["gaps"]) == 1
    gap = result.state["gaps"][0]
    assert gap.suggested_source == "local artifact"
    assert all(unknown in gap.description for unknown in original_unknowns)
    assert result.state["structured_problem"] is not None
    assert result.state["structured_problem"].unknowns == [gap.description]
    event = next(
        item for item in result.state["events"] if item.event_type == "gap_detection_completed"
    )
    assert event.metadata["batched_local_artifact_unknown_count"] == 3


def test_task_model_exposes_constraint_and_evidence_admission_impasses() -> None:
    state = create_initial_state("Inspect a supplied manual.", session_id="task-model-stages")
    state["structured_problem"] = StructuredProblem(
        core_question="What does the supplied manual require?",
        problem_type="explicit_artifact_lookup",
    )

    assert derive_task_model(state).impasse.kind.value == "constraint"

    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints completed.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="inspector",
            event_type="evidence_candidates_acquired",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Candidates acquired.",
            metadata={"acquisition_id": "acq-test"},
        ),
    ]

    snapshot = derive_task_model(state)
    assert snapshot.impasse.kind.value == "evidence"
    assert snapshot.impasse.target == "acq-test"


def test_fused_semantic_stages_complete_with_two_model_calls() -> None:
    client = FakeLLMClient([_response(_deliberation_json()), _response(_conclusion_json())])
    gateway = CognitiveModelGateway(client, "same-fake-model")
    registry = CapabilityRegistry()
    for capability in on_demand_cognitive_capabilities(gateway):
        registry.register(capability)

    result = CognitiveKernel(registry).run(
        _ready_state(),
        max_cycles=4,
        budget=CognitiveResourceBudget(
            max_model_calls=8,
            max_external_calls=0,
            max_output_tokens=10_000,
        ),
    )

    assert result.status is CognitiveRunStatus.COMPLETED
    assert [decision.selected.action_type for decision in result.decisions] == [
        CognitiveActionType.HYPOTHESIZE,
        CognitiveActionType.VERIFY,
        CognitiveActionType.STOP,
    ]
    assert len(client.requests) == 2
    assert accumulated_usage(result.state).model_calls == 2
    assert result.state["reflection"] is not None
    assert result.state["final_answer"] is not None
    assert any(event.event_type == "task_model_snapshot" for event in result.state["events"])
    assert derive_task_model(result.state).impasse.kind.value == "none"


def test_worst_case_reservation_prevents_budget_overrun_before_model_call() -> None:
    client = FakeLLMClient([_response(_deliberation_json())])
    gateway = CognitiveModelGateway(client, "same-fake-model")
    registry = CapabilityRegistry()
    for capability in on_demand_cognitive_capabilities(gateway):
        registry.register(capability)

    result = CognitiveKernel(registry).run(
        _ready_state(),
        max_cycles=2,
        budget=CognitiveResourceBudget(
            max_model_calls=1,
            max_external_calls=0,
            max_output_tokens=10_000,
        ),
    )

    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert result.decisions[0].selected.action_type is CognitiveActionType.STOP
    assert len(client.requests) == 0
    assert any(
        "hard cognitive budget" in rejected.rationale for rejected in result.decisions[0].rejected
    )


def test_model_route_is_part_of_capability_version_and_timeout_contract() -> None:
    first_gateway = CognitiveModelGateway(FakeLLMClient([]), "provider/model-a")
    second_gateway = CognitiveModelGateway(FakeLLMClient([]), "provider/model-b")
    first = {
        item.definition.name: item.definition
        for item in on_demand_cognitive_capabilities(
            first_gateway,
            max_output_tokens_per_call=1800,
            timeout_seconds_per_call=60.0,
        )
    }
    second = {
        item.definition.name: item.definition
        for item in on_demand_cognitive_capabilities(second_gateway)
    }

    assert first_gateway.model_route == "provider/model-a"
    assert first["deliberator"].version != second["deliberator"].version
    assert first["conclusion_checker"].version != second["conclusion_checker"].version
    assert first["deliberator"].max_output_tokens == 1800
    assert first["deliberator"].timeout_seconds == 60.0


def test_json_dependency_evidence_routes_to_inspection_not_measurement_or_user() -> None:
    from app.cognition.controller import _preferred_action_for_gap
    from app.cognition.on_demand_capabilities import _gap_type, _source_for_unknown

    unknown = "Which compatible versions satisfy the files in /Users/reviewer/audit.json?"
    source = _source_for_unknown(unknown, ["explicit local artifact /Users/reviewer/audit.json"])
    assert source == "local artifact"
    gap = KnowledgeGap(
        description=unknown,
        gap_type=_gap_type(unknown, source),
        suggested_source=source,
        why_needed="Resolve dependency constraints.",
    )
    assert _preferred_action_for_gap(gap) is CognitiveActionType.INSPECT


def test_explicit_measurement_and_human_sources_keep_their_routing() -> None:
    from app.cognition.controller import _preferred_action_for_gap
    from app.cognition.on_demand_capabilities import _gap_type, _source_for_unknown

    for unknown, sources, expected in [
        (
            "Compute the median request latency",
            ["dataset measurement in requests.csv"],
            CognitiveActionType.MEASURE,
        ),
        ("The user's risk preference", ["human input"], CognitiveActionType.CLARIFY),
    ]:
        source = _source_for_unknown(unknown, sources)
        gap = KnowledgeGap(
            description=unknown,
            gap_type=_gap_type(unknown, source),
            suggested_source=source,
            why_needed="Required for this decision.",
        )
        assert _preferred_action_for_gap(gap) is expected


def test_source_filenames_do_not_imply_numeric_or_measurement_operations() -> None:
    from app.cognition.on_demand_capabilities import _source_for_unknown

    for path in ("/Users/numeric/table/policy.json", "median.json", "calculator.toml"):
        assert _source_for_unknown("Find the configured policy", [path]) == "local artifact"


def test_conclusion_checker_records_residual_questions_without_blocking_completion():
    import json

    from app.cognition.report_metadata import REPORT_METADATA_EVENT, report_questions

    conclusion = json.loads(_conclusion_json())
    conclusion["report_metadata"] = {
        "open_questions": ["Does the next revision retain this timeout?"]
    }
    client = FakeLLMClient([_response(_deliberation_json()), _response(json.dumps(conclusion))])
    registry = CapabilityRegistry()
    for capability in on_demand_cognitive_capabilities(
        CognitiveModelGateway(client, "same-fake-model")
    ):
        registry.register(capability)
    result = CognitiveKernel(registry).run(_ready_state(), max_cycles=8)
    assert result.status is CognitiveRunStatus.COMPLETED
    event = next(
        event for event in result.state["events"] if event.event_type == REPORT_METADATA_EVENT
    )
    assert report_questions(event.metadata, result.state["final_answer"]) == [
        "Does the next revision retain this timeout?"
    ]


def test_public_source_subject_words_do_not_request_local_execution():
    from app.cognition.on_demand_capabilities import _source_for_unknown

    sources = ["official mission orbital-measurement pages", "official agency experiment reports"]
    for unknown in [
        "What was the measurement?",
        "Which experiment established the result?",
        "What does the document say?",
        "Which numeric result was reported?",
    ]:
        assert _source_for_unknown(unknown, sources) == "official web source"
    assert _source_for_unknown("The user's preference", sources) == "human input"
    assert _source_for_unknown("Inspect local /home/test/log.txt", sources) == "local artifact"
    assert (
        _source_for_unknown("Compute the median", ["official documentation", "dataset measurement"])
        == "dataset measurement"
    )


def test_public_questions_share_acquisition_without_losing_constituent_requirements():
    from app.cognition.on_demand_capabilities import task_gap_detector_capability

    state = _ready_state()
    state["structured_problem"].unknowns = ["What was observed?", "What remains uncertain?"]
    state["structured_problem"].required_data_sources = ["official research results pages"]
    state["gaps"] = []
    capability = task_gap_detector_capability()
    action = CognitiveActionCandidate(
        id="detect",
        action_type=CognitiveActionType.DETECT_GAPS,
        target="research",
        purpose="Find gaps",
        expected_observation="Gaps",
        expected_usefulness=0.9,
        estimated_cost=0,
        capability="task_gap_detector",
        success_condition="Gaps represented",
        failure_condition="Missing questions",
    )
    result = capability.execute(action, state)
    gaps = result.proposed_update.gaps_to_add
    assert len(gaps) == 1
    assert all(q in gaps[0].description for q in state["structured_problem"].unknowns)
    assert result.proposed_update.structured_problem.unknowns == [gaps[0].description]
