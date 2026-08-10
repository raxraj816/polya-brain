"""Chapter 13 Problem Representation Engine."""

from __future__ import annotations

from collections.abc import Callable
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
from app.llm import LLMClient, LLMRequestOptions
from app.models.contracts import ProductMode, ReasoningMode
from app.problem_understanding import (
    PROBLEM_UNDERSTANDING_PROMPT_VERSION,
    ParserRetryPolicy,
    ProblemUnderstandingRunResult,
    generate_problem_understanding,
)
from app.problem_understanding.fallbacks import deterministic_problem_understanding

PROBLEM_REPRESENTATION_ENGINE_VERSION: Final = "problem_representation@1.0.0"


def _selected_and_rejected_framing(result: ProblemUnderstandingRunResult) -> tuple[str, str]:
    output = result.output
    if output.wrong_problem_warning is not None:
        return output.deeper_framing, output.literal_framing
    return output.literal_framing, output.deeper_framing


def _trace_events(
    result: ProblemUnderstandingRunResult,
    *,
    fallback_used: bool,
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
                    "llm_call_count": result.llm_call_count,
                },
            )
        )
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
        fallback: Callable[..., ProblemUnderstandingRunResult | None] = (
            deterministic_problem_understanding
        ),
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise ValueError("problem representation model must not be blank")
        self._client = client
        self._model = normalized_model
        self._mode_hint = mode_hint
        self._domain_hint = domain_hint
        self._request_options = request_options
        self._parser_retry_policy = parser_retry_policy
        self._fallback = fallback
        self.version = EngineVersion(
            engine=PROBLEM_REPRESENTATION_ENGINE_VERSION,
            prompt=PROBLEM_UNDERSTANDING_PROMPT_VERSION,
            model=normalized_model,
            tool=f"llm_provider:{client.provider}",
            verifier="problem_understanding_contract@1.0.0",
            graph=GRAPH_VERSION,
        )

    def _understand(self, state: PolyaState) -> tuple[ProblemUnderstandingRunResult, bool]:
        fallback_result = self._fallback(
            state,
            mode_hint=self._mode_hint,
            domain_hint=self._domain_hint,
        )
        if fallback_result is not None:
            return fallback_result, True
        return (
            generate_problem_understanding(
                self._client,
                state,
                model=self._model,
                mode_hint=self._mode_hint,
                domain_hint=self._domain_hint,
                request_options=self._request_options,
                parser_retry_policy=self._parser_retry_policy,
            ),
            False,
        )

    def run(self, state: PolyaState) -> EngineRunOutput:
        result, fallback_used = self._understand(state)
        output = result.output
        events = _trace_events(result, fallback_used=fallback_used)
        token_usage = TokenUsage(
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
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
