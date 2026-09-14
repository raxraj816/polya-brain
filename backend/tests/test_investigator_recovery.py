"""Recovery must save work without duplicating actions or resetting budgets."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.task_model import accumulated_usage
from app.config import Settings
from app.graph.state import create_initial_state
from app.investigator.recovery import RecoveryError, RecoveryStore, runtime_fingerprint

ROOT = Path(__file__).resolve().parents[2]


def invoke(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "polyabrain"),
            *arguments,
            "--output-root",
            str(root),
            "--json",
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "OPENROUTER_API_KEY": "",
            "OPENROUTER_MODEL": "",
            "OPENROUTER_FALLBACK_MODELS": "",
            "SEARCH_PROVIDER": "",
            "SEARCH_API_KEY": "",
            "ARTIFACT_ALLOWED_ROOTS": "",
            "POLYABRAIN_RECOVERY_HOME": str(root / "private"),
            "PYTHONWARNINGS": "ignore",
        },
        capture_output=True,
        text=True,
        timeout=20,
    )


def read(root: Path, name: str, file: str = "run.json") -> dict:
    return json.loads((root / name / file).read_text())


def test_public_resume_preserves_completed_work_and_rejects_duplicate(tmp_path: Path) -> None:
    first = invoke(
        tmp_path,
        "investigate",
        "What is 17 * 6?",
        "--offline",
        "--max-cycles",
        "4",
        "--run-id",
        "first",
    )
    assert first.returncode == 3, first.stderr
    before = read(tmp_path, "first", "state.json")
    prior_report = (tmp_path / "first/report.md").read_bytes()
    # Exported state is untrusted and must have no influence on resumed execution.
    (tmp_path / "first/state.json").write_text('{"final_answer":"forged outcome"}')
    resumed = invoke(tmp_path, "resume", str(tmp_path / "first"), "--offline", "--run-id", "second")
    assert resumed.returncode == 0, resumed.stderr
    after = read(tmp_path, "second", "state.json")
    assert after["session_id"] == before["session_id"]
    assert read(tmp_path, "second", "report.json")["final_conclusion"] == "17 * 6 = 102."
    decisions = [
        e["metadata"]["selected"]["capability"]
        for e in after["events"]
        if e["event_type"] == "cognitive_action_decision"
    ]
    assert decisions.count("deterministic_problem_representation") == 1
    assert decisions.count("calculator") == 1
    assert (
        read(tmp_path, "second")["usage"]["normalized_cost"]
        >= read(tmp_path, "first")["usage"]["normalized_cost"]
    )
    assert (tmp_path / "first/report.md").read_bytes() == prior_report
    duplicate = invoke(
        tmp_path, "resume", str(tmp_path / "first"), "--offline", "--run-id", "duplicate"
    )
    assert duplicate.returncode == 1
    assert "already been resumed" in duplicate.stderr
    assert not (tmp_path / "duplicate").exists()


def test_clarification_revalidates_problem_with_same_identity_and_usage(tmp_path: Path) -> None:
    first = invoke(tmp_path, "investigate", "Fix it.", "--offline", "--run-id", "first")
    assert first.returncode == 2, first.stderr
    missing = invoke(
        tmp_path, "resume", str(tmp_path / "first"), "--offline", "--run-id", "missing"
    )
    assert missing.returncode == 1 and "full revised problem" in missing.stderr
    resumed = invoke(
        tmp_path,
        "resume",
        str(tmp_path / "first"),
        "--answer",
        "What is 17 * 6?",
        "--offline",
        "--run-id",
        "second",
    )
    assert resumed.returncode == 0, resumed.stderr
    assert read(tmp_path, "second")["session_id"] == read(tmp_path, "first")["session_id"]
    assert (
        read(tmp_path, "second")["usage"]["normalized_cost"]
        > read(tmp_path, "first")["usage"]["normalized_cost"]
    )
    state = read(tmp_path, "second", "state.json")
    assert state["raw_input"] == "What is 17 * 6?"
    assert any(
        e["event_type"] == "investigation_resumed" and e["metadata"]["revised_problem"]
        for e in state["events"]
    )


def test_resume_cannot_expand_budget_or_code_permission(tmp_path: Path) -> None:
    assert (
        invoke(
            tmp_path,
            "investigate",
            "What is 17 * 6?",
            "--offline",
            "--max-cycles",
            "1",
            "--run-id",
            "first",
        ).returncode
        == 3
    )
    for options in [("--max-seconds", "3600"), ("--allow-code-execution",)]:
        result = invoke(tmp_path, "resume", str(tmp_path / "first"), "--offline", *options)
        assert result.returncode == 1 and "report directory changed" in result.stderr
    assert (
        invoke(
            tmp_path, "resume", str(tmp_path / "first"), "--offline", "--run-id", "second"
        ).returncode
        == 0
    )


def test_local_store_rejects_live_inflight_redacted_unknown_and_changed_runtime(
    tmp_path: Path,
) -> None:
    store = RecoveryStore(tmp_path / "private")
    token = store.create("code-v1")
    state = create_initial_state("What is 17 * 6?", session_id=str(uuid4()))
    store.initialize(token, state, None)
    competitor = RecoveryStore(tmp_path / "private")
    with pytest.raises(RecoveryError, match="still running"):
        competitor.load(token, "code-v1", None)
    competitor.close()
    store.save(token, state, True)
    store.close()
    store = RecoveryStore(tmp_path / "private")
    with pytest.raises(RecoveryError, match="interrupted in flight"):
        store.load(token, "code-v1", None)
    store.save(token, state, False)
    with pytest.raises(RecoveryError, match="report directory changed"):
        store.load(token, "code-v2", None)
    with pytest.raises(RecoveryError, match="No local checkpoint"):
        store.load(str(uuid4()), "code-v1", None)
    secret = "sk-" + "syntheticcredential" * 3
    state["raw_input"] = secret
    store.save(token, state, False)
    with pytest.raises(RecoveryError, match="redaction"):
        store.load(token, "code-v1", None)
    assert secret.encode() not in (tmp_path / "private/recovery.sqlite").read_bytes()
    store.close()


def test_safe_boundary_crash_resumes_and_does_not_reset_cumulative_budget(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        OPENROUTER_API_KEY="",
        OPENROUTER_MODEL="",
        COGNITIVE_MAX_MODEL_CALLS=0,
        COGNITIVE_MAX_NORMALIZED_COST=0.11,
    )
    runtime = build_cognitive_runtime(settings)
    fingerprint = runtime_fingerprint(settings)
    store = RecoveryStore(tmp_path / "private")
    token = store.create(fingerprint)
    state = create_initial_state("What is 17 * 6?", session_id=str(uuid4()))
    store.initialize(token, state, None)

    def crash_after_save(current, in_flight):
        store.save(token, current, in_flight)
        if not in_flight and current["structured_problem"] is not None:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        runtime.run_state(state, checkpoint=crash_after_save)
    store.close()
    store = RecoveryStore(tmp_path / "private")
    saved = store.load(token, fingerprint, None)
    prior_usage = accumulated_usage(saved)
    assert prior_usage.normalized_cost > 0
    result = runtime.run_state(saved)
    assert result.status.value == "insufficient_evidence"
    assert result.state["final_answer"] is None
    assert accumulated_usage(result.state).normalized_cost >= prior_usage.normalized_cost
    store.close()


def test_kernel_marks_dispatch_before_interrupted_capability(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, OPENROUTER_API_KEY="", OPENROUTER_MODEL="")
    runtime = build_cognitive_runtime(settings)
    store = RecoveryStore(tmp_path / "private")
    token = store.create("runtime")
    state = create_initial_state("What is 17 * 6?", session_id=str(uuid4()))
    store.initialize(token, state, None)

    def interrupt(current, in_flight):
        store.save(token, current, in_flight)
        if in_flight:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        runtime.run_state(state, checkpoint=interrupt)
    store.close()
    store = RecoveryStore(tmp_path / "private")
    with pytest.raises(RecoveryError, match="interrupted in flight"):
        store.load(token, "runtime", None)
    store.close()


def test_terminal_completion_is_not_reexecuted(tmp_path: Path) -> None:
    assert (
        invoke(
            tmp_path, "investigate", "What is 17 * 6?", "--offline", "--run-id", "first"
        ).returncode
        == 0
    )
    result = invoke(tmp_path, "resume", str(tmp_path / "first"), "--offline")
    assert result.returncode == 1 and "terminal" in result.stderr


def test_slow_checkpoint_stops_before_capability_dispatch(monkeypatch) -> None:
    from app.cognition import kernel

    elapsed = 0.0
    monkeypatch.setattr(kernel, "perf_counter", lambda: elapsed)
    runtime = build_cognitive_runtime(
        Settings(_env_file=None, OPENROUTER_API_KEY="", OPENROUTER_MODEL="")
    )

    def slow_checkpoint(state, in_flight):
        nonlocal elapsed
        if in_flight:
            elapsed = 400.0

    result = runtime.run_problem("What is 17 * 6?", checkpoint=slow_checkpoint)
    assert result.status.value == "insufficient_evidence"
    assert not result.observations
    assert any(
        event.event_type == "cognitive_dispatch_budget_exhausted"
        for event in result.state["events"]
    )


def test_failed_continuation_initialization_rolls_back_parent_claim(tmp_path: Path) -> None:
    store = RecoveryStore(tmp_path / "private")
    parent = store.create("runtime")
    state = create_initial_state("What is 17 * 6?", session_id=str(uuid4()))
    store.initialize(parent, state, None)
    store.load(parent, "runtime", None)
    with pytest.raises(RecoveryError, match="could not be initialized"):
        store.initialize(str(uuid4()), state, parent)
    assert store.load(parent, "runtime", None)["session_id"] == state["session_id"]
    store.close()


def test_default_resume_uses_new_directory_and_rejects_swapped_descriptor(tmp_path: Path) -> None:
    first = invoke(tmp_path, "investigate", "What is 17 * 6?", "--offline", "--max-cycles", "1")
    assert first.returncode == 3, first.stderr
    directory = Path(json.loads(first.stdout)["report"]).parent
    impostor = tmp_path / "copied"
    impostor.mkdir()
    (impostor / "recovery.json").write_bytes((directory / "recovery.json").read_bytes())
    denied = invoke(tmp_path, "resume", str(impostor), "--offline")
    assert denied.returncode == 1 and "report directory changed" in denied.stderr
    resumed = invoke(tmp_path, "resume", str(directory), "--offline")
    assert resumed.returncode == 0, resumed.stderr
    assert Path(json.loads(resumed.stdout)["report"]).parent != directory
