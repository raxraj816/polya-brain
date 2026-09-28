"""Measured first model edits recover once under unchanged source/check bindings."""

import copy
import json
from pathlib import Path

import pytest
from test_repair_memory import settings
from test_source_patch_investigation import _docker_available

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.contracts import CognitiveRunStatus
from app.cognition.repair_memory import learn_repair
from app.cognition.repair_recovery import EVENT, failed_source_patch_task
from app.cognition.task_model import accumulated_usage
from app.investigator.source_patch import source_patch_state
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage

CASE = json.loads(Path("evals/chapter_13p/source_recovery/case.json").read_text())
FIXED = (
    CASE["source"]
    .replace("base_delay * (attempt + 1)", "base_delay * 2**attempt")
    .replace("when <= deadline", "when < deadline")
)


class Proposals(FakeLLMClient):
    def __init__(self, source, check, replacement=FIXED):
        super().__init__([])
        self.source, self.check, self.replacement = source, check, replacement

    def complete(self, request):
        self.requests.append(request)
        proposal = {
            **CASE["injected_edit"],
            "implicated_source_uri": self.source.as_uri(),
            "regression_check_uri": self.check.as_uri(),
        }
        if len(self.requests) > 1:
            proposal.update(
                old_text=CASE["source"],
                new_text=self.replacement,
                diagnosis="next_retry must use exponential delay and exclude when == deadline.",
            )
        return LLMResponse(
            provider="fake",
            model="test-model",
            text=json.dumps(proposal),
            usage=LLMTokenUsage(input_tokens=100, output_tokens=120),
        )


def run_case(tmp_path, monkeypatch, *, replacement=FIXED, calls=6, check_text=None):
    if not _docker_available():
        pytest.skip("requires configured Docker sandbox")
    source, check = tmp_path / "source.py", tmp_path / "check.py"
    source.write_text(CASE["source"])
    check.write_text(check_text or CASE["check"])
    fake = Proposals(source, check, replacement)
    monkeypatch.setattr("app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: fake)
    config = settings(tmp_path).model_copy(update={"cognitive_max_model_calls": calls})
    state = source_patch_state(CASE["problem"], source, check, config)
    result = build_cognitive_runtime(config, enable_source_patch=True).run_state(state)
    assert source.read_text() == CASE["source"]
    assert check.read_text() == (check_text or CASE["check"])
    return result, fake


def test_failed_first_model_edit_recovers_and_learns_only_verified_replacement(
    tmp_path, monkeypatch
):
    result, fake = run_case(tmp_path, monkeypatch)
    assert result.status is CognitiveRunStatus.COMPLETED
    assert len(fake.requests) == accumulated_usage(result.state).model_calls == 2
    old, new = result.state["execution_outputs"]
    assert old.output["patch_verified"] is False
    assert new.output["patch_verified"] is True
    assert old.output["check_snapshot_sha256"] == new.output["check_snapshot_sha256"]
    assert old.task_id != new.task_id == result.state["plan"][0].id
    assert any(e.event_type == "verification_invalidated" for e in result.state["events"])
    assert sum(e.event_type == EVENT for e in result.state["events"]) == 1
    projected = json.loads(fake.requests[1].messages[1].content)["current_state"]
    assert projected["rejected_edit"]["params"]["new_text"] == CASE["injected_edit"]["new_text"]
    lesson = learn_repair(result.state)
    assert lesson is not None and lesson.new_text == FIXED.strip()


@pytest.mark.parametrize(
    "replacement, executions",
    [
        (CASE["source"].replace("base_delay * (attempt + 1)", "base_delay * 2**attempt"), 1),
        (CASE["source"].replace("when <= deadline", "when < deadline"), 2),
    ],
)
def test_repeated_or_second_failed_model_edit_stops(tmp_path, monkeypatch, replacement, executions):
    result, fake = run_case(tmp_path, monkeypatch, replacement=replacement)
    assert result.status is not CognitiveRunStatus.COMPLETED
    assert len(fake.requests) == 2
    assert len(result.state["execution_outputs"]) == executions
    assert result.state["final_answer"] is None
    assert learn_repair(result.state) is None


def test_first_model_recovery_does_not_reset_budget(tmp_path, monkeypatch):
    result, fake = run_case(tmp_path, monkeypatch, calls=4)
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert len(fake.requests) == 1
    assert failed_source_patch_task(result.state) is not None


def test_passing_original_is_not_a_recovery_trigger(tmp_path, monkeypatch):
    result, fake = run_case(
        tmp_path, monkeypatch, check_text="def verify(implementation):\n    assert True\n"
    )
    assert result.status is not CognitiveRunStatus.COMPLETED
    assert len(fake.requests) == 1
    assert failed_source_patch_task(result.state) is None


def test_frozen_fixture_independent_checks_reject_original_and_injected_edit():
    from evals.chapter_13p.coding_execution.evidence import execution_passed

    from app.execution import DockerPythonSandbox

    if not _docker_available():
        pytest.skip("requires configured Docker sandbox")
    sandbox = DockerPythonSandbox()
    incomplete = CASE["source"].replace(
        CASE["injected_edit"]["old_text"], CASE["injected_edit"]["new_text"]
    )
    for candidate, expected in [(CASE["source"], False), (incomplete, False), (FIXED, True)]:
        observed = sandbox.execute(candidate, CASE["independent_checks"])
        assert execution_passed(observed, 1) is expected


def test_experiment_exports_independent_score_and_separates_injection(tmp_path, monkeypatch):
    import sys

    from evals.chapter_13p.source_recovery.run import main

    if not _docker_available():
        pytest.skip("requires configured Docker sandbox")
    output = tmp_path / "run"
    # Exercise CI's credential-free environment without loading the developer's
    # .env. Runtime admission still needs the explicit fake provider settings.
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setattr(
        "evals.chapter_13p.source_recovery.run.Settings", lambda: settings(tmp_path)
    )
    fake = FakeLLMClient(
        [
            LLMResponse(
                provider="fake",
                model="test-model",
                text=json.dumps(
                    {
                        **CASE["injected_edit"],
                        "old_text": CASE["source"],
                        "new_text": FIXED,
                        "implicated_source_uri": (output / "source.py").as_uri(),
                        "regression_check_uri": (output / "check.py").as_uri(),
                    }
                ),
            )
        ]
    )
    monkeypatch.setattr("app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda _: fake)
    monkeypatch.setattr(sys, "argv", ["recovery", "--output", str(output), "--model", "test-model"])
    main()
    record = json.loads((output / "summary.json").read_text())
    assert record["runtime_status"] == "completed"
    assert record["independent"]["passed"] is True
    assert record["patch_verdicts"] == [False, True]
    assert record["injected_proposals"] == record["real_model_calls"] == 1
    assert record["host_snapshots_unchanged"]
    assert record["failed_verification_retained"]
    assert "independent_retry_checks" not in fake.requests[0].messages[1].content
    with pytest.raises(FileExistsError):
        main()


@pytest.fixture
def rejected(tmp_path, monkeypatch):
    result, _ = run_case(tmp_path, monkeypatch, calls=4)
    assert failed_source_patch_task(result.state) is not None
    return result.state


@pytest.mark.parametrize(
    "mutation",
    [
        "source_snapshot",
        "check_snapshot",
        "candidate_snapshot",
        "changed_edit",
        "missing_producer",
        "missing_execution_event",
        "timeout",
        "truncated",
        "missing_results",
        "duplicate_execution",
        "missing_verdict",
    ],
)
def test_unbound_or_incomplete_failure_cannot_trigger_recovery(rejected, mutation):
    state = copy.deepcopy(rejected)
    output = state["execution_outputs"][0].output
    if mutation.endswith("_snapshot"):
        key = {
            "source_snapshot": "source_snapshot_sha256",
            "check_snapshot": "check_snapshot_sha256",
            "candidate_snapshot": "patched_source_sha256",
        }[mutation]
        output[key] = "stale"
    elif mutation == "changed_edit":
        state["plan"][0].params["new_text"] = "base_delay"
    elif mutation == "missing_producer":
        state["events"] = [e for e in state["events"] if e.event_type != "source_patch_proposed"]
    elif mutation == "missing_execution_event":
        state["events"] = [
            e for e in state["events"] if e.event_type != "source_patch_sandbox_completed"
        ]
    elif mutation == "timeout":
        output["patched"]["timed_out"] = True
    elif mutation == "truncated":
        output["patched"]["output_truncated"] = True
    elif mutation == "missing_results":
        output["patched"]["test_results"] = []
    elif mutation == "duplicate_execution":
        state["execution_outputs"].append(copy.deepcopy(state["execution_outputs"][0]))
    else:
        state["verification"] = None
    assert failed_source_patch_task(state) is None
