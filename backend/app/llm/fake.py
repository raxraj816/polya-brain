"""Deterministic fake LLM client for parser and engine tests."""

from __future__ import annotations

from collections.abc import Iterable

from app.llm.contracts import LLMCapabilities, LLMRequest, LLMResponse
from app.llm.errors import LLMClientError, LLMErrorCode


class FakeLLMClient:
    """Return scripted responses or typed failures in deterministic order."""

    provider = "fake"

    def __init__(
        self,
        scripted_results: Iterable[LLMResponse | LLMClientError],
        *,
        supports_json_mode: bool = True,
    ) -> None:
        self.capabilities = LLMCapabilities(supports_json_mode=supports_json_mode)
        self._scripted_results = list(scripted_results)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Record the request and return the next scripted result."""
        self.requests.append(request)
        if not self._scripted_results:
            raise LLMClientError(
                LLMErrorCode.PROVIDER_ERROR,
                "Fake LLM client has no scripted result remaining.",
                provider=self.provider,
            )

        result = self._scripted_results.pop(0)
        if isinstance(result, LLMClientError):
            raise result
        return result
