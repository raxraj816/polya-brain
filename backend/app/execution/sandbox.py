"""Container-isolated Python execution and test capability."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import selectors
import subprocess
import zlib
from collections.abc import Mapping, Sequence
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
from app.cognition.execution_gaps import pending_sandbox_gaps
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import ContractModel, EvidenceItem, ReasoningMode, RiskLevel

_TEST_MARKER = "__POLYABRAIN_TEST_RESULTS__="
MAX_DATA_BYTES = 2_000_000
PYTHON_TEST_HARNESS_VERSION = "python_checks@0.2.0"

GENERATED_CHECK_INSTRUCTIONS = (
    "Treat model-generated expected answers as hypotheses, not facts. Preserve explicit "
    "user examples and assertions verbatim. For additional invented cases, compute expected "
    "results in the sandbox using a simple reference implementation derived directly from "
    "the specification (such as exhaustive enumeration on small inputs). Admission rejects "
    "ANY new function-call/literal expected-result assertion, even when the answer seems "
    "obvious or is mathematically derived. Only exact examples supplied in raw_input may "
    "use literal expected results. Exact means the same callable comparison, including "
    "its receiver name. Prose examples (such as 'input returns value') are not callable "
    "assertions: keep their input and stated values unchanged, but test those inputs "
    "against an independently derived executable reference. Do not translate prose "
    "into new call/literal assertions or rename the receiver of an exact assertion. "
    "For EVERY additional boundary, random or scale case, "
    "use the shape assert candidate(args) == reference(args), or assert an independently "
    "derived property; do not write assert candidate(args) == 1, == -1, or is None. "
    "For large inputs where an exhaustive reference is too costly, use a separately "
    "derived scalable reference or property and state its coverage limits. "
    "The reference must not call or reuse the candidate algorithm. "
    "Put the reference and bounded differential cases in params.tests, separate from the "
    "deliverable implementation. Use explicit assert statements for every comparison, "
    "including randomized loops and input-preservation checks. A bare Boolean expression "
    "is not a substitute for an assertion suite. Do not change user examples or weaken "
    "existing checks to match candidate output. Explain any unavailable reference or "
    "unresolved oracle ambiguity rather than claiming comprehensive verification. "
)

PYTHON_SANDBOX_PLAN_INSTRUCTIONS = (
    "python_sandbox executes a PlanTask with params.code (complete Python, at most "
    "20000 characters) and params.tests (at most 20 assertion strings, each at most "
    "2000 characters). Each task runs in a fresh networkless container with Python "
    "standard library only, no host files or package installation. Include the actual "
    "implementation in code, and meaningful assertions in tests. The runtime invokes "
    "the container and records exit_code, stdout, stderr, tests_run and test_results. "
    "No shell command or output format needs to be supplied by the user. Results "
    "exist only after execution; never invent them."
)


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


def image_references(image: str) -> list[str]:
    """Inspectable spellings of one image: as configured, then name@digest.

    Some Docker releases reject ``docker image inspect name:tag@sha256:...`` even
    when that exact image is present, while ``name@sha256:...`` resolves it. Both
    forms identify the same pinned content.
    """
    references = [image]
    name, separator, digest = image.partition("@")
    if separator:
        colon = name.rfind(":")
        if colon > name.rfind("/"):  # a tag, not a registry port
            references.append(f"{name[:colon]}@{digest}")
    return references


def image_available(
    image: str, *, docker_binary: str = "docker", timeout_seconds: float = 10.0
) -> bool:
    """Return whether the local Docker daemon holds the configured image.

    Tries ``docker image inspect`` on each reference spelling, then falls back to
    the local digest listing, which some image stores answer even when inspect on a
    pinned reference reports "No such image". A tag alone never satisfies a pin.
    """

    def run(*args: str) -> subprocess.CompletedProcess[bytes] | None:
        try:
            return subprocess.run(  # noqa: S603 - fixed executable and argument vector
                [docker_binary, *args],
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except OSError, subprocess.TimeoutExpired:
            return None

    references = image_references(image)
    for reference in references:
        result = run("image", "inspect", reference)
        if result is None:
            return False
        if result.returncode == 0:
            return True
    pinned = [reference for reference in references if "@" in reference]
    if not pinned:
        return False
    listing = run(
        "image", "ls", "--digests", "--no-trunc", "--format", "{{.Repository}}@{{.Digest}}"
    )
    if listing is None or listing.returncode != 0:
        return False
    present = set(listing.stdout.decode(errors="replace").split())
    return any(reference in present for reference in pinned)


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
        self._admit(code, tests)
        return self._run(self._script(code, tests), len(tests))

    def execute_with_data(
        self, code: str, data: Mapping[str, bytes], tests: Sequence[str] = ()
    ) -> SandboxExecutionResult:
        """Execute code with read-only in-memory data files, still without host mounts.

        The bytes are compressed into the program stream and exposed to the code as the
        dict ``__POLYA_DATA__`` (name -> bytes). Code admission limits are unchanged;
        the data has its own bound.
        """
        self._admit(code, tests)
        total = sum(len(item) for item in data.values())
        if total > MAX_DATA_BYTES or len(data) > 16:
            raise ValueError(f"sandbox data must total at most {MAX_DATA_BYTES} bytes in 16 files")
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name) for name in data):
            raise ValueError("sandbox data names must be plain identifiers")
        payload = base64.b64encode(
            zlib.compress(
                json.dumps(
                    {name: base64.b64encode(blob).decode() for name, blob in data.items()}
                ).encode(),
                6,
            )
        ).decode()
        prelude = (
            "import base64 as __pb_b64, json as __pb_dj, zlib as __pb_zl\n"
            "__POLYA_DATA__ = {__k: __pb_b64.b64decode(__v) for __k, __v in "
            f"__pb_dj.loads(__pb_zl.decompress(__pb_b64.b64decode({payload!r}))).items()}}\n"
        )
        return self._run(prelude + self._script(code, tests), len(tests))

    @staticmethod
    def _admit(code: str, tests: Sequence[str]) -> None:
        if not code.strip() or len(code) > 20_000:
            raise ValueError("sandbox code must contain 1 to 20000 characters")
        if len(tests) > 20 or any(not item.strip() or len(item) > 2_000 for item in tests):
            raise ValueError("sandbox accepts at most 20 bounded tests")

    def _run(self, script: str, test_count: int) -> SandboxExecutionResult:
        container_name = f"polyabrain-sandbox-{uuid4().hex}"
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
            tests_run=test_count,
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
        try:
            __pb_expression = compile(__pb_test, "<polya-check>", "eval")
        except SyntaxError:
            exec(__pb_test, globals())
        else:
            __pb_value = eval(__pb_expression, globals())
            if __pb_value is False:
                raise AssertionError("The test expression evaluated to False.")
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
        version="docker_python_sandbox@0.4.0",
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
                resolved_gap_targets=pending_sandbox_gaps(state),
                unknowns_to_resolve=pending_sandbox_gaps(state),
                trace_events_to_add=[
                    StateEvent(
                        engine_name=definition.name,
                        event_type="sandbox_execution_completed",
                        reasoning_mode=ReasoningMode.EXECUTE,
                        summary=summary,
                        metadata={
                            "task_id": task.id,
                            "test_harness_version": PYTHON_TEST_HARNESS_VERSION,
                            "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                            "tests_sha256": hashlib.sha256(
                                json.dumps(raw_tests, separators=(",", ":")).encode()
                            ).hexdigest(),
                            "result_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
                            "resolved_execution_gaps": [gap for gap in pending_sandbox_gaps(state)],
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
