"""Chapter 13 Problem Representation Engine."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, cast

from pydantic import JsonValue

from app.engines.contracts import (
    EngineResult,
    EngineRoute,
    EngineRunOutput,
    EngineStatus,
    EngineVersion,
    TokenUsage,
)
from app.graph.state import PolyaState, StateEvent
from app.graph.version import GRAPH_VERSION
from app.llm import (
    LLMClient,
    LLMRequestOptions,
    LLMRouteAttemptTelemetry,
    LLMTokenUsage,
)
from app.models.contracts import ProductMode, ReasoningMode
from app.problem_understanding import (
    PROBLEM_UNDERSTANDING_PROMPT_VERSION,
    ParserRetryPolicy,
    ProblemUnderstandingProvider,
    ProblemUnderstandingProviderError,
    ProblemUnderstandingRunResult,
    generate_problem_understanding,
)
from app.problem_understanding.fallbacks import deterministic_problem_understanding
from app.problem_understanding.prompt import PROBLEM_UNDERSTANDING_MAX_OUTPUT_TOKENS

PROBLEM_REPRESENTATION_ENGINE_VERSION: Final = "problem_representation@1.4.1"


@dataclass(frozen=True)
class _UnderstandingExecution:
    result: ProblemUnderstandingRunResult
    fallback_used: bool
    usage: LLMTokenUsage
    model_calls: int
    route_attempts: tuple[LLMRouteAttemptTelemetry, ...] = ()


def _route_attempt_event(
    attempts: tuple[LLMRouteAttemptTelemetry, ...],
    *,
    model_calls: int,
    status: str,
    failure_kind: str | None = None,
) -> StateEvent | None:
    if not attempts:
        return None
    return StateEvent(
        engine_name="problem_representation",
        event_type="semantic_routes_attempted",
        reasoning_mode=ReasoningMode.EXECUTE,
        summary=f"Problem representation attempted {len(attempts)} configured route(s).",
        metadata={
            "status": status,
            "model_calls": model_calls,
            "failure_kind": failure_kind,
            "route_attempts": [item.model_dump(mode="json") for item in attempts],
        },
    )


def _selected_and_rejected_framing(result: ProblemUnderstandingRunResult) -> tuple[str, str]:
    output = result.output
    if output.wrong_problem_warning is not None:
        return output.deeper_framing, output.literal_framing
    return output.literal_framing, output.deeper_framing


def _trace_events(
    result: ProblemUnderstandingRunResult,
    *,
    fallback_used: bool,
    model_calls: int,
    route_attempts: tuple[LLMRouteAttemptTelemetry, ...],
) -> list[StateEvent]:
    output = result.output
    selected_framing, rejected_framing = _selected_and_rejected_framing(result)
    events = [
        StateEvent(
            engine_name="problem_representation",
            event_type="framing_selected",
            reasoning_mode=ReasoningMode.REFRAME,
            summary="Selected the framing used for the structured problem.",
            metadata={
                "selected_framing": selected_framing,
                "wrong_problem_warning": output.wrong_problem_warning,
            },
        ),
        StateEvent(
            engine_name="problem_representation",
            event_type="alternate_framing_rejected",
            reasoning_mode=ReasoningMode.REFRAME,
            summary="Retained the alternate framing in the audit trace without promoting it.",
            metadata={
                "rejected_framing": rejected_framing,
                "reason": (
                    output.wrong_problem_warning
                    or "The literal framing is sufficient; the deeper framing remains an inspectable alternative."
                ),
            },
        ),
        StateEvent(
            engine_name="problem_representation",
            event_type="approach_selected",
            reasoning_mode=(
                ReasoningMode.COMPARE
                if output.selected_mode is ProductMode.COMPARE
                else ReasoningMode.EXPLORE
            ),
            summary=f"Selected {output.selected_mode.value} mode for this problem.",
            metadata={
                "selected_mode": output.selected_mode.value,
                "mode_confidence": output.mode_confidence,
                "mode_selection_reason": output.mode_selection_reason,
                "needs_clarification": output.needs_clarification,
                "llm_call_count": model_calls,
            },
        ),
    ]
    if fallback_used:
        events.append(
            StateEvent(
                engine_name="problem_representation",
                event_type="deterministic_fallback_used",
                reasoning_mode=ReasoningMode.EXECUTE,
                summary="Used a narrow deterministic representation fallback.",
                metadata={"fallback_model": result.model, "llm_call_count": 0},
            )
        )
    if result.local_repair_steps or result.llm_repair_attempts:
        events.append(
            StateEvent(
                engine_name="problem_representation",
                event_type="parser_repair_applied",
                reasoning_mode=ReasoningMode.VERIFY,
                summary="Repaired and revalidated the provider response before acceptance.",
                metadata={
                    "local_repair_steps": cast(JsonValue, result.local_repair_steps),
                    "llm_repair_attempts": result.llm_repair_attempts,
                    "llm_call_count": model_calls,
                },
            )
        )
    route_event = _route_attempt_event(
        route_attempts,
        model_calls=model_calls,
        status="succeeded",
    )
    if route_event is not None:
        events.append(route_event)
    return events


class ProblemRepresentationEngine:
    """Convert raw input into one stage-gated canonical structured problem."""

    name = "problem_representation"
    reasoning_mode = ReasoningMode.EXPLORE

    def __init__(
        self,
        *,
        client: LLMClient,
        model: str,
        mode_hint: ProductMode | None = None,
        domain_hint: str | None = None,
        request_options: LLMRequestOptions | None = None,
        parser_retry_policy: ParserRetryPolicy | None = None,
        understanding_provider: ProblemUnderstandingProvider | None = None,
        total_timeout_seconds: float = 90.0,
        fallback: Callable[..., ProblemUnderstandingRunResult | None] = (
            deterministic_problem_understanding
        ),
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise ValueError("problem representation model must not be blank")
        if not 1.0 <= total_timeout_seconds <= 300.0:
            raise ValueError("problem representation timeout must be between 1 and 300")
        self._client = client
        self._model = normalized_model
        self._mode_hint = mode_hint
        self._domain_hint = domain_hint
        resolved_options = request_options or LLMRequestOptions(
            max_output_tokens=PROBLEM_UNDERSTANDING_MAX_OUTPUT_TOKENS,
            json_mode=True,
            timeout_seconds=min(45.0, total_timeout_seconds),
            total_timeout_seconds=total_timeout_seconds,
            max_retries=1,
        )
        self._request_options = resolved_options.model_copy(
            update={
                "timeout_seconds": min(
                    resolved_options.timeout_seconds,
                    total_timeout_seconds,
                ),
                "total_timeout_seconds": total_timeout_seconds,
            }
        )
        self._parser_retry_policy = parser_retry_policy or ParserRetryPolicy()
        self._understanding_provider = understanding_provider
        self._total_timeout_seconds = total_timeout_seconds
        self._fallback = fallback
        if understanding_provider is not None:
            max_provider_attempts = understanding_provider.max_provider_attempts
            route_identity = understanding_provider.model_route
        else:
            request_retries = self._request_options.max_retries
            max_provider_attempts = (request_retries + 1) * (
                self._parser_retry_policy.max_llm_repair_attempts + 1
            )
            route_identity = normalized_model
        if not 1 <= max_provider_attempts <= 10:
            raise ValueError("problem representation must reserve between 1 and 10 model calls")
        self.max_provider_attempts = max_provider_attempts
        route_fingerprint = hashlib.sha256(
            (
                route_identity
                + "|"
                + (mode_hint.value if mode_hint else "infer")
                + "|"
                + (domain_hint or "")
            ).encode()
        ).hexdigest()[:12]
        self.version = EngineVersion(
            engine=f"{PROBLEM_REPRESENTATION_ENGINE_VERSION}+route-{route_fingerprint}",
            prompt=PROBLEM_UNDERSTANDING_PROMPT_VERSION,
            model=route_identity,
            tool=(
                "semantic_route_broker"
                if understanding_provider is not None
                else f"llm_provider:{client.provider}"
            ),
            verifier="problem_understanding_contract@1.0.0",
            graph=GRAPH_VERSION,
        )

    def _understand(self, state: PolyaState) -> _UnderstandingExecution:
        fallback_result = self._fallback(
            state,
            mode_hint=self._mode_hint,
            domain_hint=self._domain_hint,
        )
        if fallback_result is not None:
            return _UnderstandingExecution(
                result=fallback_result,
                fallback_used=True,
                usage=fallback_result.usage,
                model_calls=0,
            )
        if self._understanding_provider is not None:
            routed = self._understanding_provider.generate(
                state,
                mode_hint=self._mode_hint,
                domain_hint=self._domain_hint,
                total_timeout_seconds=self._total_timeout_seconds,
            )
            return _UnderstandingExecution(
                result=routed.result,
                fallback_used=False,
                usage=routed.usage,
                model_calls=routed.model_calls,
                route_attempts=routed.route_attempts,
            )
        result = generate_problem_understanding(
            self._client,
            state,
            model=self._model,
            mode_hint=self._mode_hint,
            domain_hint=self._domain_hint,
            request_options=self._request_options,
            parser_retry_policy=self._parser_retry_policy,
        )
        return _UnderstandingExecution(
            result=result,
            fallback_used=False,
            usage=result.usage,
            model_calls=result.llm_call_count,
        )

    def run(self, state: PolyaState) -> EngineRunOutput:
        try:
            execution = self._understand(state)
        except ProblemUnderstandingProviderError as exc:
            route_event = _route_attempt_event(
                exc.route_attempts,
                model_calls=exc.model_calls,
                status="failed",
                failure_kind=exc.failure_kind,
            )
            events = [route_event] if route_event is not None else []
            exhausted = exc.failure_kind == "semantic_routes_exhausted"
            return EngineRunOutput(
                state_delta={"events": events},
                result=EngineResult(
                    status=(
                        EngineStatus.INSUFFICIENT_EVIDENCE if exhausted else EngineStatus.FAILED
                    ),
                    recommended_route=EngineRoute.FINALIZE_INSUFFICIENT_EVIDENCE,
                    errors=[exc.failure_kind],
                    token_usage=TokenUsage(
                        input_tokens=exc.usage.input_tokens,
                        output_tokens=exc.usage.output_tokens,
                    ),
                    versions=self.version,
                    summary=exc.safe_summary,
                ),
            )
        result = execution.result
        output = result.output
        events = _trace_events(
            result,
            fallback_used=execution.fallback_used,
            model_calls=execution.model_calls,
            route_attempts=execution.route_attempts,
        )
        token_usage = TokenUsage(
            input_tokens=execution.usage.input_tokens,
            output_tokens=execution.usage.output_tokens,
        )
        versions = self.version.model_copy(
            update={
                "model": result.model,
                "tool": f"llm_provider:{result.provider}",
            }
        )

        if output.needs_clarification:
            return EngineRunOutput(
                state_delta={"events": events},
                result=EngineResult(
                    status=EngineStatus.NEEDS_INPUT,
                    confidence=output.mode_confidence,
                    missing_inputs=list(output.clarifying_questions),
                    recommended_route=EngineRoute.CLARIFY,
                    token_usage=token_usage,
                    versions=versions,
                    summary="Problem representation needs user clarification before promotion.",
                ),
            )

        return EngineRunOutput(
            state_delta={
                "structured_problem": result.structured_problem,
                "events": events,
            },
            result=EngineResult(
                status=EngineStatus.OK,
                confidence=output.mode_confidence,
                recommended_route=EngineRoute.CONTINUE,
                token_usage=token_usage,
                versions=versions,
                summary="Created and contract-validated the structured problem.",
            ),
        )
