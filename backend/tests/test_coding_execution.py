"""Coding tasks use runtime tools; proposed results cannot impersonate execution."""

import hashlib
import json
import shutil

import pytest
from pydantic import ValidationError

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.contracts import CognitiveActionType, CognitiveRunStatus
from app.cognition.execution_gaps import SANDBOX_GAP_TYPE, is_sandbox_work
from app.cognition.execution_verification import sandbox_verification_failures
from app.cognition.model_contracts import DeliberationCapabilityOutput
from app.cognition.model_gateway import CognitiveModelGateway
from app.cognition.on_demand_capabilities import (
    conclusion_checker_capability,
    deliberator_capability,
    task_gap_detector_capability,
)
from app.config import Settings
from app.graph.state import ExecutionOutput, create_initial_state
from app.llm import FakeLLMClient, LLMResponse
from app.models.contracts import Hypothesis, PlanTask, StructuredProblem
from app.problem_understanding import PROBLEM_UNDERSTANDING_EXAMPLES


def response(payload):
    return LLMResponse(provider="fake", model="test-model", text=json.dumps(payload))


def proposal():
    return {
        "hypotheses": [
            Hypothesis(
                statement="Count odd values using integer parity.", origin="direct_reasoning"
            ).model_dump(mode="json")
        ],
        "tasks": [
            {
                "id": "check-parity",
                "action": "Implement and test parity count.",
                "tool_name": "python_sandbox",
                "params": {
                    "code": "def count_odd(values):\n    return sum(v % 2 != 0 for v in values)",
                    "tests": [
                        "assert count_odd([-3, -2, 0, 1, 4]) == 2",
                        "assert count_odd([]) == 0",
                    ],
                },
                "risk_level": "medium",
            }
        ],
        "execution_outputs": [],
    }


def conclusion():
    return {
        "report": {
            "passed": True,
            "checks_run": ["Checked the parity count and empty input."],
            "failed_checks": [],
        },
        "final_answer": "```python\n" + proposal()["tasks"][0]["params"]["code"] + "\n```",
        "reflection": {"outcome_summary": "Tested a bounded Python implementation."},
    }


def ready_state():
    state = create_initial_state(
        "Implement count_odd(values) and test it in Python. "
        "Examples: count_odd([-3, -2, 0, 1, 4]) == 2; count_odd([]) == 0."
    )
    state["structured_problem"] = StructuredProblem(
        core_question=state["raw_input"],
        problem_type="algorithm_implementation",
        success_criteria=["Return the correct odd-value count including an empty input."],
    )
    return state


def action_for(capability, state):
    from app.cognition.controller import CognitiveController

    action_type = next(iter(capability.definition.supported_actions))
    from app.cognition.capabilities import CapabilityRegistry

    registry = CapabilityRegistry()
    registry.register(capability)
    return CognitiveController()._candidate(
        action_type,
        target=state["raw_input"],
        purpose="Test boundary.",
        expected="Auditable output.",
        usefulness=0.9,
        registry=registry,
        capability=capability.definition.name,
    )


def test_model_cannot_supply_fabricated_sandbox_execution():
    payload = proposal()
    payload["execution_outputs"] = [{"task_id": "check-parity", "summary": "Tests passed."}]
    with pytest.raises(ValidationError, match="sandbox outputs must come from execution"):
        DeliberationCapabilityOutput.model_validate(payload)


def test_pending_algorithm_stays_candidate_without_fabricated_support():
    state = ready_state()
    client = FakeLLMClient([response(proposal())])
    capability = deliberator_capability(
        CognitiveModelGateway(client, "test"), allow_python_sandbox=True
    )
    observed = capability.execute(action_for(capability, state), state)
    prompt = client.requests[0].messages[0].content
    assert "Keep unexecuted algorithm proposals at status='candidate'" in prompt
    assert "Predicted test results and desired complexity are not observed evidence" in prompt
    hypothesis = observed.proposed_update.hypotheses_to_add[0]
    assert hypothesis.status.value == "candidate"
    assert hypothesis.evidence_for == hypothesis.evidence_against == []
    assert observed.proposed_update.execution_outputs_to_add == []
    invalid = proposal()
    invalid["hypotheses"][0]["status"] = "selected"
    with pytest.raises(ValidationError, match="selected hypothesis requires supporting"):
        DeliberationCapabilityOutput.model_validate(invalid)


@pytest.mark.parametrize(
    "unknown",
    [
        "Actual production sandbox test results from yesterday.",
        "Customer sandbox credentials and invocation permissions.",
        "Private sandbox logs.",
        "Previous sandbox test results for the installed release.",
        "Required behavior when the input is malformed.",
        "Expected output for malformed sandbox input.",
        "Actual LeetCode judge results.",
    ],
)
def test_external_observations_and_requirements_are_not_internal_work(unknown):
    assert not is_sandbox_work(
        unknown, ["Python sandbox execution environment"], "Use Python sandbox."
    )


def test_current_test_outcomes_use_explicit_task_execution_context():
    unknown = "Whether all specified edge cases pass before the code is run."
    assert is_sandbox_work(unknown, [], "Implement the function and use the Python sandbox.")
    assert not is_sandbox_work(unknown, [], "Analyze the provided observations.")


def test_required_case_results_are_internal_execution_work():
    unknown = "Recorded sandbox execution results for the required cases, which do not exist until the code is run."
    context = (
        "Execute the implementation against the required cases in the available Python sandbox."
    )
    assert is_sandbox_work(unknown, [], context)


def test_algorithm_design_unknowns_are_deliberator_work():
    state = ready_state()
    state["structured_problem"].problem_type = "algorithm_implementation_and_verification"
    state["structured_problem"].unknowns = [
        "Optimal binary search partition index logic and edge handling for Python implementation."
    ]
    capability = task_gap_detector_capability(allow_python_sandbox=True)
    result = capability.execute(action_for(capability, state), state)
    assert result.proposed_update.gaps_to_add == []
    assert result.proposed_update.structured_problem.unknowns == []


def test_algorithm_boundary_unknowns_are_deliberator_work():
    state = ready_state()
    state["structured_problem"].problem_type = "algorithm_implementation_and_verification"
    state["structured_problem"].unknowns = [
        "Exact partition indexing and boundary conditions for binary search on the smaller array."
    ]
    capability = task_gap_detector_capability(allow_python_sandbox=True)
    result = capability.execute(action_for(capability, state), state)
    assert result.proposed_update.gaps_to_add == []
    assert result.proposed_update.structured_problem.unknowns == []


@pytest.mark.parametrize("enabled", [True, False])
def test_future_results_stay_unresolved_until_configured_tool_runs(enabled):
    state = ready_state()
    state["structured_problem"].unknowns = ["Actual sandbox test outcomes until execution occurs."]
    cap = task_gap_detector_capability(allow_python_sandbox=enabled)
    result = cap.execute(action_for(cap, state), state)
    gap = result.proposed_update.gaps_to_add[0]
    assert (gap.gap_type == SANDBOX_GAP_TYPE) is enabled
    assert gap.filled is False
    assert result.proposed_update.unknowns_to_resolve == []


@pytest.mark.parametrize("enabled", [False, True])
def test_pending_sandbox_tasks_require_configured_execution(enabled):
    client = FakeLLMClient([response(proposal())])
    capability = deliberator_capability(
        CognitiveModelGateway(client, "test"), allow_python_sandbox=enabled
    )
    state = ready_state()
    if not enabled:
        with pytest.raises(ValueError, match="unavailable execution tool"):
            capability.execute(action_for(capability, state), state)
        return
    observation = capability.execute(action_for(capability, state), state)
    if enabled:
        assert observation.status.value == "succeeded"
        assert len(observation.proposed_update.plan_tasks_to_add) == 1
        assert observation.proposed_update.execution_outputs_to_add == []


@pytest.mark.parametrize(
    "kind",
    ["missing", "failed", "incomplete", "passed", "empty", "timeout", "truncated", "duplicate"],
)
def test_semantic_pass_cannot_override_missing_or_failed_execution(kind):
    state = ready_state()
    state["plan"] = [PlanTask.model_validate(proposal()["tasks"][0])]
    if kind != "missing":
        state["execution_outputs"] = [
            ExecutionOutput(
                task_id="check-parity",
                summary="Observed execution.",
                output={
                    "exit_code": 1 if kind == "failed" else 0,
                    "stdout": "",
                    "stderr": "",
                    "runtime_ms": 1,
                    "tests_run": 2,
                    "test_results": []
                    if kind == "incomplete"
                    else [
                        {"index": 1, "passed": kind != "failed"},
                        {"index": 2, "passed": True},
                    ],
                },
            )
        ]
    if kind == "empty":
        state["plan"][0].params["tests"] = []
        state["execution_outputs"][0].output.update(tests_run=0, test_results=[])
    elif kind == "timeout":
        state["execution_outputs"][0].output["timed_out"] = True
    elif kind == "truncated":
        state["execution_outputs"][0].output["output_truncated"] = True
    elif kind == "duplicate":
        state["execution_outputs"].append(state["execution_outputs"][0])
    client = FakeLLMClient([response(conclusion())])
    capability = conclusion_checker_capability(CognitiveModelGateway(client, "test"))
    result = capability.execute(action_for(capability, state), state)
    assert result.status.value == "succeeded"
    assert result.proposed_update.verification.passed is (kind == "passed")
    assert len(client.requests) == (1 if kind == "passed" else 0)
    if kind != "passed":
        assert result.proposed_update.final_answer is None
        assert result.proposed_update.reflection is None
        assert sandbox_verification_failures(state)


@pytest.mark.parametrize(
    "recovery", ["explicit", "name_only", "dropped", "changed", "unrelated", "pending"]
)
def test_recovery_requires_link_retained_checks_and_fresh_execution(recovery):
    state = ready_state()
    original = PlanTask.model_validate(proposal()["tasks"][0])
    fixed = original.model_copy(
        update={
            "id": "check-parity-fixed",
            "action": "Re-execute corrected parity implementation and tests in the sandbox.",
        }
    )
    fixed.params = {**original.params, "supersedes_task_id": original.id}
    if recovery == "name_only":
        fixed.params.pop("supersedes_task_id")
    elif recovery == "dropped":
        fixed.params["tests"] = original.params["tests"][1:]
    elif recovery == "changed":
        fixed.params["tests"] = ["assert True", "assert True"]
    elif recovery == "unrelated":
        fixed.params["supersedes_task_id"] = "another-task"
    state["plan"] = [original, fixed]
    state["execution_outputs"] = [
        ExecutionOutput(
            task_id="check-parity",
            summary="Observed failure.",
            error="AssertionError",
            output={"exit_code": 1},
        ),
        ExecutionOutput(
            task_id="check-parity-fixed",
            summary="Observed passing execution.",
            output={
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "runtime_ms": 1,
                "tests_run": 2,
                "test_results": [
                    {"index": 1, "passed": True},
                    {"index": 2, "passed": True},
                ],
            },
        ),
    ]
    if recovery == "pending":
        state["execution_outputs"].pop()
    assert bool(sandbox_verification_failures(state)) is (recovery != "explicit")
    assert state["execution_outputs"][0].error == "AssertionError"


def test_recovery_does_not_retire_an_unrelated_failed_task():
    state = ready_state()
    original = PlanTask.model_validate(proposal()["tasks"][0])
    unrelated = original.model_copy(update={"id": "unrelated"})
    replacement = original.model_copy(
        update={
            "id": "fixed",
            "params": {**original.params, "supersedes_task_id": original.id},
        }
    )
    state["plan"] = [unrelated, original, replacement]
    state["execution_outputs"] = [
        ExecutionOutput(task_id="unrelated", summary="Failed.", error="AssertionError"),
        ExecutionOutput(task_id=original.id, summary="Failed.", error="AssertionError"),
        passing_output(replacement.id),
    ]
    failures = sandbox_verification_failures(state)
    assert len(failures) == 1
    assert "unrelated" in failures[0]


@pytest.mark.parametrize("shape", ["design", "findings"])
def test_plausible_explanation_cannot_bypass_independent_review(shape):
    state = ready_state()
    state["plan"] = [PlanTask.model_validate(proposal()["tasks"][0])]
    false_claim = {"time_complexity": "O(1)", "space_complexity": "O(1)"}
    explanation = (
        {
            "algorithm_design": {
                "partition_invariant": "Every odd value contributes once.",
                "complexity_analysis": false_claim,
            }
        }
        if shape == "design"
        else {"complexity": false_claim, "findings": ["Partition invariant: count each odd value."]}
    )
    state["execution_outputs"] = [
        passing_output("check-parity"),
        ExecutionOutput(task_id="analysis", summary="Unverified analysis.", output=explanation),
    ]
    client = FakeLLMClient(
        [
            response(
                {
                    "report": {
                        "passed": False,
                        "checks_run": ["Inspect iteration over all input values."],
                        "failed_checks": ["Claimed constant time is false; the code takes O(n)."],
                    }
                }
            )
        ]
    )
    capability = conclusion_checker_capability(CognitiveModelGateway(client, "test"))
    result = capability.execute(action_for(capability, state), state)
    assert len(client.requests) == 1
    assert not result.proposed_update.verification.passed
    assert result.proposed_update.final_answer is None
    assert result.proposed_update.reflection is None


def passing_output(task_id):
    return ExecutionOutput(
        task_id=task_id,
        summary="Observed passing execution.",
        output={
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "runtime_ms": 1,
            "tests_run": 2,
            "test_results": [{"index": 1, "passed": True}, {"index": 2, "passed": True}],
        },
    )


@pytest.mark.parametrize("change", ["missing", "rewritten", "extra", "unchanged"])
def test_delivery_must_match_executed_code(change):
    state = ready_state()
    state["plan"] = [PlanTask.model_validate(proposal()["tasks"][0])]
    state["execution_outputs"] = [passing_output("check-parity")]
    payload = conclusion()
    if change == "missing":
        payload["final_answer"] = "Done."
    elif change == "rewritten":
        payload["final_answer"] = "```python\ndef count_odd(values):\n    return 0\n```"
    elif change == "extra":
        payload["final_answer"] += "\n```python\ndef count_odd(values):\n    return 0\n```"
    client = FakeLLMClient([response(payload)])
    capability = conclusion_checker_capability(CognitiveModelGateway(client, "test"))
    result = capability.execute(action_for(capability, state), state)
    assert result.proposed_update.verification.passed is (change == "unchanged")
    if change != "unchanged":
        assert result.proposed_update.final_answer is None
        assert result.proposed_update.reflection is None


@pytest.mark.parametrize("enabled", [False, True])
def test_production_framing_receives_actual_tool_inventory(monkeypatch, enabled):
    output = PROBLEM_UNDERSTANDING_EXAMPLES[2].output.model_dump(mode="json")
    client = FakeLLMClient([response(output)])
    monkeypatch.setattr(
        "app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: client
    )
    settings = Settings(
        _env_file=None,
        OPENROUTER_API_KEY="local-fake-provider",
        OPENROUTER_MODEL="test-model",
        OPENROUTER_FALLBACK_MODELS="",
        SEARCH_PROVIDER="",
        ARTIFACT_ALLOWED_ROOTS="",
        CODE_EXECUTION_ENABLED=enabled,
    )
    runtime = build_cognitive_runtime(settings)
    runtime.run_problem("Investigate the service regression.", max_cycles=1)
    prompt = client.requests[0].messages[0].content
    context = prompt.split("RUNTIME_CAPABILITIES:")[1]
    assert ("python_sandbox executes" in context) is enabled
    assert ("Python sandbox execution is disabled" in context) is (not enabled)
    assert runtime._registry.supports("python_sandbox", CognitiveActionType.EXECUTE) is enabled


@pytest.mark.parametrize("execution_unknown", [False, True])
@pytest.mark.parametrize("scenario", ["passed", "recovery", "docker_recovery"])
@pytest.mark.parametrize("code_reference", [False, True])
def test_public_runtime_dispatches_sandbox_before_verification(
    monkeypatch, execution_unknown, scenario, code_reference
):
    from app.execution import DockerPythonSandbox, image_available
    from app.execution.sandbox import SandboxExecutionResult

    executed = []
    live = scenario == "docker_recovery"
    recovery = scenario != "passed"
    if live and (
        shutil.which("docker") is None or not image_available(DockerPythonSandbox().image)
    ):
        pytest.skip("requires Docker and the pinned Python sandbox image")
    real_execute = DockerPythonSandbox.execute

    def execute(self, code, tests=()):
        executed.append((code, tests))
        if live:
            return real_execute(self, code, tests)
        failed = recovery and len(executed) == 1
        return SandboxExecutionResult(
            exit_code=1 if failed else 0,
            stdout="",
            stderr="",
            runtime_ms=1,
            tests_run=2,
            test_results=[{"index": 1, "passed": not failed}, {"index": 2, "passed": True}],
        )

    monkeypatch.setattr(DockerPythonSandbox, "execute", execute)
    framing = PROBLEM_UNDERSTANDING_EXAMPLES[2].output.model_dump(mode="json")
    framing.update(
        literal_framing="Implement and test count_odd.",
        deeper_framing="Count odd integers.",
        goal="Implement and test count_odd.",
        problem_type="algorithm_implementation",
        wrong_problem_warning=None,
        given=["Input is a list of integers."],
        unknown=["Actual sandbox execution results before running the code."]
        if execution_unknown
        else [],
        constraints=[],
        success_criteria=ready_state()["structured_problem"].success_criteria,
        required_data_sources=[],
    )
    first = proposal()
    scripted = [response(framing)]
    if recovery:
        first["tasks"][0]["params"]["code"] = (
            "def count_odd(values):\n    return sum(v > 0 and v % 2 != 0 for v in values)"
        )
        replacement = proposal()["tasks"][0]
        replacement["id"] = "check-parity-replacement"
        replacement["params"]["supersedes_task_id"] = "check-parity"
        scripted.extend([response(first), response({"tasks": [replacement]})])
    else:
        scripted.append(response(first))
    final = conclusion()
    if code_reference:
        code = proposal()["tasks"][0]["params"]["code"]
        final["final_answer"] = f"[[POLYABRAIN_CODE:{hashlib.sha256(code.encode()).hexdigest()}]]"
    scripted.append(response(final))
    client = FakeLLMClient(scripted)
    monkeypatch.setattr(
        "app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: client
    )
    runtime = build_cognitive_runtime(
        Settings(
            _env_file=None,
            OPENROUTER_API_KEY="local-fake-provider",
            OPENROUTER_MODEL="test-model",
            OPENROUTER_FALLBACK_MODELS="",
            SEARCH_PROVIDER="",
            ARTIFACT_ALLOWED_ROOTS="",
            CODE_EXECUTION_ENABLED=True,
        )
    )
    result = runtime.run_problem(ready_state()["raw_input"])
    assert result.status is CognitiveRunStatus.COMPLETED
    assert len(executed) == (2 if recovery else 1)
    assert result.state["structured_problem"].unknowns == []
    assert all(gap.filled for gap in result.state["gaps"])
    observations = [
        e.metadata.get("capability")
        for e in result.state["events"]
        if e.event_type == "capability_observation"
    ]
    assert (
        observations.index("deliberator")
        < observations.index("python_sandbox")
        < observations.index("conclusion_checker")
    )
    assert len(client.requests) == (4 if recovery else 3)
    assert result.state["final_answer"] == conclusion()["final_answer"]
    attachments = [e for e in result.state["events"] if e.event_type == "tested_code_attached"]
    assert len(attachments) == int(code_reference)
    if code_reference:
        assert attachments[0].metadata["implementation_count"] == 1
        assert "tested_code_delivery" in client.requests[-1].messages[-1].content
    if recovery:
        assert executed[0][1] == executed[1][1]
        assert result.state["execution_outputs"][0].error
        assert not result.state["execution_outputs"][1].error
        assert result.state["verification"].passed
        assert result.state["final_answer"] == conclusion()["final_answer"]
        assert observations.count("conclusion_checker") == 2
