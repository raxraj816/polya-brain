"""Live isolation and capability tests for the Docker Python sandbox."""

import shutil

import pytest

from app.cognition import CognitiveActionCandidate, CognitiveActionType
from app.execution import (
    DockerPythonSandbox,
    DockerSandboxLimits,
    image_available,
    python_sandbox_capability,
)
from app.graph.state import create_initial_state
from app.models.contracts import PlanTask, RiskLevel


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return image_available(DockerPythonSandbox().image)


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="requires Docker and the pinned python:3.14-alpine sandbox image",
)


# Include Docker startup on shared CI hosts; the timeout test explicitly uses 0.5s.
def _sandbox(*, timeout: float = 5.0, output: int = 4096) -> DockerPythonSandbox:
    return DockerPythonSandbox(
        limits=DockerSandboxLimits(timeout_seconds=timeout, max_output_bytes=output)
    )


def test_sandbox_runs_code_and_assertions_in_isolated_python() -> None:
    result = _sandbox().execute(
        "def add(left, right): return left + right",
        ["assert add(20, 22) == 42"],
    )

    assert result.exit_code == 0
    assert result.tests_run == 1
    assert result.test_results[0].passed
    assert not result.timed_out


def test_false_expression_is_not_silently_reported_as_a_pass() -> None:
    result = _sandbox().execute(
        "def wrong(values): return 0\ndef helper(): assert 2 + 2 == 4",
        [
            "wrong([1, 2]) == 3",
            "all(wrong(values) == sum(values) for values in ([1], [2]))",
            "False",
            "wrong([]) == 0",
            "helper()",
            "assert wrong([]) == 0",
            "for values in ([1], [2]):\n    assert wrong(values) == sum(values)",
            "this is invalid python !",
        ],
    )
    assert result.exit_code != 0
    assert [item.passed for item in result.test_results] == [
        False,
        False,
        False,
        True,
        True,
        True,
        False,
        False,
    ]
    assert result.test_results[0].error_type == "AssertionError"
    assert result.test_results[-1].error_type == "SyntaxError"


def test_differential_checks_reject_wrong_code_and_wrong_reference() -> None:
    oracle = "def oracle(values, target):\n    return min((j-i for i in range(len(values)) for j in range(i+1,len(values)+1) if sum(values[i:j]) >= target), default=-1)"
    result = _sandbox().execute(
        "def incorrect(values, target): return 2",
        [oracle + "\nassert incorrect([-1, -2, -3], -5) == oracle([-1, -2, -3], -5)"],
    )
    assert result.exit_code != 0
    assert not result.test_results[0].passed
    # An incorrect expected answer cannot pass merely because it appears in a
    # generated oracle. An immutable user example still falsifies it.
    wrong_oracle = _sandbox().execute(
        "def oracle(values, target): return 0",
        ["assert oracle([], 0) == -1"],
    )
    assert wrong_oracle.exit_code != 0
    assert not wrong_oracle.test_results[0].passed


def test_sandbox_blocks_network_and_writable_root_filesystem() -> None:
    result = _sandbox().execute(
        """import socket
try:
    socket.create_connection(("1.1.1.1", 53), 0.2)
    print("NETWORK_OPEN")
except OSError:
    print("NETWORK_BLOCKED")
try:
    open("/host-write.txt", "w").write("unsafe")
    print("ROOT_WRITABLE")
except OSError:
    print("ROOT_READ_ONLY")
"""
    )

    assert "NETWORK_BLOCKED" in result.stdout
    assert "ROOT_READ_ONLY" in result.stdout
    assert "NETWORK_OPEN" not in result.stdout
    assert "ROOT_WRITABLE" not in result.stdout


def test_sandbox_stops_infinite_loop_and_excess_output() -> None:
    timed_out = _sandbox(timeout=0.5).execute("while True: pass")
    too_loud = _sandbox(output=1024).execute('print("x" * 10000)')
    memory_limited = _sandbox().execute("payload = bytearray(256 * 1024 * 1024)")

    assert timed_out.timed_out
    assert timed_out.exit_code != 0
    assert too_loud.output_truncated
    assert len(too_loud.stdout.encode()) <= 1024
    assert memory_limited.exit_code != 0


def test_sandbox_capability_records_pass_and_test_failure_as_observations() -> None:
    sandbox = _sandbox()
    capability = python_sandbox_capability(sandbox)
    state = create_initial_state("Run the bounded implementation tests.")
    state["plan"] = [
        PlanTask(
            id="task-pass",
            action="Check addition.",
            tool_name="python_sandbox",
            params={"code": "def add(a, b): return a + b", "tests": ["assert add(2, 2) == 4"]},
            risk_level=RiskLevel.MEDIUM,
        ),
        PlanTask(
            id="task-fail",
            action="Expose a failing assertion.",
            tool_name="python_sandbox",
            params={"code": "value = 3", "tests": ["assert value == 4"]},
            risk_level=RiskLevel.MEDIUM,
        ),
    ]

    def action(task_id: str) -> CognitiveActionCandidate:
        return CognitiveActionCandidate(
            id=f"action-{task_id}",
            action_type=CognitiveActionType.EXECUTE,
            target=task_id,
            purpose="Execute isolated tests.",
            expected_observation="A bounded test result.",
            expected_usefulness=0.9,
            estimated_cost=0.08,
            risk_level=RiskLevel.MEDIUM,
            capability="python_sandbox",
            success_condition="Execution is captured.",
            failure_condition="The isolation backend fails.",
        )

    passed = capability.execute(action("task-pass"), state)
    failed_test = capability.execute(action("task-fail"), state)

    assert passed.status.value == "succeeded"
    assert passed.proposed_update.execution_outputs_to_add[0].error is None
    assert failed_test.status.value == "succeeded"
    assert failed_test.proposed_update.execution_outputs_to_add[0].error
    assert "failed" in failed_test.summary.casefold()
    failed_payload = failed_test.payload
    assert isinstance(failed_payload, dict)
    assert failed_payload["test_results"][0]["passed"] is False
