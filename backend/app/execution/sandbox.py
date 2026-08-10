"""Container-isolated Python execution and test capability."""

from __future__ import annotations

import json
import selectors
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from time import monotonic
from typing import IO, cast
from uuid import uuid4

from pydantic import Field

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import ContractModel, EvidenceItem, ReasoningMode, RiskLevel

_TEST_MARKER = "__POLYABRAIN_TEST_RESULTS__="


class SandboxTestResult(ContractModel):
    """One assertion result emitted by the isolated test harness."""

    index: int = Field(ge=1)
    passed: bool
    error_type: str | None = None


class SandboxExecutionResult(ContractModel):
    """Bounded observable result from an isolated process."""

    exit_code: int
    stdout: str
    stderr: str
    runtime_ms: float = Field(ge=0)
    timed_out: bool = False
    output_truncated: bool = False
    tests_run: int = Field(ge=0)
    test_results: list[SandboxTestResult] = Field(default_factory=list)


@dataclass(frozen=True)
class DockerSandboxLimits:
    """Hard isolation and resource bounds for a Python container."""

    timeout_seconds: float = 5.0
    memory_megabytes: int = 64
    cpus: float = 0.5
    pids: int = 32
    max_output_bytes: int = 64_000


class DockerPythonSandbox:
    """Run untrusted Python in an ephemeral, networkless, read-only container."""

    def __init__(
        self,
        *,
        image: str = (
            "python:3.14-alpine@sha256:"
            "a1321512d6a287428c50dcdf2ab3857761127e03a23b1f648e9c1c0de59288f8"
        ),
        limits: DockerSandboxLimits | None = None,
        docker_binary: str = "docker",
    ) -> None:
        self.image = image
        self.limits = limits or DockerSandboxLimits()
        self.docker_binary = docker_binary

    def execute(self, code: str, tests: Sequence[str] = ()) -> SandboxExecutionResult:
        """Execute code and assertions without host mounts, network, or writable root."""
        if not code.strip() or len(code) > 20_000:
            raise ValueError("sandbox code must contain 1 to 20000 characters")
        if len(tests) > 20 or any(not item.strip() or len(item) > 2_000 for item in tests):
            raise ValueError("sandbox accepts at most 20 bounded tests")
        container_name = f"polyabrain-sandbox-{uuid4().hex}"
        script = self._script(code, tests)
        command = self._command(container_name)
        started = monotonic()
        process = subprocess.Popen(  # noqa: S603 - fixed executable and argument vector
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdin is not None
        process.stdin.write(script.encode())
        process.stdin.close()
        stdout, stderr, timed_out, truncated = self._bounded_output(process, container_name)
        runtime_ms = (monotonic() - started) * 1000
        exit_code = process.returncode if process.returncode is not None else -1
        stdout_text = stdout.decode(errors="replace")
        test_results = self._parse_test_results(stdout_text)
        return SandboxExecutionResult(
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr.decode(errors="replace"),
            runtime_ms=runtime_ms,
            timed_out=timed_out,
            output_truncated=truncated,
            tests_run=len(tests),
            test_results=test_results,
        )

    def _command(self, container_name: str) -> list[str]:
        limits = self.limits
        return [
            self.docker_binary,
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--memory",
            f"{limits.memory_megabytes}m",
            "--memory-swap",
            f"{limits.memory_megabytes}m",
            "--cpus",
            str(limits.cpus),
            "--pids-limit",
            str(limits.pids),
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--user",
            "65534:65534",
            "--ulimit",
            "nofile=64:64",
            "--ulimit",
            "nproc=32:32",
            "-i",
            self.image,
            "python",
            "-I",
            "-B",
            "-",
        ]

    @staticmethod
    def _script(code: str, tests: Sequence[str]) -> str:
        serialized_tests = json.dumps(list(tests))
        return f"""import json as __pb_json
import sys as __pb_sys
{code}
__pb_results = []
for __pb_index, __pb_test in enumerate({serialized_tests}, start=1):
    try:
        exec(__pb_test, globals())
        __pb_results.append({{"index": __pb_index, "passed": True, "error_type": None}})
    except BaseException as __pb_error:
        __pb_results.append({{"index": __pb_index, "passed": False, "error_type": type(__pb_error).__name__}})
__pb_sys.__stdout__.write({_TEST_MARKER!r} + __pb_json.dumps(__pb_results) + "\\n")
if not all(__pb_item["passed"] for __pb_item in __pb_results):
    raise SystemExit(1)
"""

    @staticmethod
    def _parse_test_results(stdout: str) -> list[SandboxTestResult]:
        for line in reversed(stdout.splitlines()):
            if not line.startswith(_TEST_MARKER):
                continue
            try:
                payload = json.loads(line.removeprefix(_TEST_MARKER))
            except json.JSONDecodeError:
                return []
            if not isinstance(payload, list):
                return []
            try:
                return [SandboxTestResult.model_validate(item) for item in payload]
            except ValueError:
                return []
        return []

    def _bounded_output(
        self,
        process: subprocess.Popen[bytes],
        container_name: str,
    ) -> tuple[bytes, bytes, bool, bool]:
        assert process.stdout is not None and process.stderr is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        deadline = monotonic() + self.limits.timeout_seconds
        timed_out = False
        truncated = False
        while selector.get_map():
            if monotonic() >= deadline:
                timed_out = True
                self._terminate(process, container_name)
                break
            for key, _ in selector.select(timeout=0.05):
                stream = cast(IO[bytes], key.fileobj)
                chunk = stream.read(4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buffer = buffers[key.data]
                remaining = self.limits.max_output_bytes - sum(
                    len(item) for item in buffers.values()
                )
                if remaining <= 0:
                    truncated = True
                    self._terminate(process, container_name)
                    break
                buffer.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated = True
                    self._terminate(process, container_name)
                    break
            if timed_out or truncated:
                break
        process.wait(timeout=2)
        return bytes(buffers["stdout"]), bytes(buffers["stderr"]), timed_out, truncated

    def _terminate(self, process: subprocess.Popen[bytes], container_name: str) -> None:
        process.kill()
        process.wait(timeout=2)
        subprocess.run(  # noqa: S603 - exact generated container name, no shell
            [self.docker_binary, "rm", "-f", container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )


def python_sandbox_capability(sandbox: DockerPythonSandbox) -> FunctionCapability:
    """Execute only a plan task explicitly assigned to the Python sandbox."""
    definition = CapabilityDefinition(
        name="python_sandbox",
        version="docker_python_sandbox@0.1.0",
        supported_actions={CognitiveActionType.EXECUTE},
        risk_level=RiskLevel.MEDIUM,
        approved_for_sensitive_data=False,
        timeout_seconds=sandbox.limits.timeout_seconds + 3,
        estimated_cost=0.08,
    )

    def execute(action: CognitiveActionCandidate, state: PolyaState) -> CognitiveObservation:
        task = next((item for item in state["plan"] if item.id == action.target), None)
        if task is None or task.tool_name != definition.name:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary="The selected sandbox plan task is missing or assigned elsewhere.",
                failure_kind="sandbox_task_invalid",
            )
        code = task.params.get("code")
        raw_tests = task.params.get("tests", [])
        if (
            not isinstance(code, str)
            or not isinstance(raw_tests, list)
            or not all(isinstance(item, str) for item in raw_tests)
        ):
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary="Sandbox task parameters require code and an optional string test list.",
                failure_kind="sandbox_params_invalid",
            )
        try:
            result = sandbox.execute(code, raw_tests)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary=f"Sandbox execution failed at its isolation boundary ({type(exc).__name__}).",
                failure_kind="sandbox_unavailable",
            )
        if result.timed_out or result.output_truncated:
            kind = "sandbox_timeout" if result.timed_out else "sandbox_output_limit"
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary="Sandbox stopped the program at a configured resource boundary.",
                payload=result.model_dump(mode="json"),
                failure_kind=kind,
            )
        summary = (
            "Sandboxed code and all supplied tests passed."
            if result.exit_code == 0
            else "Sandboxed code or a supplied test failed."
        )
        output = ExecutionOutput(
            task_id=task.id,
            summary=summary,
            output=result.model_dump(mode="json"),
            error=(result.stderr or "One or more sandbox tests failed.")
            if result.exit_code != 0
            else None,
        )
        serialized = result.model_dump_json()
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=summary,
            payload=result.model_dump(mode="json"),
            evidence=[
                EvidenceItem(
                    source_type="isolated_python_execution",
                    source_uri=f"sandbox://{action.id}",
                    claim=summary,
                    raw_excerpt=serialized,
                    reliability_score=1.0,
                    relevance_score=1.0,
                )
            ],
            proposed_update=CognitiveStateUpdate(
                execution_outputs_to_add=[output],
                trace_events_to_add=[
                    StateEvent(
                        engine_name=definition.name,
                        event_type="sandbox_execution_completed",
                        reasoning_mode=ReasoningMode.EXECUTE,
                        summary=summary,
                        metadata={
                            "exit_code": result.exit_code,
                            "runtime_ms": result.runtime_ms,
                            "tests_run": result.tests_run,
                            "network": "none",
                            "root_filesystem": "read_only",
                        },
                    )
                ],
            ),
        )

    return FunctionCapability(definition, execute)
