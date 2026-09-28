"""Necessary execution checks; passing them is not proof of correctness."""

import re
from collections import Counter

from pydantic import ValidationError

from app.execution.sandbox import SandboxExecutionResult
from app.graph.state import PolyaState
from app.models.contracts import PlanTask


def _execution_failures(state: PolyaState, task: PlanTask) -> list[str]:
    outputs = [item for item in state["execution_outputs"] if item.task_id == task.id]
    if len(outputs) != 1 or outputs[0].error:
        return [f"Sandbox task {task.id} has missing, ambiguous or failed execution."]
    try:
        result = SandboxExecutionResult.model_validate(outputs[0].output)
    except ValidationError:
        return [f"Sandbox task {task.id} has no valid execution result."]
    tests = task.params.get("tests", [])
    code = task.params.get("code")
    if (
        not isinstance(code, str)
        or not code.strip()
        or not isinstance(tests, list)
        or not tests
        or any(not isinstance(test, str) or not test.strip() for test in tests)
        or result.exit_code != 0
        or result.timed_out
        or result.output_truncated
        or result.tests_run != len(tests)
        or len(result.test_results) != result.tests_run
        or [test.index for test in result.test_results] != list(range(1, result.tests_run + 1))
        or any(not test.passed for test in result.test_results)
    ):
        return [f"Sandbox task {task.id} did not complete all declared checks successfully."]
    return []


def _recovery_links(state: PolyaState) -> tuple[set[str], list[str]]:
    """Only an explicit, tested replacement retaining every check retires a task."""
    earlier: dict[str, PlanTask] = {}
    superseded: set[str] = set()
    failures: list[str] = []
    for task in state["plan"]:
        if task.tool_name != "python_sandbox":
            continue
        predecessor = task.params.get("supersedes_task_id")
        if predecessor is not None:
            original = earlier.get(predecessor) if isinstance(predecessor, str) else None
            old_tests = original.params.get("tests") if original else None
            new_tests = task.params.get("tests")
            if (
                original is None
                or not isinstance(old_tests, list)
                or not old_tests
                or not isinstance(new_tests, list)
                or any(not isinstance(test, str) for test in [*old_tests, *new_tests])
                or not Counter(old_tests) <= Counter(new_tests)
            ):
                failures.append(
                    f"Sandbox task {task.id} has an invalid recovery link or dropped checks."
                )
            elif not _execution_failures(state, task):
                superseded.add(original.id)
        earlier[task.id] = task
    return superseded, failures


def sandbox_verification_failures(state: PolyaState) -> list[str]:
    """Reject missing/failed execution before requesting semantic review."""
    superseded, failures = _recovery_links(state)
    for task in state["plan"]:
        if task.tool_name == "python_sandbox" and task.id not in superseded:
            failures.extend(_execution_failures(state, task))
    return failures


def active_sandbox_tasks(state: PolyaState) -> list[PlanTask]:
    """Current implementations, independent of model-supplied problem labels."""
    superseded, _ = _recovery_links(state)
    return [
        task
        for task in state["plan"]
        if task.tool_name == "python_sandbox" and task.id not in superseded
    ]


def coding_delivery_failures(state: PolyaState, answer: str) -> list[str]:
    """Bind a coding deliverable to active tested code; no semantic claim is made."""
    delivered = {
        block.strip()
        for block in re.findall(
            r"^```(?:python|py)\s*\n(.*?)^```\s*$", answer, re.MULTILINE | re.DOTALL
        )
    }
    problem = state["structured_problem"]
    coding = problem is not None and any(
        marker in problem.problem_type.casefold()
        for marker in ("algorithm", "coding", "program", "source_patch")
    )
    # Analyses can use Python privately. Once Python code is delivered, a
    # free-form problem label cannot bypass implementation identity checks.
    if not coding and not delivered:
        return []
    expected = {str(task.params.get("code", "")).strip() for task in active_sandbox_tasks(state)}
    if not expected:
        return []
    if delivered != expected:
        return ["Delivered Python code differs from the active executed implementations."]
    return []
