"""Planning can pause for unobtainable evidence instead of inventing tool work."""

import json

import pytest
from pydantic import ValidationError

from app.cognition import (
    CapabilityRegistry,
    CognitiveKernel,
    CognitiveModelGateway,
    CognitiveRunStatus,
    CognitiveRuntime,
    CognitiveSessionRunner,
    accumulated_usage,
)
from app.cognition.model_capabilities import planner_capability
from app.cognition.model_contracts import PlanGenerationOutput
from app.graph.state import ExecutionOutput, StateEvent, create_initial_state
from app.investigator.artifacts import report_from_result
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    PlanTask,
    ReasoningMode,
    StructuredProblem,
    VerificationReport,
)

QUESTION = "Provide the actual full-suite command, result, and code revision tested."


def failed_execution_state():
    state = create_initial_state("Verify the full test suite passed; metadata alone is not proof.")
    state["structured_problem"] = StructuredProblem(
        core_question="Did the full test suite actually pass?",
        problem_type="execution_verification",
        knowns=["Only dependency metadata was supplied."],
        unknowns=[],
        constraints=["Do not infer execution from package metadata."],
        success_criteria=["Observe a passing full-suite result for the relevant revision."],
    )
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_local_artifact",
            source_uri="fixture://installed.json",
            claim="The artifact contains package metadata, not executed test results.",
            raw_excerpt='{"dependencies": [{"name":"example", "version":"1.0"}]}',
        )
    ]
    state["hypotheses"] = [
        Hypothesis(
            statement="Execution evidence is missing.",
            mechanism="No test output was supplied.",
            origin=HypothesisOrigin.DIRECT_REASONING,
        )
    ]
    state["plan"] = [
        PlanTask(id="inspect", action="Inspect the supplied evidence.", tool_name="executor")
    ]
    state["execution_outputs"] = [
        ExecutionOutput(
            task_id="inspect", summary="Only metadata found.", output={"test_results": None}
        )
    ]
    state["verification"] = VerificationReport(
        passed=False,
        checks_run=["Looked for full-suite test execution."],
        failed_checks=["Missing test command, result, and tested revision."],
        recommended_route="Acquire actual test records.",
    )
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints validated.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="task_gap_detector",
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Initial evidence inspected.",
            metadata={"status": "ok", "gap_count": 0},
        ),
    ]
    return state


def recovery_registry():
    client = FakeLLMClient(
        [
            LLMResponse(
                provider="fake",
                model="planner-model",
                text=json.dumps({"tasks": [], "clarifying_questions": [QUESTION]}),
                usage=LLMTokenUsage(input_tokens=40, output_tokens=20),
            )
        ]
    )
    registry = CapabilityRegistry()
    registry.register(planner_capability(CognitiveModelGateway(client, "planner-model")))
    return registry, client


def test_missing_observations_pause_recovery_without_erasing_failure_or_spending_on_tools():
    state = failed_execution_state()
    registry, client = recovery_registry()
    result = CognitiveKernel(registry).run(state, max_cycles=2)

    assert result.status is CognitiveRunStatus.NEEDS_INPUT
    assert len(client.requests) == 1
    assert result.state["plan"] == state["plan"]
    assert result.state["verification"] == state["verification"]
    assert result.state["final_answer"] is None
    assert result.state["reflection"] is None
    usage = accumulated_usage(result.state)
    assert usage.model_calls == 1
    assert usage.input_tokens == 40
    assert usage.output_tokens == 20
    report = report_from_result(result)
    assert report.open_questions == [QUESTION]
    assert report.failed_checks == state["verification"].failed_checks


def test_planner_questions_reach_the_durable_session_adapter():
    state = failed_execution_state()
    registry, _ = recovery_registry()
    runner = CognitiveSessionRunner(CognitiveRuntime(registry), initial_state=state, max_cycles=2)
    execution = runner(state["raw_input"], session_id=state["session_id"])
    assert execution.awaiting_user_input
    assert execution.clarifying_questions == (QUESTION,)
    assert execution.state["verification"] == state["verification"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tasks": [], "clarifying_questions": []},
        {"tasks": [{"id": "x", "action": "Run a check."}], "clarifying_questions": [QUESTION]},
        {"clarifying_questions": [QUESTION] * 4},
        {"clarifying_questions": [""]},
    ],
)
def test_planner_cannot_mix_work_and_questions_or_return_an_empty_recovery(payload):
    with pytest.raises(ValidationError):
        PlanGenerationOutput.model_validate(payload)


def test_existing_executable_plan_remains_valid():
    output = PlanGenerationOutput(
        tasks=[PlanTask(id="x", action="Check recorded evidence.", tool_name="executor")]
    )
    assert len(output.tasks) == 1
    assert output.clarifying_questions == []
