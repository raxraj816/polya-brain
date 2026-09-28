"""The benchmark must reject false wins as rigorously as the runtime does."""

import json
from types import SimpleNamespace

import pytest
from evals.chapter_13p.coding_execution import compare, direct_baseline, evidence, gate, verify

from app.execution.sandbox import SandboxExecutionResult
from app.llm import FakeLLMClient, LLMResponse

CODE = "def covered_count(intervals): return 0"
ANSWER = "```python\n" + CODE + "\n```"


def result(*, passed=True, truncated=False):
    return SandboxExecutionResult(
        exit_code=0 if passed else 1,
        stdout="",
        stderr="",
        runtime_ms=1,
        tests_run=1,
        test_results=[{"index": 1, "passed": passed}],
        output_truncated=truncated,
    )


def stub_sandbox(monkeypatch, *, passed=True, truncated=False):
    calls = []

    def execute(self, code, tests):
        calls.append((code, tests))
        return result(passed=passed, truncated=truncated)

    monkeypatch.setattr(verify.DockerPythonSandbox, "execute", execute)
    return calls


@pytest.mark.parametrize(
    "items", [[], [None], [{"id": "x"}], [{"id": "x", "prompt": "p"}, {"id": "x", "prompt": "q"}]]
)
def test_malformed_or_duplicate_cases_rejected(tmp_path, items):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(items))
    with pytest.raises(ValueError):
        evidence.load_cases(path)


@pytest.mark.parametrize("items", [[], ["x"], ["x=a", "x=b"]])
def test_empty_or_duplicate_assignments_rejected(items):
    with pytest.raises(ValueError):
        evidence.assignments(items)


@pytest.mark.parametrize("answer", ["No code.", ANSWER + "\n" + ANSWER, ANSWER + "\n```python\n"])
def test_ambiguous_or_incomplete_code_rejected(answer):
    assert evidence.extract_code(answer) is None


def test_truncation_cannot_pass_even_with_a_pass_marker():
    assert not evidence.execution_passed(result(truncated=True), 1)


def test_baseline_preserves_response_code_and_disables_hidden_retries(monkeypatch):
    calls = stub_sandbox(monkeypatch)
    client = FakeLLMClient([LLMResponse(provider="fake", model="test", text=ANSWER)])
    record = direct_baseline.run_case(client, "test", "integer_coverage", "A frozen task.")
    assert record["passed"]
    assert record["response"]["text"] == ANSWER
    assert record["code"] == CODE
    assert record["code_sha256"] == evidence.digest(CODE)
    assert record["prompt_sha256"] == evidence.digest(record["prompt"])
    assert client.requests[0].options.max_retries == 0
    assert calls[0][0] == CODE
    assert record["total_elapsed_ms"] >= record["elapsed_ms"]


def test_failed_provider_attempt_keeps_unknown_usage_and_call_count():
    record = direct_baseline.run_case(FakeLLMClient([]), "test", "integer_coverage", "Task")
    assert not record["passed"]
    assert record["model_calls"] == 1
    assert record["usage"] is None
    assert record["failure"]
    assert compare.total_tokens(record["usage"]) is None


def test_legacy_reported_pass_is_not_replayable(monkeypatch):
    calls = stub_sandbox(monkeypatch)
    assert not compare.verify_direct("integer_coverage", {"passed": True})["passed"]
    assert calls == []


@pytest.mark.parametrize("tamper", ["code", "prompt", "checks_sha256", "response"])
def test_direct_artifact_binding_rejected(monkeypatch, tamper):
    calls = stub_sandbox(monkeypatch)
    client = FakeLLMClient([LLMResponse(provider="fake", model="test", text=ANSWER)])
    record = direct_baseline.run_case(client, "test", "integer_coverage", "Task")
    record[tamper] = {"text": "Different"} if tamper == "response" else "Different"
    assert not compare.verify_direct("integer_coverage", record)["passed"]
    assert len(calls) == 1


def write_run(directory):
    state = {
        "raw_input": "Task",
        "structured_problem": {
            "core_question": "Task",
            "problem_type": "algorithm_implementation",
        },
        "plan": [
            {
                "id": "code",
                "action": "Run tests",
                "tool_name": "python_sandbox",
                "params": {"code": CODE, "tests": ["assert True"]},
            }
        ],
        "execution_outputs": [
            {"task_id": "code", "summary": "Observed", "output": result().model_dump(mode="json")}
        ],
        "verification": {"passed": True},
        "final_answer": ANSWER,
    }
    (directory / "state.json").write_text(json.dumps(state))
    (directory / "run.json").write_text(json.dumps({"status": "completed"}))
    return state


def test_completed_status_does_not_override_independent_failure(monkeypatch, tmp_path):
    calls = stub_sandbox(monkeypatch, passed=False)
    write_run(tmp_path)
    report = verify.verify("integer_coverage", tmp_path)
    assert report["runtime_reported_pass"]
    assert not report["passed"]
    assert calls[0][0] == CODE
    assert not (tmp_path / "independent-candidate.py").exists()


def test_current_recovery_rules_applied_to_saved_run(monkeypatch, tmp_path):
    stub_sandbox(monkeypatch)
    state = write_run(tmp_path)
    state["plan"].insert(
        0,
        {
            **state["plan"][0],
            "id": "earlier-failure",
            "action": "Earlier attempt",
        },
    )
    state["execution_outputs"].insert(
        0,
        {
            "task_id": "earlier-failure",
            "summary": "Observed failure",
            "error": "AssertionError",
        },
    )
    (tmp_path / "state.json").write_text(json.dumps(state))
    report = verify.verify("integer_coverage", tmp_path)
    assert report["independent_checks_passed"]
    assert not report["current_execution_contract_passed"]
    assert not report["passed"]


def test_comparison_exposes_unreplayable_baseline_and_missing_usage(monkeypatch, tmp_path):
    stub_sandbox(monkeypatch)
    write_run(tmp_path)
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([{"id": "integer_coverage", "prompt": "Task"}]))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"cases": [{"case": "integer_coverage", "passed": True}]}))
    summary = compare.compare(baseline, [f"integer_coverage={tmp_path}"], cases)
    row = summary["cases"][0]
    assert row["polya_passed"]
    assert row["direct_reported_pass"] and not row["direct_passed"]
    assert row["direct_total_tokens"] is None
    assert row["polya_total_tokens"] is None
    assert not summary["controlled_superiority_evidence"]
    assert not summary["all_inputs_match"]


def test_gate_does_not_collapse_duplicate_assignments(tmp_path):
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps([{"id": "integer_coverage", "prompt": "Task"}]))
    with pytest.raises(ValueError, match="duplicate"):
        gate.run_gate(cases, ["integer_coverage=a", "integer_coverage=b"])


def test_baseline_checkpoint_survives_interruption_and_refuses_overwrite(monkeypatch, tmp_path):
    cases = tmp_path / "cases.json"
    output = tmp_path / "result.json"
    cases.write_text(
        json.dumps(
            [
                {"id": "integer_coverage", "prompt": "A"},
                {"id": "median", "prompt": "B"},
            ]
        )
    )
    monkeypatch.setattr("sys.argv", ["baseline", "--cases", str(cases), "--output", str(output)])
    monkeypatch.setattr(
        direct_baseline, "Settings", lambda: SimpleNamespace(openrouter_model="test")
    )
    monkeypatch.setattr(direct_baseline.OpenRouterLLMClient, "from_settings", lambda _: None)

    def run(client, model, case, prompt):
        if case == "median":
            raise KeyboardInterrupt
        return {"case": case, "passed": False, "failure": "DeliberateFailure"}

    monkeypatch.setattr(direct_baseline, "run_case", run)
    with pytest.raises(KeyboardInterrupt):
        direct_baseline.main()
    saved = json.loads(output.read_text())
    assert not saved["complete"]
    assert saved["attempted_cases"] == ["integer_coverage", "median"]
    assert saved["in_flight_case"] == "median"
    assert saved["cases"][0]["failure"] == "DeliberateFailure"
    with pytest.raises(FileExistsError):
        direct_baseline.main()
    assert json.loads(output.read_text()) == saved
