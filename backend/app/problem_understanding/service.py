"""End-to-end fake-testable prompt, call, parse, and repair workflow."""

from __future__ import annotations

import time
from collections.abc import Callable

from app.graph.state import PolyaState
from app.llm import (
    LLMClient,
    LLMClientError,
    LLMErrorCode,
    LLMRequestOptions,
    LLMResponse,
    LLMTokenUsage,
    complete_with_retry,
)
from app.models.contracts import ProductMode
from app.problem_understanding.contracts import (
    ParserRetryPolicy,
    ProblemUnderstandingRunResult,
)
from app.problem_understanding.parser import (
    ProblemUnderstandingParseError,
    parse_problem_understanding,
)
from app.problem_understanding.prompt import (
    PROBLEM_UNDERSTANDING_PROMPT_VERSION,
    build_problem_understanding_repair_request,
    build_problem_understanding_request,
)


def _aggregate_usage(responses: list[LLMResponse]) -> LLMTokenUsage:
    costs = [response.usage.estimated_cost_usd for response in responses]
    present_costs = [cost for cost in costs if cost is not None]
    return LLMTokenUsage(
        input_tokens=sum(response.usage.input_tokens for response in responses),
        output_tokens=sum(response.usage.output_tokens for response in responses),
        cached_input_tokens=sum(response.usage.cached_input_tokens for response in responses),
        reasoning_tokens=sum(response.usage.reasoning_tokens for response in responses),
        estimated_cost_usd=sum(present_costs) if present_costs else None,
    )


def generate_problem_understanding(
    client: LLMClient,
    state: PolyaState,
    *,
    model: str,
    mode_hint: ProductMode | None = None,
    domain_hint: str | None = None,
    request_options: LLMRequestOptions | None = None,
    parser_retry_policy: ParserRetryPolicy | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ProblemUnderstandingRunResult:
    """Run the Chapter 11 boundary and stop safely after bounded repair attempts."""
    retry_policy = parser_retry_policy or ParserRetryPolicy()
    request = build_problem_understanding_request(
        state,
        model=model,
        mode_hint=mode_hint,
        domain_hint=domain_hint,
        options=request_options,
    )
    responses: list[LLMResponse] = []
    response = complete_with_retry(client, request, sleep=sleep)
    responses.append(response)

    for repair_attempt in range(retry_policy.max_llm_repair_attempts + 1):
        try:
            parsed = parse_problem_understanding(response.text)
            if mode_hint is not None and parsed.output.selected_mode is not mode_hint:
                raise ProblemUnderstandingParseError(
                    "selected_mode must preserve the supplied user mode_hint"
                )
            return ProblemUnderstandingRunResult(
                output=parsed.output,
                structured_problem=parsed.output.to_structured_problem(),
                prompt_version=PROBLEM_UNDERSTANDING_PROMPT_VERSION,
                provider=response.provider,
                model=response.model,
                llm_call_count=len(responses),
                llm_repair_attempts=repair_attempt,
                local_repair_steps=parsed.local_repair_steps,
                response_ids=[
                    item.response_id for item in responses if item.response_id is not None
                ],
                usage=_aggregate_usage(responses),
            )
        except ProblemUnderstandingParseError as exc:
            if repair_attempt >= retry_policy.max_llm_repair_attempts:
                raise LLMClientError(
                    LLMErrorCode.MALFORMED_RESPONSE,
                    f"Problem-understanding output remained invalid after "
                    f"{repair_attempt} repair attempts: {exc.safe_message}",
                    provider=client.provider,
                ) from exc
            request = build_problem_understanding_repair_request(
                request,
                invalid_response=response.text,
                parse_error=exc.safe_message,
            )
            response = complete_with_retry(client, request, sleep=sleep)
            responses.append(response)

    raise AssertionError("bounded parser repair loop exited unexpectedly")
