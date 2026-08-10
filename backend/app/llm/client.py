"""Client protocol and bounded execution policy for Chapter 12-A."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Protocol

from app.llm.contracts import LLMCapabilities, LLMRequest, LLMResponse
from app.llm.errors import LLMClientError, LLMErrorCode

logger = logging.getLogger("polyabrain.llm")


class LLMClient(Protocol):
    """Synchronous provider adapter used by the current synchronous graph."""

    provider: str
    capabilities: LLMCapabilities

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return one normalized completion or raise a typed client error."""
        ...


def _retry_delay(request: LLMRequest, retry_index: int) -> float:
    """Return deterministic exponential backoff capped by request policy."""
    initial = request.options.initial_retry_delay_seconds
    maximum = request.options.max_retry_delay_seconds
    return float(min(initial * (2**retry_index), maximum))


def _resolved_retry_delay(
    request: LLMRequest,
    retry_index: int,
    provider_retry_after_seconds: float | None,
) -> float:
    bounded_backoff = _retry_delay(request, retry_index)
    if provider_retry_after_seconds is None:
        return bounded_backoff
    bounded_provider_delay = min(
        provider_retry_after_seconds,
        request.options.max_retry_delay_seconds,
    )
    return max(bounded_backoff, bounded_provider_delay)


def complete_with_retry(
    client: LLMClient,
    request: LLMRequest,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> LLMResponse:
    """Enforce declared capabilities and bounded retry policy around one client."""
    if request.options.json_mode and not client.capabilities.supports_json_mode:
        raise LLMClientError(
            LLMErrorCode.UNSUPPORTED_CAPABILITY,
            "The selected provider adapter does not support JSON mode.",
            provider=client.provider,
        )

    for attempt in range(request.options.max_retries + 1):
        try:
            return client.complete(request)
        except LLMClientError as exc:
            retries_exhausted = attempt >= request.options.max_retries
            if not exc.retryable or retries_exhausted:
                raise

            delay_seconds = _resolved_retry_delay(
                request,
                attempt,
                exc.retry_after_seconds,
            )
            logger.warning(
                "llm.retry",
                extra={
                    "provider": client.provider,
                    "model": request.model,
                    "attempt": attempt + 1,
                    "error_code": exc.code.value,
                    "retry_delay_seconds": delay_seconds,
                    "provider_retry_after_seconds": exc.retry_after_seconds,
                    "timeout_seconds": request.options.timeout_seconds,
                },
            )
            sleep(delay_seconds)

    raise AssertionError("bounded LLM retry loop exited unexpectedly")
