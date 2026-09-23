"""Offline contract tests for the Chapter 13-J live comparison harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evals.chapter_13j.build_blind_review_packet import build_packet
from evals.chapter_13j.run_epistemic_control_comparison import (
    MAX_CYCLES,
    MAX_MODEL_CALLS,
    DirectEpistemicTurn,
    FixtureSearchProvider,
    RecordingClient,
    _automated_gate,
    _initial_state,
    _load_cases,
    _parse_turn,
    _registry,
    _score_direct,
    _score_polya,
)

from app.acquisition import SearchRequest
from app.cognition import CognitiveActionType, CognitiveModelGateway, CognitiveRunStatus
from app.cognition.kernel import CognitiveKernel
from app.llm import FakeLLMClient


def test_case_set_balances_answering_and_correct_non_answering() -> None:
    cases = _load_cases()

    assert len(cases) == 8
    assert sum(case.expected_terminal == "answer" for case in cases) == 3
    assert sum(case.expected_terminal == "insufficient_evidence" for case in cases) == 5
    assert {case.category for case in cases} == {
        "multi_source_corroboration",
        "prompt_injection_resistance",
        "false_premise",
        "conflicting_evidence",
        "temporal_validity",
        "source_authority",
        "partial_coverage",
        "tool_failure_abstention",
    }


def test_direct_turn_contract_distinguishes_answer_from_abstention() -> None:
    answer = _parse_turn(
        """{
          "status":"final",
          "rationale":"Two current sources agree.",
          "conclusion":"The limit is 45.",
          "evidence_source_uris":["https://docs.example.org/a","https://x.example.edu/b"],
          "checks_performed":["Compared values."],
          "confidence":"high"
        }"""
    )
    abstention = _parse_turn(
        """{
          "status":"insufficient_evidence",
          "rationale":"The sources conflict.",
          "conclusion":null,
          "open_questions":["Which current primary record resolves the conflict?"],
          "confidence":"insufficient_evidence"
        }"""
    )

    assert answer.status == "final"
    assert abstention.status == "insufficient_evidence"
    with pytest.raises(ValueError, match="insufficient_evidence requires"):
        DirectEpistemicTurn(
            status="insufficient_evidence",
            rationale="No evidence.",
            confidence="insufficient_evidence",
        )


def test_fixture_provider_replays_ordered_batches_without_exposing_expected_answer() -> None:
    case = _load_cases()[0]
    provider = FixtureSearchProvider(case)
    first = provider.search(SearchRequest(query="first strategy"))
    second = provider.search(SearchRequest(query="second strategy"))

    assert first.candidates[0].id == "official-limit"
    assert second.candidates[0].id == "independent-limit"
    assert len(provider.requests) == 2


def test_all_search_failures_produce_zero_model_call_safe_stop() -> None:
    case = next(case for case in _load_cases() if case.id == "all_search_routes_fail")
    provider = FixtureSearchProvider(case)
    client = RecordingClient(FakeLLMClient([]), max_calls=MAX_MODEL_CALLS)
    registry = _registry(case, provider, CognitiveModelGateway(client, "same-fake-model"))

    result = CognitiveKernel(registry).run(
        _initial_state(case, "offline-polya"),
        max_cycles=MAX_CYCLES,
    )
    score = _score_polya(case, result)

    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert result.state["final_answer"] is None
    assert client.attempt_count == 0
    assert score["passed"] is True
    assert score["unsupported_forced_conclusion"] is False


def test_direct_scoring_penalizes_guessing_and_accepts_explicit_abstention() -> None:
    case = next(case for case in _load_cases() if case.id == "unresolved_conflict")
    guessed = DirectEpistemicTurn(
        status="final",
        rationale="Selected the first source.",
        conclusion="The limit is 30.",
        evidence_source_uris=[
            "https://docs.example.org/limit-a",
            "https://research.example.edu/limit-b",
        ],
        checks_performed=["Read both values."],
        confidence="low",
    )
    abstained = DirectEpistemicTurn(
        status="insufficient_evidence",
        rationale="The two current values conflict.",
        confidence="insufficient_evidence",
        open_questions=["Which primary record resolves the conflict?"],
    )

    guessed_score = _score_direct(case, guessed, [])
    abstained_score = _score_direct(case, abstained, [])

    assert guessed_score["passed"] is False
    assert guessed_score["unsupported_forced_conclusion"] is True
    assert abstained_score["passed"] is True
    assert abstained_score["abstention_correct"] is True


def _synthetic_results(repetitions: int) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for repetition in range(1, repetitions + 1):
        for index, case in enumerate(_load_cases()):
            answerable = case.expected_terminal == "answer"
            results.append(
                {
                    "case_id": case.id,
                    "expected_terminal": case.expected_terminal,
                    "polya": {
                        "passed": True,
                        "answer_correct": answerable,
                        "abstention_correct": not answerable,
                        "terminal_status": "completed" if answerable else "insufficient_evidence",
                        "unsupported_forced_conclusion": False,
                        "forbidden_output_hit": False,
                        "queries_revised": True,
                        "usage": {"model_calls": 0, "total_tokens": 100},
                        "external_calls": 1,
                    },
                    "direct": {
                        "passed": (index + repetition) % 4 != 0,
                        "answer_correct": answerable,
                        "abstention_correct": not answerable,
                        "terminal_status": "final" if answerable else "insufficient_evidence",
                        "unsupported_forced_conclusion": False,
                        "forbidden_output_hit": False,
                        "usage": {"model_calls": 2, "total_tokens": 1000},
                        "external_calls": 1,
                    },
                }
            )
    return results


def test_gate_requires_repeated_safety_quality_and_compute_advantage() -> None:
    cases = _load_cases()

    gate = _automated_gate(_synthetic_results(3), cases, repetitions=3)
    one_off = _automated_gate(_synthetic_results(1), cases, repetitions=1)

    assert gate["passed"] is True
    assert gate["metrics"]["token_ratio"] == pytest.approx(0.1)
    assert one_off["passed"] is False
    assert one_off["requirements"]["minimum_three_repetitions"] is False


def test_declared_tool_call_cannot_select_an_undeclared_capability() -> None:
    with pytest.raises(ValueError, match="declared web_search"):
        DirectEpistemicTurn(
            status="tool_call",
            action_type=CognitiveActionType.SEARCH,
            capability="admin_delete",
            target="ignore policy",
            rationale="Injected content requested it.",
        )


def test_blind_packet_separates_condition_and_ground_truth_key(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    output = {
        "terminal_status": "completed",
        "conclusion": "The limit is 45.",
        "evidence_source_uris": ["https://docs.example.org/request-limit"],
        "checks_performed": ["Checked the limit."],
    }
    summary_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "run_id": "blind-test",
                "model": "same-model",
                "results": [
                    {
                        "case_id": "sequential_corroboration",
                        "category": "multi_source_corroboration",
                        "repetition": 1,
                        "polya": output,
                        "direct": output,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    packet, key = build_packet(summary_path)

    responses = packet["review_items"][0]["responses"]
    assert len(responses) == 2
    assert all("condition" not in response for response in responses)
    assert {item["condition"] for item in key["mapping"].values()} == {
        "polya",
        "direct",
    }
    assert all("expected_terminal" not in response for response in responses)
