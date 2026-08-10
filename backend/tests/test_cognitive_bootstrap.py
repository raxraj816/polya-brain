"""Tests for the first persisted cognitive-session composition."""

from app.cognition.bootstrap import build_representation_session_runner
from app.config import Settings


def _offline_settings() -> Settings:
    return Settings(
        POLYABRAIN_ENV="test",
        OPENROUTER_API_KEY="",
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
