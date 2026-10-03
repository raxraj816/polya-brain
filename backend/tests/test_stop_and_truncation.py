"""Truncated model answers, share-link inputs, and explaining runs that stop early."""

from __future__ import annotations

import pytest

from app.cognition import (
    AuditedCapabilityError,
    CognitiveActionCandidate,
    CognitiveActionType,
    ObservationStatus,
    RoutedCognitiveModelGateway,
    SemanticModelRoute,
    problem_representation_capability,
)
from app.cognition.input_links import unreadable_share_link
from app.cognition.model_gateway import (
    CognitiveModelGateway,
    ModelOutputTruncatedError,
    response_truncated,
)
from app.cognition.stop_explanation import explain_stop
from app.graph.state import create_initial_state
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.models.contracts import ContractModel, NonEmptyStr


class Answer(ContractModel):
    answer: NonEmptyStr


def reply(text: str, *, finish: str | None = "stop") -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="fake-model",
        text=text,
        finish_reason=finish,
        usage=LLMTokenUsage(input_tokens=10, output_tokens=5),
    )


CUT = reply('{"answer": "an architecture that goes on and on', finish="length")


def complete(client: FakeLLMClient) -> Answer:
    return (
        CognitiveModelGateway(client, "fake-model")
        .complete(
            capability="deliberator",
            instructions="Return the answer.",
            output_type=Answer,
            state=create_initial_state("Design exactly-once payments."),
            max_output_tokens=1800,
            total_timeout_seconds=60,
        )
        .output
    )


def test_truncated_answer_is_retried_compactly_within_the_same_limit() -> None:
    client = FakeLLMClient([CUT, reply('{"answer": "compact design"}')])
    assert complete(client).answer == "compact design"
    first, second = client.requests
    assert "CUT OFF AT THE 1800-TOKEN OUTPUT LIMIT" in second.messages[0].content
    assert second.options.max_output_tokens == first.options.max_output_tokens == 1800
    # The truncated text is not resent; the retry asks for a fresh complete answer.
    assert second.messages[1].content == first.messages[1].content
    assert "goes on and on" not in second.messages[1].content


def test_repeated_truncation_is_labelled_not_disguised_as_a_schema_error() -> None:
    with pytest.raises(ModelOutputTruncatedError):
        complete(FakeLLMClient([CUT, reply('{"answer": "still too long', finish="length")]))


def test_ordinary_malformed_answers_keep_the_existing_repair_path() -> None:
    client = FakeLLMClient([reply('{"wrong": 1}'), reply('{"answer": "repaired"}')])
    assert complete(client).answer == "repaired"
    assert (
        "Repair one malformed structured capability response"
        in client.requests[1].messages[0].content
    )


def test_finish_reason_variants() -> None:
    assert response_truncated(reply("x", finish="length"))
    assert response_truncated(reply("x", finish="MAX_TOKENS"))
    assert not response_truncated(reply("x", finish="stop"))
    assert not response_truncated(reply("x", finish=None))


def test_routed_gateway_reports_output_truncation_as_the_terminal_reason() -> None:
    gateway = RoutedCognitiveModelGateway(
        FakeLLMClient([CUT, reply('{"answer": "cut again', finish="length")]),
        [SemanticModelRoute(model_slug="provider/primary", priority=0, timeout_seconds=60)],
    )
    with pytest.raises(AuditedCapabilityError) as caught:
        gateway.complete(
            capability="deliberator",
            instructions="Return the answer.",
            output_type=Answer,
            state=create_initial_state("Design exactly-once payments."),
            total_timeout_seconds=60,
        )
    payload = caught.value.payload
    assert payload["terminal_failure_kind"] == "output_truncated"
    assert payload["route_attempts"][0]["failure_kind"] == "output_truncated"


def test_deliberator_gets_the_full_allowance_without_the_sandbox() -> None:
    from app.cognition import on_demand_cognitive_capabilities

    gateway = CognitiveModelGateway(FakeLLMClient([]), "fake-model")
    deliberator = next(
        capability
        for capability in on_demand_cognitive_capabilities(gateway, allow_python_sandbox=False)
        if capability.definition.name == "deliberator"
    )
    assert deliberator.definition.max_output_tokens == 6000


@pytest.mark.parametrize(
    ("text", "product"),
    [
        ("https://chatgpt.com/share/6abfc21e-a174-83ee-a431-24aa80129458", "ChatGPT"),
        ("  https://chat.openai.com/share/abc  ", "ChatGPT"),
        ("https://claude.ai/share/123", "Claude"),
        ("https://www.perplexity.ai/search/xyz", "Perplexity"),
        ("https://chatgpt.com/share/abc and explain this", None),
        ("https://example.com/share/abc", None),
        ("Why does https://chatgpt.com/share/abc fail?", None),
        ("https://chatgpt.com/c/abc", None),
    ],
)
def test_share_link_detection(text: str, product: str | None) -> None:
    assert unreadable_share_link(text) == product


def test_share_link_input_asks_for_the_text_without_a_model_call() -> None:
    class Engine:
        class version:  # noqa: N801 - mimics the engine's version attribute
            engine = "test-engine@1"

        max_provider_attempts = 4

    capability = problem_representation_capability(Engine())  # type: ignore[arg-type]
    observation = capability.execute(
        CognitiveActionCandidate(
            id="interpret",
            action_type=CognitiveActionType.INTERPRET,
            target="raw problem",
            purpose="Represent the problem.",
            expected_observation="A structured problem.",
            expected_usefulness=1.0,
            estimated_cost=0.1,
            capability="problem_representation",
            success_condition="Representation passes.",
            failure_condition="No representation.",
        ),
        create_initial_state("https://chatgpt.com/share/6abfc21e-a174-83ee-a431-24aa80129458"),
    )
    assert observation.status is ObservationStatus.BLOCKED
    assert observation.payload == {"model_calls": 0, "procedure": "deterministic"}
    (question,) = observation.proposed_update.questions_to_ask
    assert "cannot open ChatGPT share links" in question and "Paste" in question


def recorded_trace(route_failure: str, terminal: str) -> list[tuple[str, dict, str]]:
    """The shape of the failed exactly-once payments session, event for event."""
    observation = "capability_observation"
    events: list[tuple[str, dict, str]] = [
        (
            observation,
            {
                "capability": "problem_representation",
                "status": "blocked",
                "failure_kind": "human_input_required",
            },
            "Problem representation needs user clarification before promotion.",
        ),
        ("clarification_answered", {}, "Received user clarification."),
        (
            observation,
            {"capability": "problem_representation", "status": "succeeded"},
            "Created and contract-validated the structured problem.",
        ),
        (
            observation,
            {"capability": "constraint_discovery", "status": "succeeded"},
            "Discovered and validated explicit and implicit constraints.",
        ),
    ]
    events += [("constraint_discovered", {}, "Discovered other constraint.")] * 17
    events += [
        (
            observation,
            {"capability": "task_gap_detector", "status": "succeeded"},
            "Constructed 0 explicit blocking gap(s) deterministically.",
        ),
        (
            observation,
            {
                "capability": "deliberator",
                "status": "failed",
                "failure_kind": "semantic_routes_exhausted",
                "terminal_failure_kind": terminal,
                "model_calls": 2,
                "route_attempts": [{"route": "openrouter/auto", "failure_kind": route_failure}],
            },
            "All configured semantic routes failed safely.",
        ),
        (
            "cognitive_action_decision",
            {"selected": {"action_type": "stop"}},
            "Selected stop for current run.",
        ),
    ]
    return events


def test_the_recorded_failed_session_now_explains_itself() -> None:
    explanation = explain_stop(recorded_trace("schema_validation", "malformed_response"))
    assert explanation.progress == [
        "Problem framing: Created and contract-validated the structured problem.",
        "Constraint discovery: identified 17 explicit and implicit constraints.",
        "Knowledge-gap check: Constructed 0 explicit blocking gap(s) deterministically.",
    ]
    assert (
        explanation.failure is not None
        and "did not match the required structure" in explanation.failure
    )
    assert "OPENROUTER_MODEL" in (explanation.next_action or "")


def test_truncation_stop_recommends_asking_in_parts() -> None:
    explanation = explain_stop(recorded_trace("output_truncated", "output_truncated"))
    assert "cut off at its output limit on every attempt (2 model attempts)" in (
        explanation.failure or ""
    )
    assert "one part at a time" in (explanation.next_action or "")
    assert explanation.headline.startswith(
        "PolyaBrain stopped without a verified conclusion: Solution design"
    )


def test_provider_refusal_and_clean_runs() -> None:
    refusal = [
        (
            "capability_observation",
            {"capability": "deliberator", "status": "failed", "failure_kind": "permission"},
            "x",
        )
    ]
    assert "credits" in (explain_stop(refusal).failure or "")
    recovered = [
        (
            "capability_observation",
            {"capability": "deliberator", "status": "failed", "failure_kind": "timeout"},
            "x",
        ),
        (
            "capability_observation",
            {"capability": "deliberator", "status": "succeeded"},
            "Constructed 2 candidate(s).",
        ),
    ]
    assert explain_stop(recovered).failure is None


def stopped_result():  # noqa: ANN201
    from app.cognition import CognitiveRunStatus
    from app.cognition.kernel import CognitiveRunResult
    from app.graph.state import StateEvent
    from app.models.contracts import ReasoningMode

    state = create_initial_state(
        "Design exactly-once payments.", session_id="11111111-1111-4111-8111-111111111111"
    )
    state["events"] = [
        StateEvent(
            engine_name="cognitive_kernel",
            event_type=event_type,
            reasoning_mode=ReasoningMode.EXECUTE,
            summary=summary,
            metadata=metadata,
        )
        for event_type, metadata, summary in recorded_trace("output_truncated", "output_truncated")
    ]
    return CognitiveRunResult(
        status=CognitiveRunStatus.INSUFFICIENT_EVIDENCE,
        state=state,
        decisions=(),
        observations=(),
        cycles=6,
    )


def test_session_final_answer_states_why_the_run_stopped() -> None:
    from app.cognition.session_runner import CognitiveSessionRunner

    class Runtime:
        def run_problem(self, raw_input, **kwargs):  # noqa: ANN001, ANN003, ANN201
            return stopped_result()

    execution = CognitiveSessionRunner(Runtime())(
        "Design exactly-once payments.", session_id="11111111-1111-4111-8111-111111111111"
    )  # type: ignore[arg-type]
    answer = execution.state["final_answer"] or ""
    assert answer.startswith("PolyaBrain stopped without a verified conclusion: Solution design")
    assert "cut off at its output limit" in answer and answer.endswith("insufficient_evidence.")


def test_cli_report_shows_progress_failure_and_next_action() -> None:
    from app.investigator.artifacts import report_from_result

    report = report_from_result(stopped_result())
    assert report.final_conclusion.startswith("PolyaBrain stopped without a verified conclusion")
    assert "identified 17 explicit and implicit constraints" in " ".join(report.checks_performed)
    assert report.failed_checks and "cut off" in report.failed_checks[0]
    assert "one part at a time" in report.recommended_next_action
