"""Delivery references save copying work, never replace review or execution evidence."""

import hashlib
import json
from copy import deepcopy

import pytest

from app.cognition.code_delivery import assemble_tested_code, code_delivery_context
from app.cognition.contracts import CognitiveActionCandidate
from app.cognition.execution_verification import coding_delivery_failures
from app.cognition.model_gateway import CognitiveModelGateway
from app.cognition.on_demand_capabilities import conclusion_checker_capability
from app.execution.sandbox import SandboxExecutionResult
from app.graph.state import ExecutionOutput, StateEvent, create_initial_state
from app.llm import FakeLLMClient, LLMResponse
from app.models.contracts import PlanTask, StructuredProblem


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def record(state, task_id, code):
    tests = ["assert twice(2) == 4"]
    state["plan"].append(
        PlanTask(
            id=task_id,
            action="Test candidate",
            tool_name="python_sandbox",
            params={"code": code, "tests": tests},
            risk_level="medium",
        )
    )
    result = SandboxExecutionResult(
        exit_code=0,
        stdout="",
        stderr="",
        runtime_ms=1,
        tests_run=1,
        test_results=[{"index": 1, "passed": True}],
    )
    state["execution_outputs"].append(
        ExecutionOutput(task_id=task_id, summary="Executed", output=result.model_dump(mode="json"))
    )
    state["events"].append(
        StateEvent(
            engine_name="python_sandbox",
            event_type="sandbox_execution_completed",
            reasoning_mode="execute",
            summary="Executed",
            metadata={
                "task_id": task_id,
                "code_sha256": digest(code),
                "tests_sha256": digest(json.dumps(tests, separators=(",", ":"))),
                "result_sha256": digest(result.model_dump_json()),
            },
        )
    )
    return f"[[POLYABRAIN_CODE:{digest(code.strip())}]]"


@pytest.fixture
def checked():
    state = create_initial_state("Implement twice(n).")
    state["structured_problem"] = StructuredProblem(
        core_question=state["raw_input"],
        problem_type="algorithm_implementation",
        success_criteria=["Double the integer."],
    )
    marker = record(state, "tested", "def twice(n):\n    return n * 2")
    return state, marker


@pytest.mark.parametrize(
    "change",
    [
        "code",
        "tests",
        "result",
        "missing_trace",
        "duplicate_trace",
        "wrong_producer",
        "failed",
        "timeout",
        "truncated",
        "missing_output",
        "duplicate_output",
    ],
)
def test_changed_or_missing_execution_binding_never_offers_references(checked, change):
    state, marker = checked
    if change in {"code", "tests"}:
        state["plan"][0].params[change] += "\n# changed" if change == "code" else ["assert True"]
    elif change == "result":
        state["execution_outputs"][0].output["stdout"] = "changed"
    elif change == "missing_trace":
        state["events"] = []
    elif change == "duplicate_trace":
        state["events"] *= 2
    elif change == "wrong_producer":
        state["events"][0].engine_name = "deliberator"
    elif change in {"failed", "timeout", "truncated"}:
        key, value = {
            "failed": ("exit_code", 1),
            "timeout": ("timed_out", True),
            "truncated": ("output_truncated", True),
        }[change]
        state["execution_outputs"][0].output[key] = value
    elif change == "missing_output":
        state["execution_outputs"] = []
    elif change == "duplicate_output":
        state["execution_outputs"] *= 2
    assert code_delivery_context(state) == {}
    with pytest.raises(ValueError):
        assemble_tested_code(state, marker)


@pytest.mark.parametrize(
    "shape", ["unknown", "duplicate", "inline", "fenced", "mixed", "malformed"]
)
def test_ambiguous_model_references_fail_closed(checked, shape):
    state, marker = checked
    answer = {
        "unknown": f"[[POLYABRAIN_CODE:{'0' * 64}]]",
        "duplicate": marker + "\n" + marker,
        "inline": "Implementation: " + marker,
        "fenced": "```python\n" + marker + "\n```",
        "mixed": marker + "\n```python\ndef twice(n): return 0\n```",
        "malformed": marker[:-1],
    }[shape]
    with pytest.raises(ValueError):
        assemble_tested_code(state, answer)


def test_exact_code_is_attached_and_provider_response_is_hash_bound(checked):
    state, marker = checked
    before = deepcopy(state)
    answer = "O(1) arithmetic, subject to integer size.\n\n" + marker
    rendered, binding = assemble_tested_code(state, answer)
    assert (
        rendered
        == "O(1) arithmetic, subject to integer size.\n\n```python\ndef twice(n):\n    return n * 2\n```"
    )
    assert coding_delivery_failures(state, rendered) == []
    assert binding["provider_answer_sha256"] == digest(answer)
    assert binding["delivered_answer_sha256"] == digest(rendered)
    assert binding["bindings"] == [
        {"task_id": "tested", "code_sha256": digest(state["plan"][0].params["code"])}
    ]
    assert state == before
    assert assemble_tested_code(state, rendered) == (rendered, None)


def test_multiple_deliverables_require_complete_coverage(checked):
    state, marker = checked
    second = record(state, "also-tested", "def twice(n):\n    return n + n")
    with pytest.raises(ValueError):
        assemble_tested_code(state, marker)
    rendered, binding = assemble_tested_code(state, marker + "\n\n" + second)
    assert binding["implementation_count"] == 2
    assert coding_delivery_failures(state, rendered) == []


@pytest.mark.parametrize(
    "problem_type", ["interval_intersection_scheduling", "data_analysis", None]
)
def test_model_problem_labels_cannot_disable_delivery_identity(checked, problem_type):
    state, marker = checked
    if problem_type is None:
        state["structured_problem"] = None
    else:
        state["structured_problem"].problem_type = problem_type
    assert code_delivery_context(state)
    rendered, _ = assemble_tested_code(state, marker)
    assert coding_delivery_failures(state, rendered) == []
    assert coding_delivery_failures(state, "```python\ndef twice(n): return 0\n```")
    assert coding_delivery_failures(state, "The measured result is four.") == []


def test_retired_code_reference_cannot_replace_current_recovery(checked):
    state, old = checked
    state["execution_outputs"][0].error = "Original attempt failed."
    new = record(state, "recovery", "def twice(n):\n    return n + n")
    state["plan"][1].params["supersedes_task_id"] = "tested"
    references = code_delivery_context(state)["tested_code_delivery"]["references"]
    assert [item["marker"] for item in references] == [new]
    with pytest.raises(ValueError):
        assemble_tested_code(state, old)
    rendered, _ = assemble_tested_code(state, new)
    assert coding_delivery_failures(state, rendered) == []


@pytest.mark.parametrize("verdict", ["failed_review", "invalid_reference", "passed"])
def test_review_owns_acceptance_and_invalid_delivery_discards_answer_and_learning(checked, verdict):
    state, marker = checked
    payload = {
        "report": {
            "passed": verdict != "failed_review",
            "checks_run": ["Inspected implementation and observed tests."],
            "failed_checks": ["Unsupported complexity claim."]
            if verdict == "failed_review"
            else [],
        }
    }
    if verdict != "failed_review":
        payload.update(
            final_answer=marker if verdict == "passed" else "Code: " + marker,
            reflection={"outcome_summary": "Tested integer doubling."},
        )
    client = FakeLLMClient([LLMResponse(provider="fake", model="fake", text=json.dumps(payload))])
    capability = conclusion_checker_capability(CognitiveModelGateway(client, "fake"))
    action = CognitiveActionCandidate(
        id="review",
        action_type="verify",
        target="candidate",
        purpose="Check independently",
        expected_observation="Verified result or failed checks",
        expected_usefulness=1,
        estimated_cost=0.1,
        capability="conclusion_checker",
        success_condition="Every check passes",
        failure_condition="Any check fails",
    )
    update = capability.execute(action, state).proposed_update
    assert len(client.requests) == 1
    request_context = json.loads(client.requests[0].messages[-1].content)
    assert (
        request_context["capability_context"]["tested_code_delivery"]["references"][0]["marker"]
        == marker
    )
    assert update.verification.passed is (verdict == "passed")
    assert any(e.event_type == "tested_code_attached" for e in update.trace_events_to_add) is (
        verdict == "passed"
    )
    if verdict != "passed":
        assert update.final_answer is None
        assert update.reflection is None
    else:
        assert coding_delivery_failures(state, update.final_answer) == []
