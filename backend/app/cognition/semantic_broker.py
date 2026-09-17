"""Deterministic multi-route semantic capability broker for Chapter 13-H."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from statistics import median
from time import perf_counter
from typing import Annotated, TypeVar

from pydantic import Field, JsonValue

from app.cognition.capabilities import AuditedCapabilityError
from app.cognition.model_gateway import (
    COGNITIVE_CAPABILITY_PROMPT_VERSION,
    CognitiveModelGateway,
    ModelCapabilityParseError,
    ModelCapabilityResult,
)
from app.graph.state import PolyaState
from app.llm import (
    AttemptCountingLLMClient,
    LLMClient,
    LLMClientError,
    LLMErrorCode,
    LLMRequestOptions,
    LLMResponse,
    LLMRouteAttemptTelemetry,
    LLMTokenUsage,
)
from app.models.contracts import ContractModel, NonEmptyStr, ProductMode, Score
from app.problem_understanding import ProblemUnderstandingRunResult, generate_problem_understanding
from app.problem_understanding.prompt import PROBLEM_UNDERSTANDING_MAX_OUTPUT_TOKENS
from app.problem_understanding.routing import (
    ProblemUnderstandingExecution,
    ProblemUnderstandingProviderError,
)

BROKER_POLICY_VERSION = "semantic-route-broker@0.2.0"
_FALLBACK_CODES = {
    LLMErrorCode.RATE_LIMIT,
    LLMErrorCode.TIMEOUT,
    LLMErrorCode.UNAVAILABLE,
    LLMErrorCode.MALFORMED_RESPONSE,
    LLMErrorCode.PROVIDER_ERROR,
}
OutputT = TypeVar("OutputT", bound=ContractModel)
RouteOutputT = TypeVar("RouteOutputT")


class SemanticModelRoute(ContractModel):
    """One explicitly configured model route eligible for semantic work."""

    model_slug: NonEmptyStr
    priority: Annotated[int, Field(ge=0, le=100)] = 0
    timeout_seconds: Annotated[float, Field(ge=1.0, le=300.0)] = 45.0

    @property
    def version(self) -> str:
        fingerprint = hashlib.sha256(self.model_slug.encode()).hexdigest()[:12]
        return f"model-route-{fingerprint}"


class SemanticRouteSample(ContractModel):
    """One capability-specific route outcome without prompt or response content."""

    sequence: Annotated[int, Field(ge=1)]
    capability: NonEmptyStr
    route_version: NonEmptyStr
    succeeded: bool
    failure_kind: NonEmptyStr | None = None
    duration_ms: Annotated[float, Field(ge=0.0)]
    provider_attempts: Annotated[int, Field(ge=0)]


class SemanticRouteHealthProfile(ContractModel):
    """Bounded route health scoped to one semantic output contract."""

    capability: NonEmptyStr
    route_version: NonEmptyStr
    sample_count: Annotated[int, Field(ge=0)]
    successes: Annotated[int, Field(ge=0)]
    consecutive_failures: Annotated[int, Field(ge=0)]
    smoothed_reliability: Score
    median_duration_ms: Annotated[float, Field(ge=0.0)]
    last_attempt_sequence: Annotated[int, Field(ge=0)]
    circuit_open: bool


type RouteHealthKey = tuple[str, str]


class SemanticRouteHealthLedger:
    """Process-local health evidence with bounded circuits and recovery probes."""

    def __init__(
        self,
        *,
        max_samples_per_profile: int = 100,
        circuit_failure_threshold: int = 2,
        probe_interval: int = 3,
    ) -> None:
        if not 5 <= max_samples_per_profile <= 10_000:
            raise ValueError("max_samples_per_profile must be between 5 and 10000")
        if not 1 <= circuit_failure_threshold <= 10:
            raise ValueError("circuit_failure_threshold must be between 1 and 10")
        if not 1 <= probe_interval <= 100:
            raise ValueError("probe_interval must be between 1 and 100")
        self._max_samples = max_samples_per_profile
        self._failure_threshold = circuit_failure_threshold
        self._probe_interval = probe_interval
        self._samples: dict[RouteHealthKey, list[SemanticRouteSample]] = defaultdict(list)
        self._sequence = 0

    def next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def record(self, sample: SemanticRouteSample) -> None:
        key = (sample.capability, sample.route_version)
        items = self._samples[key]
        items.append(sample)
        if len(items) > self._max_samples:
            del items[: len(items) - self._max_samples]

    def profile(self, capability: str, route: SemanticModelRoute) -> SemanticRouteHealthProfile:
        items = self._samples.get((capability, route.version), [])
        successes = sum(item.succeeded for item in items)
        consecutive_failures = 0
        for item in reversed(items):
            if item.succeeded:
                break
            consecutive_failures += 1
        durations = [item.duration_ms for item in items]
        return SemanticRouteHealthProfile(
            capability=capability,
            route_version=route.version,
            sample_count=len(items),
            successes=successes,
            consecutive_failures=consecutive_failures,
            smoothed_reliability=(successes + 1) / (len(items) + 2),
            median_duration_ms=median(durations) if durations else 0.0,
            last_attempt_sequence=items[-1].sequence if items else 0,
            circuit_open=consecutive_failures >= self._failure_threshold,
        )

    def rank(
        self,
        capability: str,
        routes: tuple[SemanticModelRoute, ...],
        *,
        sequence: int,
    ) -> list[SemanticModelRoute]:
        """Rank routes deterministically and periodically probe open circuits."""
        annotated = [(route, self.profile(capability, route)) for route in routes]

        def probe_due(profile: SemanticRouteHealthProfile) -> bool:
            return bool(
                profile.circuit_open
                and sequence - profile.last_attempt_sequence >= self._probe_interval
            )

        eligible = [
            (route, profile)
            for route, profile in annotated
            if not profile.circuit_open or probe_due(profile)
        ]
        if not eligible:
            eligible = annotated

        def rank_key(
            item: tuple[SemanticModelRoute, SemanticRouteHealthProfile],
        ) -> tuple[float, int, str]:
            route, profile = item
            confidence = profile.sample_count / (profile.sample_count + 5)
            reliability_penalty = confidence * (1.0 - profile.smoothed_reliability) * 5.0
            latency_penalty = min(2.0, profile.median_duration_ms / 60_000.0)
            probe_bonus = -1.0 if probe_due(profile) else 0.0
            return (
                route.priority + reliability_penalty + latency_penalty + probe_bonus,
                profile.last_attempt_sequence,
                route.model_slug,
            )

        return [route for route, _profile in sorted(eligible, key=rank_key)]

    def sample_count(self) -> int:
        return sum(len(items) for items in self._samples.values())


def _combined_usage(responses: list[LLMResponse]) -> LLMTokenUsage:
    usages = [response.usage for response in responses]
    costs = [usage.estimated_cost_usd for usage in usages if usage.estimated_cost_usd is not None]
    return LLMTokenUsage(
        input_tokens=sum(usage.input_tokens for usage in usages),
        output_tokens=sum(usage.output_tokens for usage in usages),
        cached_input_tokens=sum(usage.cached_input_tokens for usage in usages),
        reasoning_tokens=sum(usage.reasoning_tokens for usage in usages),
        estimated_cost_usd=sum(costs) if costs else None,
    )


@dataclass(frozen=True)
class SemanticBrokerResult[RouteOutputT]:
    """One successful routed operation with cross-route resource telemetry."""

    output: RouteOutputT
    usage: LLMTokenUsage
    provider_attempts: int
    route_attempts: tuple[LLMRouteAttemptTelemetry, ...]


class SemanticRouteBrokerError(RuntimeError):
    """Typed safe broker failure with actual non-content resource telemetry."""

    def __init__(
        self,
        summary: str,
        *,
        failure_kind: str,
        terminal_failure_kind: str,
        usage: LLMTokenUsage,
        provider_attempts: int,
        route_attempts: tuple[LLMRouteAttemptTelemetry, ...],
    ) -> None:
        self.safe_summary = summary
        self.failure_kind = failure_kind
        self.terminal_failure_kind = terminal_failure_kind
        self.usage = usage
        self.provider_attempts = max(0, provider_attempts)
        self.route_attempts = route_attempts
        super().__init__(summary)


class SemanticRouteBroker:
    """Shared deterministic route policy for contract-validated semantic work."""

    def __init__(
        self,
        client: LLMClient,
        routes: list[SemanticModelRoute],
        *,
        health_ledger: SemanticRouteHealthLedger | None = None,
    ) -> None:
        if not routes:
            raise ValueError("semantic broker requires at least one configured route")
        unique = list(dict.fromkeys(route.model_slug for route in routes))
        if len(unique) != len(routes):
            raise ValueError("semantic broker routes must be unique")
        if len(routes) > 2:
            raise ValueError("the first semantic broker supports one primary and one fallback")
        self.routes = tuple(routes)
        self.health = health_ledger or SemanticRouteHealthLedger()
        self._route_clients = {
            route.model_slug: AttemptCountingLLMClient(client) for route in self.routes
        }

    def execute(
        self,
        *,
        capability: str,
        total_timeout_seconds: float,
        operation: Callable[[LLMClient, SemanticModelRoute, float], RouteOutputT],
        schema_failure_types: tuple[type[Exception], ...] = (),
    ) -> SemanticBrokerResult[RouteOutputT]:
        """Execute one operation with one shared deadline and typed fallback."""
        if total_timeout_seconds <= 0:
            raise ValueError("total_timeout_seconds must be positive")
        sequence = self.health.next_sequence()
        ranked = self.health.rank(capability, self.routes, sequence=sequence)
        overall_started = perf_counter()
        attempts: list[LLMRouteAttemptTelemetry] = []
        all_responses: list[LLMResponse] = []
        total_provider_attempts = 0
        last_error: Exception | None = None
        deadline_exhausted = False

        for index, route in enumerate(ranked):
            elapsed_seconds = perf_counter() - overall_started
            remaining_seconds = total_timeout_seconds - elapsed_seconds
            if remaining_seconds <= 0:
                deadline_exhausted = True
                break
            routes_remaining = len(ranked) - index
            route_budget = min(route.timeout_seconds, remaining_seconds / routes_remaining)
            route_client = self._route_clients[route.model_slug]
            calls_before = route_client.attempt_count
            responses_before = len(route_client.responses)
            route_started = perf_counter()
            fallback_allowed = True
            try:
                output = operation(route_client, route, route_budget)
            except Exception as exc:
                if isinstance(exc, schema_failure_types):
                    failure_kind = "schema_validation"
                elif isinstance(exc, LLMClientError):
                    failure_kind = exc.code.value
                    if exc.code not in _FALLBACK_CODES:
                        fallback_allowed = False
                else:
                    raise
                last_error = exc
            else:
                provider_attempts = route_client.attempt_count - calls_before
                duration_ms = (perf_counter() - route_started) * 1000
                all_responses.extend(route_client.responses[responses_before:])
                total_provider_attempts += provider_attempts
                telemetry = LLMRouteAttemptTelemetry(
                    route=route.model_slug,
                    succeeded=True,
                    duration_ms=duration_ms,
                    provider_attempts=provider_attempts,
                )
                attempts.append(telemetry)
                self.health.record(
                    SemanticRouteSample(
                        sequence=sequence,
                        capability=capability,
                        route_version=route.version,
                        succeeded=True,
                        duration_ms=duration_ms,
                        provider_attempts=provider_attempts,
                    )
                )
                return SemanticBrokerResult(
                    output=output,
                    usage=_combined_usage(all_responses),
                    provider_attempts=total_provider_attempts,
                    route_attempts=tuple(attempts),
                )

            provider_attempts = route_client.attempt_count - calls_before
            duration_ms = (perf_counter() - route_started) * 1000
            all_responses.extend(route_client.responses[responses_before:])
            total_provider_attempts += provider_attempts
            attempts.append(
                LLMRouteAttemptTelemetry(
                    route=route.model_slug,
                    succeeded=False,
                    duration_ms=duration_ms,
                    provider_attempts=provider_attempts,
                    failure_kind=failure_kind,
                )
            )
            self.health.record(
                SemanticRouteSample(
                    sequence=sequence,
                    capability=capability,
                    route_version=route.version,
                    succeeded=False,
                    failure_kind=failure_kind,
                    duration_ms=duration_ms,
                    provider_attempts=provider_attempts,
                )
            )
            if not fallback_allowed:
                raise SemanticRouteBrokerError(
                    "Semantic route failed and fallback was not permitted.",
                    failure_kind=failure_kind,
                    terminal_failure_kind=failure_kind,
                    usage=_combined_usage(all_responses),
                    provider_attempts=total_provider_attempts,
                    route_attempts=tuple(attempts),
                ) from last_error

        terminal_failure_kind = (
            LLMErrorCode.TIMEOUT.value
            if deadline_exhausted
            else (
                last_error.code.value
                if isinstance(last_error, LLMClientError)
                else LLMErrorCode.MALFORMED_RESPONSE.value
            )
        )
        raise SemanticRouteBrokerError(
            "All configured semantic routes failed safely.",
            failure_kind="semantic_routes_exhausted",
            terminal_failure_kind=terminal_failure_kind,
            usage=_combined_usage(all_responses),
            provider_attempts=total_provider_attempts,
            route_attempts=tuple(attempts),
        ) from last_error


class RoutedProblemUnderstandingProvider:
    """Apply the shared semantic route policy to initial problem representation."""

    def __init__(
        self,
        client: LLMClient,
        routes: list[SemanticModelRoute],
        *,
        health_ledger: SemanticRouteHealthLedger | None = None,
    ) -> None:
        self._broker = SemanticRouteBroker(
            client,
            routes,
            health_ledger=health_ledger,
        )

    @property
    def model_route(self) -> str:
        fingerprint = hashlib.sha256(
            "|".join(route.model_slug for route in self._broker.routes).encode()
        ).hexdigest()[:12]
        return f"semantic-broker-{fingerprint}"

    @property
    def max_provider_attempts(self) -> int:
        return 4 * len(self._broker.routes)

    def generate(
        self,
        state: PolyaState,
        *,
        mode_hint: ProductMode | None,
        domain_hint: str | None,
        total_timeout_seconds: float,
    ) -> ProblemUnderstandingExecution:
        def execute_route(
            route_client: LLMClient,
            route: SemanticModelRoute,
            route_budget: float,
        ) -> ProblemUnderstandingRunResult:
            return generate_problem_understanding(
                route_client,
                state,
                model=route.model_slug,
                mode_hint=mode_hint,
                domain_hint=domain_hint,
                request_options=LLMRequestOptions(
                    max_output_tokens=PROBLEM_UNDERSTANDING_MAX_OUTPUT_TOKENS,
                    json_mode=True,
                    timeout_seconds=min(45.0, route_budget),
                    total_timeout_seconds=route_budget,
                    max_retries=1,
                ),
            )

        try:
            execution = self._broker.execute(
                capability="problem_representation",
                total_timeout_seconds=total_timeout_seconds,
                operation=execute_route,
            )
        except SemanticRouteBrokerError as exc:
            raise ProblemUnderstandingProviderError(
                exc.safe_summary,
                failure_kind=exc.failure_kind,
                usage=exc.usage,
                model_calls=exc.provider_attempts,
                route_attempts=exc.route_attempts,
            ) from exc
        result = execution.output
        routed_result = result.model_copy(
            update={
                "llm_call_count": execution.provider_attempts,
                "usage": execution.usage,
            }
        )
        return ProblemUnderstandingExecution(
            result=routed_result,
            usage=execution.usage,
            model_calls=execution.provider_attempts,
            route_attempts=execution.route_attempts,
        )


class RoutedCognitiveModelGateway(CognitiveModelGateway):
    """Execute one semantic contract across explicit routes under one deadline."""

    def __init__(
        self,
        client: LLMClient,
        routes: list[SemanticModelRoute],
        *,
        health_ledger: SemanticRouteHealthLedger | None = None,
    ) -> None:
        self._broker = SemanticRouteBroker(
            client,
            routes,
            health_ledger=health_ledger,
        )
        super().__init__(client, routes[0].model_slug)
        self._routes = self._broker.routes

    @property
    def model_route(self) -> str:
        fingerprint = hashlib.sha256(
            "|".join(route.model_slug for route in self._routes).encode()
        ).hexdigest()[:12]
        return f"semantic-broker-{fingerprint}"

    def capability_version(self, implementation_version: str) -> str:
        fingerprint = hashlib.sha256(
            (
                BROKER_POLICY_VERSION
                + "|"
                + COGNITIVE_CAPABILITY_PROMPT_VERSION
                + "|"
                + "|".join(route.version for route in self._routes)
            ).encode()
        ).hexdigest()[:12]
        return f"{implementation_version}+broker-{fingerprint}"

    @property
    def max_provider_attempts_per_capability(self) -> int:
        return 4 * len(self._routes)

    def complete(
        self,
        *,
        capability: str,
        instructions: str,
        output_type: type[OutputT],
        state: PolyaState,
        max_output_tokens: int = 1800,
        total_timeout_seconds: float = 90.0,
        context: dict[str, JsonValue] | None = None,
        state_projection: dict[str, JsonValue] | None = None,
    ) -> ModelCapabilityResult[OutputT]:
        def execute_route(
            route_client: LLMClient,
            route: SemanticModelRoute,
            route_budget: float,
        ) -> ModelCapabilityResult[OutputT]:
            return CognitiveModelGateway(route_client, route.model_slug).complete(
                capability=capability,
                instructions=instructions,
                output_type=output_type,
                state=state,
                max_output_tokens=max_output_tokens,
                total_timeout_seconds=route_budget,
                context=context,
                state_projection=state_projection,
            )

        try:
            execution = self._broker.execute(
                capability=capability,
                total_timeout_seconds=total_timeout_seconds,
                operation=execute_route,
                schema_failure_types=(ModelCapabilityParseError,),
            )
        except SemanticRouteBrokerError as exc:
            raise AuditedCapabilityError(
                exc.safe_summary,
                failure_kind=exc.failure_kind,
                payload={
                    "procedure": "semantic_route_broker",
                    "policy_version": BROKER_POLICY_VERSION,
                    "model_calls": exc.provider_attempts,
                    "usage": exc.usage.model_dump(mode="json"),
                    "terminal_failure_kind": exc.terminal_failure_kind,
                    "route_attempts": [item.model_dump(mode="json") for item in exc.route_attempts],
                },
            ) from exc
        result = execution.output
        return ModelCapabilityResult(
            output=result.output,
            provider=result.provider,
            model=result.model,
            usage=execution.usage,
            model_calls=execution.provider_attempts,
            route_attempts=execution.route_attempts,
        )
