"""Validate experiment ceilings and feedback before spending on live trials."""

import json
import shutil
import subprocess

import pytest
from evals.chapter_13p.coding_execution.matched import Limits, Meter, lean_solve, run_arm

from app.execution import DockerPythonSandbox
from app.execution.sandbox import SandboxExecutionResult
from app.llm import FakeLLMClient, LLMClientError, LLMRequest, LLMResponse, LLMTokenUsage


def response(text="response", output_tokens=10):
    return LLMResponse(
        provider="fake",
        model="test",
        text=text,
        usage=LLMTokenUsage(input_tokens=20, output_tokens=output_tokens),
    )


def request(model="test"):
    return LLMRequest(model=model, messages=[{"role": "user", "content": "Task"}])


def test_common_call_budget_and_request_capture(tmp_path):
    client = FakeLLMClient([response(), response()])
    meter = Meter(client, "test", DockerPythonSandbox(), tmp_path, Limits(model_calls=1))
    meter.complete(request())
    with pytest.raises(LLMClientError):
        meter.complete(request())
    assert len(client.requests) == 1
    assert client.requests[0].options.max_retries == 0
    assert (tmp_path / "model-1.request.json").is_file()
    assert (tmp_path / "model-1.response.json").is_file()


def test_output_reservation_clamps_and_blocks_next_call(tmp_path):
    client = FakeLLMClient([response(output_tokens=5)])
    meter = Meter(client, "test", DockerPythonSandbox(), tmp_path, Limits(output_tokens=5))
    meter.complete(request())
    assert client.requests[0].options.max_output_tokens == 5
    with pytest.raises(LLMClientError):
        meter.complete(request())


@pytest.mark.parametrize("reason", ["route", "deadline"])
def test_route_changes_and_expired_deadlines_never_reach_provider(tmp_path, reason):
    client = FakeLLMClient([response()])
    meter = Meter(client, "test", DockerPythonSandbox(), tmp_path)
    if reason == "deadline":
        meter.started -= 1000
    with pytest.raises(LLMClientError):
        meter.complete(request("another" if reason == "route" else "test"))
    assert client.requests == []


def test_unknown_failed_call_usage_stops_further_spending(tmp_path):
    meter = Meter(FakeLLMClient([]), "test", DockerPythonSandbox(), tmp_path)
    with pytest.raises(LLMClientError):
        meter.complete(request())
    assert meter.usage()["output_tokens"] is None
    assert (tmp_path / "model-1.failure.json").is_file()
    with pytest.raises(LLMClientError):
        meter.complete(request())
    assert meter.calls == 1


def test_instrumented_public_runtime_reaches_provider(monkeypatch, tmp_path):
    from app.config import Settings
    from app.llm import OpenRouterLLMClient

    client = FakeLLMClient([])
    monkeypatch.setattr(OpenRouterLLMClient, "from_settings", lambda _: client)
    settings = Settings(
        _env_file=None,
        OPENROUTER_API_KEY="fake-local-test",
        OPENROUTER_MODEL="test",
        OPENROUTER_FALLBACK_MODELS="",
        CODE_EXECUTION_ENABLED=True,
        SEARCH_PROVIDER="",
        ARTIFACT_ALLOWED_ROOTS="",
    )
    record = run_arm(
        settings, "common_slot", "Implement first_slot in Python.", "polya", tmp_path / "polya"
    )
    assert record["usage"]["model_calls"] == 1
    assert record.get("failure") != "AttributeError"
    assert (tmp_path / "polya" / "model-1.failure.json").is_file()


def test_lean_solver_sees_actual_failure_and_repairs_within_tool_budget(tmp_path):
    attempts = []

    class Sandbox:
        limits = DockerPythonSandbox().limits

        def execute(self, code, tests):
            attempts.append(code)
            passed = len(attempts) == 2
            return SandboxExecutionResult(
                exit_code=0 if passed else 1,
                stdout="",
                stderr="",
                runtime_ms=1,
                tests_run=1,
                test_results=[{"index": 1, "passed": passed}],
            )

    payload = {"code": "value=0", "tests": ["assert value==1"], "explanation": "constant"}
    fixed = {**payload, "code": "value=1"}
    client = FakeLLMClient([response(json.dumps(payload)), response(json.dumps(fixed))])
    meter = Meter(client, "test", Sandbox(), tmp_path, Limits(sandbox_calls=2))
    answer = lean_solve(meter, "Return one")
    assert "value=1" in answer
    assert attempts == ["value=0", "value=1"]
    assert '"passed":false' in client.requests[1].messages[-1].content
    with pytest.raises(ValueError, match="budget"):
        meter.execute("value=1", ["assert value==1"])
    assert len(attempts) == 2


def test_calendar_oracle_accepts_reference_and_rejects_constant_result():
    from evals.chapter_13p.coding_execution.evidence import execution_passed
    from evals.chapter_13p.coding_execution.verify import CHECKS

    from app.execution import DockerSandboxLimits

    sandbox = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=20))
    if (
        shutil.which("docker") is None
        or subprocess.run(
            ["docker", "image", "inspect", sandbox.image],
            capture_output=True,
            check=False,
            timeout=10,
        ).returncode
        != 0
    ):
        pytest.skip("requires Docker and the pinned sandbox image")
    reference = """from itertools import groupby
def first_slot(calendars, duration):
    if not calendars: return 0
    counts = [0] * len(calendars)
    events = sorted((time, p, delta) for p, spans in enumerate(calendars)
                    for a, b in spans for time, delta in [(a, 1), (b, -1)])
    active, begin = 0, None
    for time, group in groupby(events, key=lambda e: e[0]):
        if begin is not None and time - begin >= duration: return begin
        for _, p, delta in group:
            before = counts[p] > 0
            counts[p] += delta
            active += (counts[p] > 0) - before
        if active == len(calendars):
            if begin is None: begin = time
        else: begin = None
    return None
"""
    checks = CHECKS["common_slot"]
    assert execution_passed(sandbox.execute(reference, checks), len(checks))
    assert not execution_passed(
        sandbox.execute("def first_slot(calendars, duration): return 0", checks), len(checks)
    )
