"""Public CLI outcome, budget, artifact integrity, and privacy regressions."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.contracts import CognitiveRunStatus
from app.cognition.kernel import CognitiveRunResult
from app.config import Settings
from app.graph.state import create_initial_state
from app.investigator.artifacts import export_run

ROOT = Path(__file__).resolve().parents[2]


def _run(tmp_path: Path, problem: str, *options: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "OPENROUTER_API_KEY": "",
        "OPENROUTER_MODEL": "",
        "OPENROUTER_FALLBACK_MODELS": "",
        "SEARCH_API_KEY": "",
        "SEARCH_PROVIDER": "",
        "ARTIFACT_ALLOWED_ROOTS": "",
        "PYTHONWARNINGS": "ignore",
    }
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "polyabrain"),
            "investigate",
            problem,
            "--output-root",
            str(tmp_path),
            "--run-id",
            "result",
            "--json",
            *options,
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def test_public_cli_solves_with_zero_model_budget_and_exports_actual_checks(tmp_path: Path) -> None:
    process = _run(tmp_path, "What is 17 * 6?", "--offline")
    assert process.returncode == 0, process.stderr + process.stdout
    summary = json.loads(process.stdout)
    assert summary["status"] == "completed"
    directory = tmp_path / "result"
    report = json.loads((directory / "report.json").read_text())
    assert report["final_conclusion"] == "17 * 6 = 102."
    assert report["verification_status"] == "passed"
    assert report["checks_performed"]
    run = json.loads((directory / "run.json").read_text())
    assert run["usage"]["model_calls"] == 0
    assert run["usage"]["input_tokens"] == 0
    assert run["budget"]["max_model_calls"] == 0
    trace = json.loads((directory / "trace.json").read_text())
    assert any(event["engine_name"] == "calculator" for event in trace)
    manifest = json.loads((directory / "manifest.json").read_text())
    assert set(manifest["files"]) == {p.name for p in directory.iterdir()} - {"manifest.json"}
    for name, digest in manifest["files"].items():
        path = directory / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700


def test_public_cli_asks_for_input_without_fabricating_a_report(tmp_path: Path) -> None:
    process = _run(tmp_path, "Fix it.", "--offline")
    assert process.returncode == 2, process.stderr
    summary = json.loads(process.stdout)
    assert summary["status"] == "needs_input"
    assert len(summary["open_questions"]) == 2
    report = json.loads((tmp_path / "result/report.json").read_text())
    assert report["checks_performed"] == []
    assert report["confidence_level"] == "insufficient_evidence"


@pytest.mark.parametrize(
    "options", [("--offline",), ("--max-model-calls", "0"), ("--max-seconds", "0")]
)
def test_public_cli_stops_when_required_work_cannot_fit_budget(
    tmp_path: Path, options: tuple[str, ...]
) -> None:
    process = _run(
        tmp_path,
        "Investigate an unknown scheduler failure in an unspecified distributed system.",
        *options,
    )
    assert process.returncode == 3, process.stderr
    report = json.loads((tmp_path / "result/report.json").read_text())
    assert report["verification_status"] != "passed"
    assert report["final_conclusion"] == "No verified conclusion is available."
    run = json.loads((tmp_path / "result/run.json").read_text())
    assert run["usage"]["model_calls"] == 0


def test_public_cli_reads_explicit_artifact_offline(tmp_path: Path) -> None:
    manual = tmp_path / "manual.txt"
    manual.write_text("Zephyra revision 7\nRule Z7.4: request_timeout_ticks = 37.\n")
    process = _run(
        tmp_path,
        f"Using only the manual at '{manual}', determine what request timeout Zephyra revision 7 requires and state the exact rule.",
        "--offline",
        "--artifact-root",
        str(tmp_path),
    )
    assert process.returncode == 0, process.stderr + process.stdout
    report = json.loads((tmp_path / "result/report.json").read_text())
    assert "Z7.4" in report["final_conclusion"]
    assert "37" in report["final_conclusion"]
    assert report["evidence_used"]


def test_public_cli_missing_provider_does_not_charge_fictitious_calls(tmp_path: Path) -> None:
    process = _run(tmp_path, "Investigate the cause of a previously unseen scheduler failure.")
    assert process.returncode == 3, process.stderr
    run = json.loads((tmp_path / "result/run.json").read_text())
    assert run["usage"]["model_calls"] == 0
    assert run["status"] == "insufficient_evidence"


def test_public_cli_preserves_existing_run_and_rejects_path_escape(tmp_path: Path) -> None:
    existing = tmp_path / "result"
    existing.mkdir()
    saved = existing / "report.md"
    saved.write_text("Keep my prior investigation.")
    process = _run(tmp_path, "2 + 2", "--offline")
    assert process.returncode == 1
    assert saved.read_text() == "Keep my prior investigation."
    assert sorted(p.name for p in existing.iterdir()) == ["report.md"]
    process = _run(tmp_path, "2 + 2", "--run-id", "../escape", "--offline")
    assert process.returncode == 2
    assert not (tmp_path.parent / "escape").exists()


def test_local_exports_redact_secret_content_and_never_dump_settings(tmp_path: Path) -> None:
    secret = "sk-" + "syntheticcredential" * 3
    state = create_initial_state("Inspect supplied credential " + secret, session_id=str(uuid4()))
    result = CognitiveRunResult(
        status=CognitiveRunStatus.INSUFFICIENT_EVIDENCE,
        state=state,
        decisions=(),
        observations=(),
        cycles=0,
    )
    export_run(result, tmp_path, elapsed_ms=1)
    for path in tmp_path.iterdir():
        assert secret not in path.read_text()
        assert "openrouter_api_key" not in path.read_text()


def test_deterministic_runtime_keeps_unknown_inputs_out_of_zero_call_route() -> None:
    runtime = build_cognitive_runtime(
        Settings(
            _env_file=None,
            OPENROUTER_API_KEY=SecretStr(""),
            OPENROUTER_MODEL="",
            ARTIFACT_ALLOWED_ROOTS="",
            SEARCH_PROVIDER="",
            SEARCH_API_KEY=SecretStr(""),
            COGNITIVE_MAX_MODEL_CALLS=0,
        )
    )
    result = runtime.run_problem("Diagnose this completely unspecified deployment.")
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert result.observations == ()
