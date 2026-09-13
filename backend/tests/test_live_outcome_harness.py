"""Offline contract tests for the fair live-outcome comparison harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evals.chapter_13c.build_blind_review_packet import build_packet
from evals.chapter_13c.run_live_outcome_comparison import (
    MAX_MODEL_CALLS,
    DirectOutcomeTurn,
    RecordingClient,
    _automated_gate,
    _execute_direct_tool,
    _execution_order,
    _fixture_executor,
    _initial_state,
    _load_cases,
    _parse_turn,
    _registry,
    _run_direct,
    _score_direct,
    _score_polya,
    _tool_definition,
    _usage,
)

from app.cognition import (
    CapabilityRegistry,
    CognitiveActionType,
    CognitiveController,
    CognitiveModelGateway,
    FunctionCapability,
)
from app.cognition.kernel import CognitiveKernel
from app.llm import (
    FakeLLMClient,
    LLMClientError,
    LLMErrorCode,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMRole,
    LLMTokenUsage,
)


def _tool_registry(case: dict[str, object]) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    tools = case["tools"]
    assert isinstance(tools, dict)
    for name, raw_spec in tools.items():
        assert isinstance(name, str)
        assert isinstance(raw_spec, dict)
        action_type = CognitiveActionType(str(raw_spec["action_type"]))
        definition = _tool_definition(name, action_type)
        registry.register(
            FunctionCapability(
                definition,
                _fixture_executor(case, name, definition),
            )
        )
    return registry


def _response(text: str) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="same-fake-model",
        text=text,
        finish_reason="stop",
        usage=LLMTokenUsage(input_tokens=40, output_tokens=20),
    )


def test_recording_client_counts_failed_provider_attempts_against_budget() -> None:
    client = RecordingClient(
        FakeLLMClient(
            [
                LLMClientError(
                    LLMErrorCode.TIMEOUT,
                    "Synthetic timeout.",
                    provider="fake",
                    retryable=True,
                ),
                _response('{"status":"final"}'),
            ]
        ),
        max_calls=1,
    )
    request = LLMRequest(
        model="same-fake-model",
        messages=[LLMMessage(role=LLMRole.USER, content="Return JSON.")],
    )

    with pytest.raises(LLMClientError):
        client.complete(request)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        client.complete(request)

    assert client.attempt_count == 1
    assert client.responses == []
    assert _usage(client)["model_calls"] == 1


def test_all_outcome_cases_route_to_the_expected_first_shared_tool() -> None:
    cases = _load_cases(None)

    assert len(cases) == 6
    for case in cases:
        selected = (
            CognitiveController()
            .decide(
                _initial_state(case, "offline-test"),
                _tool_registry(case),
            )
            .selected
        )
        assert selected.action_type.value == case["expected_first_action"]
        assert selected.capability in case["tools"]


def test_three_repetitions_balance_which_condition_runs_first() -> None:
    first_conditions = [
        _execution_order(case_index, repetition)[0]
        for repetition in range(1, 4)
        for case_index in range(6)
    ]

    assert first_conditions.count("polya") == 9
    assert first_conditions.count("direct") == 9


def _synthetic_gate_results(
    cases: list[dict[str, object]], repetitions: int = 3
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for repetition in range(1, repetitions + 1):
        for case_index, case in enumerate(cases):
            results.append(
                {
                    "case_id": case["id"],
                    "category": case["category"],
                    "repetition": repetition,
                    "polya": {
                        "passed": True,
                        "recovery_passed": True,
                        "unsupported_forced_conclusion": False,
                    },
                    "direct": {"passed": (case_index + repetition) % 3 != 0},
                }
            )
    return results


def test_automated_gate_enforces_the_full_win_threshold() -> None:
    cases = _load_cases(None)
    results = _synthetic_gate_results(cases)

    gate = _automated_gate(results, cases, repetitions=3)

    assert gate["passed"] is True
    assert gate["metrics"]["completed_comparison_pairs"] == 18
    assert gate["metrics"]["polya_pass_rate"] == 1.0
    assert gate["metrics"]["direct_pass_rate"] == pytest.approx(2 / 3)


def test_automated_gate_rejects_unsupported_conclusions_and_one_off_runs() -> None:
    cases = _load_cases(None)
    results = _synthetic_gate_results(cases, repetitions=1)
    results[0]["polya"]["unsupported_forced_conclusion"] = True

    gate = _automated_gate(results, cases, repetitions=1)

    assert gate["passed"] is False
    assert gate["requirements"]["minimum_three_repetitions"] is False
    assert gate["requirements"]["zero_unsupported_forced_conclusions"] is False


def test_direct_turn_parser_enforces_tool_and_final_shapes() -> None:
    tool_turn = _parse_turn(
        """```json
        {"status":"tool_call","action_type":"calculate","capability":"calculator",
        "target":"x","rationale":"Need exact evidence."}
        ```"""
    )
    final_turn = _parse_turn(
        """{"status":"final","rationale":"Checked the observation.",
        "conclusion":"x = 3","evidence_source_uris":["fixture://source"],
        "checks_performed":["substitution"],"confidence":"high"}"""
    )

    assert tool_turn.status == "tool_call"
    assert final_turn.conclusion == "x = 3"
    with pytest.raises(ValueError, match="final requires"):
        DirectOutcomeTurn(status="final", rationale="No conclusion.")


def test_recording_client_enforces_model_call_budget() -> None:
    client = RecordingClient(FakeLLMClient([_response("{}")]), max_calls=0)

    with pytest.raises(RuntimeError, match="model-call budget exhausted"):
        client.complete(
            LLMRequest(
                model="same-fake-model",
                messages=[LLMMessage(role=LLMRole.USER, content="bounded")],
            )
        )


def test_direct_condition_recovers_from_a_malformed_turn_within_its_budget() -> None:
    case = _load_cases(None)[1]
    source_uri = "fixture://chapter-13c-outcome/pagination_outcome/inspector"
    client = RecordingClient(
        FakeLLMClient(
            [
                _response(
                    '{"status":"tool_call","action_type":"inspect",'
                    '"capability_name":"inspector","target":"code",'
                    '"rationale":"Inspect it."}'
                ),
                _response(
                    '{"status":"tool_call","action_type":"inspect",'
                    '"capability":"inspector","target":"code",'
                    '"rationale":"Inspect it."}'
                ),
                _response(
                    f'{{"status":"final","rationale":"Checked source.",'
                    '"conclusion":"Use (page - 1) * page_size.",'
                    f'"evidence_source_uris":["{source_uri}"],'
                    '"checks_performed":["Compared both offsets."],'
                    '"confidence":"high"}'
                ),
            ]
        ),
        max_calls=MAX_MODEL_CALLS,
    )

    final, history, _, parse_error = _run_direct(case, "same-fake-model", client)

    assert final is not None
    assert len(history) == 1
    assert parse_error is not None
    assert len(client.responses) == 3


def test_equation_scoring_accepts_verified_conclusion_without_repeating_check_result() -> None:
    case = _load_cases(1)[0]
    final = DirectOutcomeTurn(
        status="final",
        rationale="Calculator evidence was checked by substitution.",
        conclusion="x=3",
        evidence_source_uris=["fixture://chapter-13c-outcome/equation_outcome/calculator"],
        checks_performed=["Substituted x into the original equation."],
        confidence="high",
    )
    history = [
        {
            "action_type": "calculate",
            "observation": {
                "status": "succeeded",
                "source_uri": ("fixture://chapter-13c-outcome/equation_outcome/calculator"),
            },
        }
    ]

    assert _score_direct(case, final, history)["passed"] is True


def test_direct_condition_cannot_call_undeclared_or_mismatched_tool() -> None:
    case = _load_cases(1)[0]
    undeclared = DirectOutcomeTurn(
        status="tool_call",
        action_type=CognitiveActionType.SEARCH,
        capability="web_search",
        target="x",
        rationale="Try an undeclared tool.",
    )
    mismatched = DirectOutcomeTurn(
        status="tool_call",
        action_type=CognitiveActionType.SEARCH,
        capability="calculator",
        target="x",
        rationale="Use the wrong action type.",
    )

    assert _execute_direct_tool(case, undeclared)["failure_kind"] == "undeclared_tool"
    assert _execute_direct_tool(case, mismatched)["failure_kind"] == "unsupported_action"


def test_blind_review_packet_separates_condition_identity(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    shared_output = {
        "conclusion": "x = 3 and substitution gives 10.",
        "evidence_source_uris": ["fixture://chapter-13c-outcome/equation_outcome/calculator"],
        "checks_performed": ["Substituted x into the equation."],
        "terminal_status": "completed",
    }
    summary_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "run_id": "test-run",
                "model": "test-model",
                "cases": [
                    {
                        "case_id": "equation_outcome",
                        "category": "mathematical_reasoning",
                        "repetition": 1,
                        "polya": shared_output,
                        "direct": shared_output,
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


def test_both_conditions_pass_and_polya_closes_attested_evidence_without_model() -> None:
    case = _load_cases(None)[1]
    source_uri = "fixture://chapter-13c-outcome/pagination_outcome/inspector"
    polya_responses = [
        _response(
            """{
              "hypotheses": [{
                "statement": "The one-based pagination offset is calculated incorrectly.",
                "mechanism": "Multiplying page by page_size skips the preceding page.",
                "origin": "direct_reasoning",
                "expected_signals": ["Page 2 begins after two page widths."],
                "verification_checks": ["Compare the expression with one-based indexing."],
                "falsification_criteria": ["The implementation already subtracts one."]
              }],
              "tasks": [{
                "id": "check-pagination-offset",
                "action": "Check the proposed correction against the inspected expression.",
                "tool_name": "deliberator",
                "params": {},
                "expected_output": "A source-grounded corrected offset.",
                "risk_level": "low"
              }],
              "execution_outputs": [{
                "task_id": "check-pagination-offset",
                "summary": "The inspected expression is off by one page.",
                "output": {"corrected_expression": "(page - 1) * page_size"}
              }]
            }"""
        ),
        _response(
            """{
              "report": {
                "passed": true,
                "checks_run": ["Compared both expressions for page 1 and page 2."],
                "failed_checks": [],
                "contradictions": [],
                "confidence_delta": 0.3
              },
              "final_answer": "Replace the faulty offset with (page - 1) * page_size.",
              "reflection": {
                "outcome_summary": "The pagination defect was source-grounded and verified.",
                "what_worked": ["Inspected the failing expression."],
                "reusable_lessons": ["Check indexing conventions at boundaries."]
              }
            }"""
        ),
    ]
    polya_client = RecordingClient(FakeLLMClient(polya_responses))
    polya_result = CognitiveKernel(
        _registry(case, CognitiveModelGateway(polya_client, "same-fake-model")),
        controller=CognitiveController(),
    ).run(_initial_state(case, "offline-polya"), max_cycles=12)

    direct_responses = [
        _response(
            """{
              "status": "tool_call",
              "action_type": "inspect",
              "capability": "inspector",
              "target": "the failing pagination code path",
              "rationale": "Inspect the reproducible failing path."
            }"""
        ),
        _response(
            f"""{{
              "status": "final",
              "rationale": "The source observation identifies an off-by-one page offset.",
              "conclusion": "Use (page - 1) * page_size.",
              "evidence_source_uris": ["{source_uri}"],
              "checks_performed": ["Checked page 1 and page 2 offsets."],
              "open_questions": [],
              "confidence": "high"
            }}"""
        ),
    ]
    direct_client = RecordingClient(FakeLLMClient(direct_responses))
    direct_final, direct_history, _, parse_error = _run_direct(
        case, "same-fake-model", direct_client
    )

    assert parse_error is None
    assert _score_polya(case, polya_result)["passed"] is True
    assert _score_direct(case, direct_final, direct_history)["passed"] is True
    assert len(polya_client.responses) == 0
    assert polya_client.attempt_count == 0
    assert len(direct_client.responses) == 2
