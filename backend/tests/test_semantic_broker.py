"""Chapter 13-H tests for deterministic semantic route brokerage."""

from __future__ import annotations

import json

import pytest

from app.cognition import (
    AuditedCapabilityError,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveKernel,
    CognitiveResourceBudget,
    CognitiveRunStatus,
    ObservationStatus,
    RoutedCognitiveModelGateway,
    RoutedProblemUnderstandingProvider,
    SemanticModelRoute,
    SemanticRouteHealthLedger,
    SemanticRouteSample,
    accumulated_usage,
    on_demand_cognitive_capabilities,
    problem_representation_capability,
)
from app.engines import ProblemRepresentationEngine
from app.graph.state import StateEvent, create_initial_state
from app.llm import (
    FakeLLMClient,
    LLMClientError,
    LLMErrorCode,
    LLMResponse,
    LLMTokenUsage,
)
from app.models.contracts import (
    ContractModel,
    NonEmptyStr,
    ReasoningMode,
    StructuredProblem,
)
from app.problem_understanding import PROBLEM_UNDERSTANDING_EXAMPLES


class BrokerOutput(ContractModel):
    answer: NonEmptyStr


def _response(answer: str, *, model: str) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model=model,
        text=f'{{"answer":"{answer}"}}',
        usage=LLMTokenUsage(input_tokens=10, output_tokens=5),
    )


def _problem_response(*, model: str) -> LLMResponse:
    output = PROBLEM_UNDERSTANDING_EXAMPLES[2].output
    return LLMResponse(
        provider="fake",
        model=model,
        text=output.model_dump_json(),
        usage=LLMTokenUsage(input_tokens=20, output_tokens=30),
    )


def _interpret_action() -> CognitiveActionCandidate:
    return CognitiveActionCandidate(
        id="interpret-through-semantic-broker",
        action_type=CognitiveActionType.INTERPRET,
        target="raw problem",
        purpose="Create a contract-validated problem representation.",
        expected_observation="A structured problem or an audited route failure.",
        expected_usefulness=1.0,
        estimated_cost=0.1,
        capability="problem_representation",
        success_condition="A structured problem passes the representation contract.",
        failure_condition="No configured route returns a valid representation.",
    )


def _retryable_timeout() -> LLMClientError:
    return LLMClientError(
        LLMErrorCode.TIMEOUT,
        "The synthetic route timed out.",
        provider="fake",
        retryable=True,
    )


def _routes() -> list[SemanticModelRoute]:
    return [
        SemanticModelRoute(model_slug="provider/primary", priority=0, timeout_seconds=60),
        SemanticModelRoute(model_slug="provider/fallback", priority=1, timeout_seconds=60),
    ]


def _complete(gateway: RoutedCognitiveModelGateway) -> BrokerOutput:
    result = gateway.complete(
        capability="test_semantic_contract",
        instructions="Return the supplied bounded answer.",
        output_type=BrokerOutput,
        state=create_initial_state("Return a bounded answer."),
        total_timeout_seconds=60,
    )
    return result.output


def test_primary_success_uses_one_route_and_one_real_provider_attempt() -> None:
    client = FakeLLMClient([_response("primary", model="provider/primary")])
    gateway = RoutedCognitiveModelGateway(client, _routes())

    result = gateway.complete(
        capability="test_semantic_contract",
        instructions="Return the supplied bounded answer.",
        output_type=BrokerOutput,
        state=create_initial_state("Return a bounded answer."),
    )

    assert result.output.answer == "primary"
    assert result.model_calls == 1
    assert [item.route for item in result.route_attempts] == ["provider/primary"]
    assert result.route_attempts[0].succeeded is True
    assert result.usage.total_tokens == 15
    assert len(client.requests) == 1


def test_routed_gateway_preserves_capability_state_projection() -> None:
    client = FakeLLMClient([_response("primary", model="provider/primary")])
    gateway = RoutedCognitiveModelGateway(client, _routes())
    projection = {"projection_version": "test@1.0.0", "problem": "bounded"}

    gateway.complete(
        capability="test_semantic_contract",
        instructions="Return the supplied bounded answer.",
        output_type=BrokerOutput,
        state=create_initial_state("This duplicated raw state must not be sent."),
        state_projection=projection,
    )

    payload = json.loads(client.requests[0].messages[1].content)
    assert payload["current_state"] == projection


def test_typed_primary_failure_falls_back_and_counts_failed_attempts() -> None:
    client = FakeLLMClient(
        [
            _retryable_timeout(),
            _retryable_timeout(),
            _response("fallback", model="provider/fallback"),
        ]
    )
    ledger = SemanticRouteHealthLedger()
    gateway = RoutedCognitiveModelGateway(client, _routes(), health_ledger=ledger)

    result = gateway.complete(
        capability="test_semantic_contract",
        instructions="Return the supplied bounded answer.",
        output_type=BrokerOutput,
        state=create_initial_state("Return a bounded answer."),
        total_timeout_seconds=60,
    )

    assert result.output.answer == "fallback"
    assert result.model_calls == 3
    assert [item.succeeded for item in result.route_attempts] == [False, True]
    assert result.route_attempts[0].provider_attempts == 2
    assert result.route_attempts[0].failure_kind == "timeout"
    assert result.route_attempts[1].provider_attempts == 1
    assert ledger.sample_count() == 2
    assert [request.model for request in client.requests] == [
        "provider/primary",
        "provider/primary",
        "provider/fallback",
    ]
    assert client.requests[0].options.total_timeout_seconds == pytest.approx(30, abs=0.1)
    assert client.requests[-1].options.total_timeout_seconds == pytest.approx(60, abs=1.0)


def test_schema_failure_can_fall_back_but_authentication_failure_cannot() -> None:
    schema_client = FakeLLMClient(
        [
            LLMResponse(provider="fake", model="provider/primary", text="not-json"),
            LLMResponse(provider="fake", model="provider/primary", text="still-not-json"),
            _response("fallback", model="provider/fallback"),
        ]
    )
    schema_gateway = RoutedCognitiveModelGateway(schema_client, _routes())

    schema_result = schema_gateway.complete(
        capability="schema_contract",
        instructions="Return valid JSON.",
        output_type=BrokerOutput,
        state=create_initial_state("Return valid JSON."),
    )

    assert schema_result.output.answer == "fallback"
    assert schema_result.model_calls == 3
    assert schema_result.route_attempts[0].failure_kind == "schema_validation"

    authentication = LLMClientError(
        LLMErrorCode.AUTHENTICATION,
        "Authentication failed.",
        provider="fake",
        retryable=False,
    )
    auth_client = FakeLLMClient(
        [authentication, _response("must-not-run", model="provider/fallback")]
    )
    auth_gateway = RoutedCognitiveModelGateway(auth_client, _routes())

    with pytest.raises(AuditedCapabilityError) as exc_info:
        _complete(auth_gateway)

    assert exc_info.value.failure_kind == LLMErrorCode.AUTHENTICATION.value
    assert isinstance(exc_info.value.payload, dict)
    assert exc_info.value.payload["model_calls"] == 1
    assert exc_info.value.payload["terminal_failure_kind"] == "authentication"
    assert len(auth_client.requests) == 1


def test_repeated_failure_opens_circuit_then_probe_recovers_primary() -> None:
    client = FakeLLMClient(
        [
            _retryable_timeout(),
            _retryable_timeout(),
            _response("fallback-1", model="provider/fallback"),
            _retryable_timeout(),
            _retryable_timeout(),
            _response("fallback-2", model="provider/fallback"),
            _response("fallback-3", model="provider/fallback"),
            _response("fallback-4", model="provider/fallback"),
            _response("primary-recovered", model="provider/primary"),
        ]
    )
    ledger = SemanticRouteHealthLedger(circuit_failure_threshold=2, probe_interval=3)
    gateway = RoutedCognitiveModelGateway(client, _routes(), health_ledger=ledger)

    answers = [_complete(gateway).answer for _ in range(5)]

    assert answers == [
        "fallback-1",
        "fallback-2",
        "fallback-3",
        "fallback-4",
        "primary-recovered",
    ]
    assert [request.model for request in client.requests[6:]] == [
        "provider/fallback",
        "provider/fallback",
        "provider/primary",
    ]
    profile = ledger.profile("test_semantic_contract", _routes()[0])
    assert profile.consecutive_failures == 0
    assert profile.circuit_open is False


def test_route_version_isolation_and_bounded_configuration() -> None:
    ledger = SemanticRouteHealthLedger()
    first = _routes()[0]
    ledger.record(
        # This history must not transfer to a different model slug.
        SemanticRouteSample(
            sequence=1,
            capability="contract",
            route_version=first.version,
            succeeded=False,
            failure_kind="timeout",
            duration_ms=100,
            provider_attempts=1,
        )
    )
    changed = SemanticModelRoute(model_slug="provider/primary-v2")

    assert ledger.profile("contract", first).sample_count == 1
    assert ledger.profile("contract", changed).sample_count == 0

    with pytest.raises(ValueError, match="one primary and one fallback"):
        RoutedCognitiveModelGateway(
            FakeLLMClient([]),
            [*_routes(), SemanticModelRoute(model_slug="provider/third")],
        )


def test_total_route_failure_is_audited_and_cannot_create_final_answer() -> None:
    client = FakeLLMClient([_retryable_timeout() for _ in range(4)])
    gateway = RoutedCognitiveModelGateway(client, _routes())
    registry = CapabilityRegistry()
    for capability in on_demand_cognitive_capabilities(gateway):
        registry.register(capability)
    state = create_initial_state("Resolve a semantic task safely.", max_iterations=3)
    state["structured_problem"] = StructuredProblem(
        core_question="What conclusion is supported?",
        problem_type="semantic_test",
        knowns=["No deterministic procedure applies."],
        unknowns=[],
        constraints=["Do not force an unsupported conclusion."],
        success_criteria=["Return only a verified conclusion."],
    )
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints were supplied.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="task_gap_detector",
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="No acquisition gap remains.",
            metadata={"status": "ok"},
        ),
    ]

    result = CognitiveKernel(registry).run(
        state,
        max_cycles=3,
        budget=CognitiveResourceBudget(
            max_model_calls=12,
            max_duration_ms=120_000,
        ),
    )

    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert result.state["final_answer"] is None
    assert len(result.observations) == 1
    assert result.observations[0].failure_kind == "semantic_routes_exhausted"
    assert result.observations[0].payload is not None
    assert accumulated_usage(result.state).model_calls == 4
    assert len(client.requests) == 4
    observation_events = [
        event for event in result.state["events"] if event.event_type == "capability_observation"
    ]
    assert len(observation_events) == 1
    assert observation_events[0].metadata["model_calls"] == 4
    route_attempts = observation_events[0].metadata["route_attempts"]
    assert isinstance(route_attempts, list)
    assert [item["route"] for item in route_attempts if isinstance(item, dict)] == [
        "provider/primary",
        "provider/fallback",
    ]
    assert all(item["succeeded"] is False for item in route_attempts if isinstance(item, dict))


def test_problem_representation_uses_the_same_typed_fallback_and_call_ledger() -> None:
    client = FakeLLMClient(
        [
            _retryable_timeout(),
            _retryable_timeout(),
            _problem_response(model="provider/fallback"),
        ]
    )
    provider = RoutedProblemUnderstandingProvider(client, _routes())
    engine = ProblemRepresentationEngine(
        client=client,
        model="provider/primary",
        understanding_provider=provider,
        fallback=lambda *_args, **_kwargs: None,
    )
    capability = problem_representation_capability(engine)
    state = create_initial_state(PROBLEM_UNDERSTANDING_EXAMPLES[2].raw_input)

    observation = capability.execute(_interpret_action(), state)

    assert capability.definition.max_model_calls == 8
    assert observation.status is ObservationStatus.SUCCEEDED
    assert observation.proposed_update.structured_problem is not None
    assert isinstance(observation.payload, dict)
    assert observation.payload["model_calls"] == 3
    attempts = observation.payload["route_attempts"]
    assert isinstance(attempts, list)
    assert [item["route"] for item in attempts if isinstance(item, dict)] == [
        "provider/primary",
        "provider/fallback",
    ]
    route_events = [
        event
        for event in observation.proposed_update.trace_events_to_add
        if event.event_type == "semantic_routes_attempted"
    ]
    assert len(route_events) == 1
    assert route_events[0].metadata["model_calls"] == 3
    assert [request.model for request in client.requests] == [
        "provider/primary",
        "provider/primary",
        "provider/fallback",
    ]


def test_problem_representation_exhaustion_returns_no_structured_problem() -> None:
    client = FakeLLMClient([_retryable_timeout() for _ in range(4)])
    provider = RoutedProblemUnderstandingProvider(client, _routes())
    engine = ProblemRepresentationEngine(
        client=client,
        model="provider/primary",
        understanding_provider=provider,
        fallback=lambda *_args, **_kwargs: None,
    )
    capability = problem_representation_capability(engine)

    observation = capability.execute(
        _interpret_action(),
        create_initial_state("Investigate an unfamiliar production failure."),
    )

    assert observation.status is ObservationStatus.INCONCLUSIVE
    assert observation.failure_kind == "semantic_routes_exhausted"
    assert observation.proposed_update.structured_problem is None
    assert isinstance(observation.payload, dict)
    assert observation.payload["model_calls"] == 4
    attempts = observation.payload["route_attempts"]
    assert isinstance(attempts, list)
    assert len(attempts) == 2
    assert len(client.requests) == 4
