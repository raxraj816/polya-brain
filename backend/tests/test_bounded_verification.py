"""Verification uses remaining calls without bypassing review or overspending."""

import pytest

from app.cognition import (
    CapabilityRegistry,
    CognitiveKernel,
    CognitiveResourceBudget,
    CognitiveRunStatus,
    accumulated_usage,
)
from app.cognition.capabilities import AuditedCapabilityError
from app.cognition.model_capabilities import planner_capability
from app.cognition.model_gateway import CognitiveModelGateway
from app.cognition.on_demand_capabilities import conclusion_checker_capability
from app.cognition.semantic_broker import RoutedCognitiveModelGateway, SemanticModelRoute
from app.cognition.task_model import budget_event
from app.graph.state import ExecutionOutput, StateEvent, create_initial_state
from app.llm import FakeLLMClient, LLMClientError, LLMErrorCode, LLMResponse, LLMTokenUsage
from app.models.contracts import (
    ContractModel,
    Hypothesis,
    PlanTask,
    StructuredProblem,
    VerificationReport,
)


class Answer(ContractModel):
    answer: str


def response(text='{"answer":"supported"}'):
    return LLMResponse(
        provider="fake",
        model="primary",
        text=text,
        usage=LLMTokenUsage(input_tokens=30, output_tokens=20),
    )


def gateway(client, routed):
    if not routed:
        return CognitiveModelGateway(client, "primary")
    return RoutedCognitiveModelGateway(
        client,
        [
            SemanticModelRoute(model_slug="primary"),
            SemanticModelRoute(model_slug="fallback", priority=1),
        ],
    )


def complete(model, limit):
    return model.complete(
        capability="review",
        instructions="Independently review the candidate.",
        output_type=Answer,
        state=create_initial_state("Review this candidate."),
        max_output_tokens=512,
        max_provider_attempts=limit,
    )


@pytest.mark.parametrize("routed", [False, True])
@pytest.mark.parametrize("limit", [0, 1, 2, 3])
def test_malformed_output_cannot_spend_beyond_attempt_allowance(routed, limit):
    client = FakeLLMClient([response("malformed") for _ in range(8)])
    with pytest.raises(AuditedCapabilityError) as error:
        complete(gateway(client, routed), limit)
    expected = min(limit, 4 if routed else 2)
    assert len(client.requests) == expected
    assert error.value.payload["model_calls"] == expected
    assert error.value.payload["usage"]["output_tokens"] == expected * 20
    assert all(request.options.max_retries == 0 for request in client.requests)


@pytest.mark.parametrize("routed", [False, True])
def test_last_call_can_review_but_cannot_repair(routed):
    client = FakeLLMClient([response()])
    result = complete(gateway(client, routed), 1)
    assert result.output.answer == "supported"
    assert result.model_calls == len(client.requests) == 1


def test_fallback_and_schema_repairs_share_allowance():
    client = FakeLLMClient([response("bad"), response("bad"), response()])
    result = complete(gateway(client, True), 3)
    assert result.model_calls == 3
    assert [request.model for request in client.requests] == ["primary", "primary", "fallback"]
    assert result.usage.output_tokens == 60


@pytest.mark.parametrize("routed", [False, True])
def test_retry_consumes_allowance_and_unknown_usage_is_reserved(routed, monkeypatch):
    monkeypatch.setattr("app.llm.client._resolved_retry_delay", lambda *_: 0)
    error = LLMClientError(LLMErrorCode.TIMEOUT, "Timed out.", provider="fake", retryable=True)
    client = FakeLLMClient([error, response()])
    result = complete(gateway(client, routed), 2)
    assert result.model_calls == len(client.requests) == 2
    assert result.usage.output_tokens == 20
    assert result.unreported_output_token_reservation == 512


@pytest.mark.parametrize("routed", [False, True])
def test_retry_after_final_call_never_dispatches(routed, monkeypatch):
    monkeypatch.setattr("app.llm.client._resolved_retry_delay", lambda *_: 0)
    client = FakeLLMClient(
        [
            LLMClientError(LLMErrorCode.TIMEOUT, "Timed out.", provider="fake", retryable=True),
            response(),
        ]
    )
    with pytest.raises(AuditedCapabilityError) as error:
        complete(gateway(client, routed), 1)
    assert len(client.requests) == error.value.payload["model_calls"] == 1
    assert error.value.payload["unreported_output_token_reservation"] == 512


def review_state(spent_calls, output_budget=20_000, *, private=False):
    state = create_initial_state("Review the supplied technical analysis.")
    state["structured_problem"] = StructuredProblem(
        core_question=state["raw_input"],
        problem_type="technical_analysis",
        success_criteria=["Check the supported conclusion."],
        constraints=["Contains sensitive data; do not send it to external models."]
        if private
        else [],
    )
    state["hypotheses"] = [
        Hypothesis(statement="The supplied analysis is supported.", origin="direct_reasoning")
    ]
    state["plan"] = [
        PlanTask(id="analysis", action="Analyze supplied facts", tool_name="deliberator")
    ]
    state["execution_outputs"] = [
        ExecutionOutput(task_id="analysis", summary="Candidate analysis.")
    ]
    state["events"] = [
        StateEvent(
            reasoning_mode="verify",
            engine_name="constraint_discovery",
            event_type="completed",
            summary="Done.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            reasoning_mode="verify",
            engine_name="task_gap_detector",
            event_type="gap_detection_completed",
            summary="No gaps.",
        ),
        budget_event(CognitiveResourceBudget(max_model_calls=6, max_output_tokens=output_budget)),
        StateEvent(
            reasoning_mode="verify",
            engine_name="cognitive_kernel",
            event_type="cognitive_resource_usage",
            summary="Prior calls.",
            metadata={"model_calls": spent_calls},
        ),
    ]
    return state


VERDICT = """{"report":{"passed":true,"checks_run":["Checked supplied analysis."],"failed_checks":[]},
"final_answer":"The conclusion is supported.","reflection":{"outcome_summary":"Reviewed supplied analysis."}}"""


@pytest.mark.parametrize(
    "spent_calls, output_budget, allowed", [(3, 20_000, 3), (5, 20_000, 1), (3, 3200, 1)]
)
def test_kernel_and_checkpoint_admit_bounded_review(spent_calls, output_budget, allowed):
    client = FakeLLMClient([response(VERDICT)])
    registry = CapabilityRegistry()
    registry.register(conclusion_checker_capability(gateway(client, True)))
    state = review_state(spent_calls, output_budget)
    result = CognitiveKernel(registry).run(state, max_cycles=2, checkpoint=lambda *_: None)
    assert result.status is CognitiveRunStatus.COMPLETED
    assert result.state["verification"].passed
    assert result.state["final_answer"] == "The conclusion is supported."
    assert accumulated_usage(result.state).model_calls == spent_calls + 1
    assert result.observations[0].payload["reserved_model_calls"] == allowed
    assert result.observations[0].payload["reserved_output_tokens"] == allowed * 3200


@pytest.mark.parametrize("spent_calls, output_budget", [(6, 20_000), (5, 3199)])
def test_exhausted_budget_never_dispatches_review(spent_calls, output_budget):
    client = FakeLLMClient([response(VERDICT)])
    registry = CapabilityRegistry()
    registry.register(conclusion_checker_capability(gateway(client, True)))
    result = CognitiveKernel(registry).run(review_state(spent_calls, output_budget), max_cycles=2)
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert not client.requests
    assert result.state["final_answer"] is None


def test_unknown_failure_reservation_reaches_kernel_ledger(monkeypatch):
    monkeypatch.setattr("app.llm.client._resolved_retry_delay", lambda *_: 0)
    client = FakeLLMClient(
        [
            LLMClientError(LLMErrorCode.TIMEOUT, "Timed out.", provider="fake", retryable=True),
            response(VERDICT),
        ]
    )
    registry = CapabilityRegistry()
    registry.register(conclusion_checker_capability(gateway(client, True)))
    result = CognitiveKernel(registry).run(review_state(3), max_cycles=2)
    assert result.status is CognitiveRunStatus.COMPLETED
    usage = accumulated_usage(result.state)
    assert usage.model_calls == 5
    assert usage.output_tokens == 3200 + 20


def test_bounded_review_preserves_privacy_gate():
    client = FakeLLMClient([response(VERDICT)])
    registry = CapabilityRegistry()
    registry.register(conclusion_checker_capability(gateway(client, True)))
    result = CognitiveKernel(registry).run(review_state(5, private=True), max_cycles=2)
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert not client.requests


PLAN = """{"tasks":[{"id":"recovery","action":"Recheck the candidate","tool_name":"python_sandbox","risk_level":"medium","params":{"code":"value=1","tests":["assert value==1"]}}]}"""


@pytest.mark.parametrize("spent, tokens, expected", [(3, 20000, 3), (5, 20000, 1), (3, 6000, 1)])
def test_recovery_planner_can_use_remaining_budget_with_checkpoints(spent, tokens, expected):
    client = FakeLLMClient([response(PLAN)])
    registry = CapabilityRegistry()
    capability = planner_capability(
        gateway(client, True), available_execution_tools=("python_sandbox",)
    )
    registry.register(capability)
    state = review_state(spent, tokens)
    state["verification"] = VerificationReport(
        passed=False, checks_run=["Checked candidate"], failed_checks=["Needs correction"]
    )
    result = CognitiveKernel(registry).run(state, max_cycles=1, checkpoint=lambda *_: None)
    assert len(client.requests) == 1
    assert result.state["plan"][-1].id == "recovery"
    assert result.observations[0].payload["reserved_model_calls"] == expected
    assert result.observations[0].payload["reserved_output_tokens"] == expected * 6000
    assert accumulated_usage(result.state).model_calls == spent + 1
    assert (
        "Treat model-generated expected answers as hypotheses"
        in client.requests[0].messages[0].content
    )


@pytest.mark.parametrize(
    "spent, tokens, private", [(6, 20000, False), (5, 5999, False), (5, 20000, True)]
)
def test_recovery_planner_does_not_bypass_exhaustion_or_privacy(spent, tokens, private):
    client = FakeLLMClient([response(PLAN)])
    registry = CapabilityRegistry()
    registry.register(
        planner_capability(gateway(client, True), available_execution_tools=("python_sandbox",))
    )
    state = review_state(spent, tokens, private=private)
    state["verification"] = VerificationReport(
        passed=False, checks_run=["Checked candidate"], failed_checks=["Failed"]
    )
    result = CognitiveKernel(registry).run(state, max_cycles=2)
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert not client.requests


def test_recovery_planner_schema_repair_cannot_exceed_last_call():
    client = FakeLLMClient([response("invalid"), response(PLAN)])
    registry = CapabilityRegistry()
    registry.register(
        planner_capability(gateway(client, True), available_execution_tools=("python_sandbox",))
    )
    state = review_state(5)
    state["verification"] = VerificationReport(
        passed=False, checks_run=["Checked candidate"], failed_checks=["Failed"]
    )
    result = CognitiveKernel(registry).run(state, max_cycles=2)
    assert len(client.requests) == 1
    assert accumulated_usage(result.state).model_calls == 6
    assert result.state["final_answer"] is None
