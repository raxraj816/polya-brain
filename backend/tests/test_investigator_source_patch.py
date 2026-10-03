"""Public source/check workflow, supplied-check scope, and host integrity."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.execution import DockerPythonSandbox, image_available
from app.investigator.cli import main
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage


@pytest.fixture
def patch_case(tmp_path, monkeypatch):
    for key, value in {
        "OPENROUTER_API_KEY": "local-fake-provider",
        "OPENROUTER_MODEL": "test-model",
        "OPENROUTER_FALLBACK_MODELS": "",
        "SEARCH_PROVIDER": "",
        "SEARCH_API_KEY": "",
        "ARTIFACT_ALLOWED_ROOTS": "",
        "POLYABRAIN_RECOVERY_HOME": str(tmp_path / "recovery"),
    }.items():
        monkeypatch.setenv(key, value)
    source = tmp_path / "source.py"
    source.write_text("def total(count, unit_price):\n    return count + unit_price\n")
    check = tmp_path / "check.py"
    check.write_text(
        "def verify(implementation):\n    assert implementation.total(3, 7) == 21\n    assert implementation.total(0, 7) == 0\n"
    )
    return source, check


def proposal(source: Path, check: Path, replacement="count * unit_price") -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="test-model",
        text=json.dumps(
            {
                "diagnosis": "total adds count and unit_price instead of multiplying them.",
                "implicated_source_uri": source.as_uri(),
                "old_text": "count + unit_price",
                "new_text": replacement,
                "correction_rationale": "Multiply units by price.",
                "regression_check_uri": check.as_uri(),
                "regression_check_summary": "Check total for three and zero units.",
                "remaining_uncertainty": ["Only the supplied examples are covered."],
            }
        ),
        finish_reason="stop",
        usage=LLMTokenUsage(input_tokens=100, output_tokens=120),
    )


def arguments(tmp_path: Path, source: Path, check: Path) -> list[str]:
    return [
        "investigate",
        "Diagnose why total charges are wrong and propose a minimal edit.",
        "--source",
        str(source),
        "--check",
        str(check),
        "--artifact-root",
        str(tmp_path),
        "--experimental-source-patch",
        "--allow-code-execution",
        "--output-root",
        str(tmp_path / "runs"),
        "--run-id",
        "result",
        "--json",
    ]


@pytest.mark.skipif(
    shutil.which("docker") is None or not image_available(DockerPythonSandbox().image),
    reason="requires the pinned Docker sandbox image",
)
@pytest.mark.parametrize("case", ["fixed", "vacuous", "wrong_edit"])
def test_public_source_patch_workflow(patch_case, tmp_path, monkeypatch, case):
    source, check = patch_case
    if case == "vacuous":
        check.write_text("def verify(implementation):\n    pass\n")
    original = source.read_bytes()
    client = FakeLLMClient(
        [
            proposal(
                source,
                check,
                "count - unit_price" if case == "wrong_edit" else "count * unit_price",
            )
        ]
    )
    monkeypatch.setattr(
        "app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda settings: client
    )
    code = main(arguments(tmp_path, source, check))
    output = tmp_path / "runs/result"
    report = json.loads((output / "report.json").read_text())
    assert source.read_bytes() == original
    assert (output / "candidate.patch").exists()
    assert json.loads((output / "candidate_edit.json").read_text())["host_files_modified"] is False
    execution = json.loads((output / "execution.json").read_text())[0]["output"]
    if case == "fixed":
        assert code == 0
        assert len(client.requests) == 1
        assert execution["baseline_failed"] is True
        assert execution["baseline"]["test_results"][0]["passed"] is False
        assert execution["patched"]["test_results"][0]["passed"] is True
        assert report["verification_status"] == "passed"
        assert report["confidence_level"] == "medium"
        assert "Proposed diagnosis" in report["final_conclusion"]
        assert (
            "failed on the original source and passed on the candidate edit"
            in report["final_conclusion"]
        )
    else:
        assert code == 3
        assert execution["patch_verified"] is False
        assert report["verification_status"] != "passed"
        assert report["final_conclusion"] == "No verified conclusion is available."


def test_source_patch_requires_explicit_execution_permission(patch_case, tmp_path):
    source, check = patch_case
    args = arguments(tmp_path, source, check)
    args.remove("--allow-code-execution")
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert not (tmp_path / "runs").exists()


def test_source_patch_rejects_outside_root_before_provider(patch_case, tmp_path, monkeypatch):
    source, check = patch_case
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    client = FakeLLMClient([])
    monkeypatch.setattr(
        "app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda settings: client
    )
    args = arguments(tmp_path, source, check)
    args[args.index("--artifact-root") + 1] = str(allowed)
    assert main(args) == 1
    assert not client.requests


def test_source_patch_offline_stops_without_fictitious_model_calls(patch_case, tmp_path):
    source, check = patch_case
    assert main([*arguments(tmp_path, source, check), "--offline"]) == 3
    run = json.loads((tmp_path / "runs/result/run.json").read_text())
    assert run["usage"]["model_calls"] == 0


@pytest.mark.skipif(
    shutil.which("docker") is None or not image_available(DockerPythonSandbox().image),
    reason="requires the pinned Docker sandbox image",
)
def test_source_patch_pause_resumes_through_same_composer(patch_case, tmp_path, monkeypatch):
    source, check = patch_case
    client = FakeLLMClient([proposal(source, check)])
    monkeypatch.setattr(
        "app.cognition.bootstrap.OpenRouterLLMClient.from_settings", lambda settings: client
    )
    assert main([*arguments(tmp_path, source, check), "--max-cycles", "2"]) == 3
    assert not client.requests
    assert (
        main(
            [
                "resume",
                str(tmp_path / "runs/result"),
                "--artifact-root",
                str(tmp_path),
                "--allow-code-execution",
                "--output-root",
                str(tmp_path / "runs"),
                "--run-id",
                "continued",
                "--json",
            ]
        )
        == 0
    )
    assert len(client.requests) == 1
    assert (tmp_path / "runs/continued/candidate_edit.json").exists()
