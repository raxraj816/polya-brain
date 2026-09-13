"""Tests for the first persisted cognitive-session composition."""

from pathlib import Path

import pytest
from pydantic import SecretStr

from app.cognition import accumulated_usage
from app.cognition.bootstrap import build_representation_session_runner
from app.config import Settings


def _offline_settings() -> Settings:
    return Settings(
        POLYABRAIN_ENV="test",
        OPENROUTER_API_KEY=SecretStr(""),
        OPENROUTER_MODEL="",
    )


def test_bootstrap_pauses_deterministic_ambiguous_input_without_provider() -> None:
    runner = build_representation_session_runner(_offline_settings())

    execution = runner("Fix it.", session_id="bootstrap-needs-input")

    assert execution.awaiting_user_input
    assert len(execution.clarifying_questions) == 2
    assert execution.state["structured_problem"] is None
    assert execution.state["final_answer"] is None


def test_bootstrap_solves_exact_arithmetic_without_a_model_provider() -> None:
    runner = build_representation_session_runner(_offline_settings())

    execution = runner("What is 17 * 6?", session_id="bootstrap-safe-stop")

    assert not execution.awaiting_user_input
    assert execution.state["structured_problem"] is not None
    assert execution.state["final_answer"] == "17 * 6 = 102."
    assert execution.state["verification"] is not None
    assert execution.state["verification"].passed
    assert execution.state["reflection"] is not None


def test_bootstrap_solves_exact_explicit_artifact_lookup_without_model(
    tmp_path: Path,
) -> None:
    manual = tmp_path / "fictional_manual.txt"
    manual.write_text(
        "Zephyra revision 7\nRule Z7.4: request_timeout_ticks = 37.\n",
        encoding="utf-8",
    )
    settings = Settings(
        POLYABRAIN_ENV="test",
        OPENROUTER_API_KEY=SecretStr(""),
        OPENROUTER_MODEL="",
        ARTIFACT_ALLOWED_ROOTS=str(tmp_path),
    )
    runner = build_representation_session_runner(settings)

    execution = runner(
        f"Using only the manual at '{manual}', determine what request timeout "
        "Zephyra revision 7 requires and state the exact rule.",
        session_id="bootstrap-artifact-lookup",
    )

    assert not execution.awaiting_user_input
    assert execution.state["verification"] is not None
    assert execution.state["verification"].passed
    assert "Z7.4" in (execution.state["final_answer"] or "")
    assert "37" in (execution.state["final_answer"] or "")
    assert accumulated_usage(execution.state).model_calls == 0
    compiled = [
        event
        for event in execution.state["events"]
        if event.event_type == "compiled_procedure_proposed"
    ]
    assert len(compiled) == 1
    assert compiled[0].metadata["lifecycle"] == "proposed"


def test_bootstrap_rejects_more_than_one_explicit_semantic_fallback() -> None:
    settings = Settings(
        POLYABRAIN_ENV="test",
        OPENROUTER_API_KEY=SecretStr("synthetic-not-used"),
        OPENROUTER_MODEL="provider/primary",
        OPENROUTER_FALLBACK_MODELS="provider/fallback-a, provider/fallback-b",
    )

    with pytest.raises(ValueError, match="at most one fallback model"):
        build_representation_session_runner(settings)
