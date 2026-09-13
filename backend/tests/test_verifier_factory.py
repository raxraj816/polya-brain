"""Executable verifier-factory tests for Chapter 13-E."""

from __future__ import annotations

from app.cognition import (
    CapabilityRegistry,
    CognitiveKernel,
    CognitiveRunStatus,
    DeterministicVerifierExecutor,
    VerifierFactory,
    deterministic_verification_available,
    verification_declarations_validated_event,
    verifier_factory_capability,
)
from app.graph.state import ExecutionOutput, StateEvent, create_initial_state
from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    PlanTask,
    ReasoningMode,
    StructuredProblem,
)


def _ready_state(*, tests: list[bool] | None = None):
    state = create_initial_state("Choose a release candidate.", session_id="multi-rule-verifier")
    state["structured_problem"] = StructuredProblem(
        core_question="Does candidate A satisfy every release rule?",
        problem_type="multi_rule_decision",
        knowns=["The test runner emitted structured observations."],
        constraints=["Do not waive a failed rule."],
        success_criteria=[
            "Every required test passes.",
            "The measured risk score is at most 0.2.",
            "The release decision is approved.",
        ],
    )
    state["hypotheses"] = [
        Hypothesis(
            statement="Candidate A satisfies every declared release rule.",
            mechanism="Apply the release rules to independent structured test output.",
            origin=HypothesisOrigin.DIRECT_REASONING,
            expected_signals=["All tests pass and risk is within threshold."],
            verification_checks=["Evaluate every declared release invariant."],
            falsification_criteria=["Any required release invariant fails."],
        )
    ]
    state["plan"] = [
        PlanTask(
            id="release-check",
            action="Run the independent release checks.",
            tool_name="test_runner",
            expected_output="Structured test, risk, and decision results.",
            params={
                "verification": [
                    {
                        "criterion_index": 0,
                        "operation": "all_true",
                        "actual_path": "tests",
                    },
                    {
                        "criterion_index": 1,
                        "operation": "less_than_or_equal",
                        "actual_path": "risk",
                        "expected": 0.2,
                    },
                    {
                        "criterion_index": 2,
                        "operation": "equals",
                        "actual_path": "approved",
                        "expected": True,
                    },
                ]
            },
        )
    ]
    state["execution_outputs"] = [
        ExecutionOutput(
            task_id="release-check",
            summary="The independent release check completed.",
            output={"tests": tests or [True, True, True], "risk": 0.12, "approved": True},
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
            summary="No blocking acquisition gap remains.",
            metadata={"status": "ok", "gap_count": 0},
        ),
    ]
    state["events"].append(verification_declarations_validated_event(state))
    return state


def test_factory_executes_every_multi_rule_criterion_without_a_model() -> None:
    state = _ready_state()
    registry = CapabilityRegistry()
    registry.register(verifier_factory_capability())

    result = CognitiveKernel(registry).run(state, max_cycles=2)

    assert result.status is CognitiveRunStatus.COMPLETED
    assert result.state["verification"] is not None
    assert result.state["verification"].passed
    assert len(result.state["verification"].checks_run) == 3
    assert result.state["final_answer"] == state["hypotheses"][0].statement
    assert any(event.event_type == "verifier_suite_synthesized" for event in result.state["events"])
    execution_event = next(
        event for event in result.state["events"] if event.event_type == "verifier_suite_executed"
    )
    assert execution_event.metadata["criterion_coverage"] == 1.0
    assert all(item["status"] == "passed" for item in execution_event.metadata["results"])


def test_present_case_verification_rejects_an_incorrect_reused_result() -> None:
    state = _ready_state(tests=[True, False, True])
    registry = CapabilityRegistry()
    registry.register(verifier_factory_capability())

    result = CognitiveKernel(registry).run(state, max_cycles=1)

    assert result.status is CognitiveRunStatus.MAX_CYCLES
    assert result.state["verification"] is not None
    assert not result.state["verification"].passed
    assert result.state["final_answer"] is None
    assert any("did not satisfy" in item for item in result.state["verification"].failed_checks)


def test_unknown_semantic_criterion_is_not_misrepresented_as_executable() -> None:
    state = _ready_state()
    state["structured_problem"] = state["structured_problem"].model_copy(
        update={
            "problem_type": "creative_strategy",
            "success_criteria": ["The strategy is meaningfully original and culturally resonant."],
        }
    )
    state["plan"] = []
    state["execution_outputs"] = []

    suite = VerifierFactory().synthesize(state)

    assert not deterministic_verification_available(state)
    assert len(suite.specifications) == 1
    assert not suite.specifications[0].executable
    assert suite.specifications[0].lifecycle.value == "proposed"
    executed = DeterministicVerifierExecutor().execute(suite, state)
    assert not executed.passed
    assert executed.results[0].status.value == "inconclusive"


def test_model_authored_plan_declaration_cannot_self_authorize_execution() -> None:
    state = _ready_state()
    state["events"] = [
        event
        for event in state["events"]
        if event.event_type != "verification_declarations_validated"
    ]

    suite = VerifierFactory().synthesize(state)

    assert not deterministic_verification_available(state)
    assert not any(item.executable for item in suite.specifications)
    assert any("untrusted or stale" in warning for warning in suite.warnings)


def test_artifact_verifier_requires_candidate_to_match_independent_evidence() -> None:
    state = _ready_state()
    state["structured_problem"] = StructuredProblem(
        core_question="What timeout does the manual require?",
        problem_type="explicit_artifact_lookup",
        success_criteria=["State the exact timeout from the supplied manual."],
    )
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_local_artifact",
            source_uri="file:///tmp/fictional-manual.txt",
            claim="The timeout is 37 ticks.",
            raw_excerpt="Rule Z7.4: The timeout is 37 ticks.",
            reliability_score=1.0,
            relevance_score=1.0,
        )
    ]
    state["hypotheses"] = [
        Hypothesis(
            statement="The timeout is 99 ticks.",
            origin=HypothesisOrigin.DIRECT_REASONING,
            verification_checks=["Check the manual."],
            falsification_criteria=["The manual states another value."],
        )
    ]

    suite = VerifierFactory().synthesize(state)
    result = DeterministicVerifierExecutor().execute(suite, state)

    assert not result.passed
    assert result.results[0].observed == {
        "eligible_evidence_count": 1,
        "claim_in_excerpt": True,
        "candidate_matches_claim": False,
    }
