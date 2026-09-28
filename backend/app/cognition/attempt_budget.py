"""Invocation-local provider allowance, shared across retries and model routes."""

from dataclasses import dataclass

from app.llm import LLMClient, LLMClientError, LLMErrorCode, LLMRequest, LLMResponse


@dataclass
class ProviderAttemptBudget:
    max_attempts: int
    output_tokens_per_attempt: int
    attempts: int = 0
    responses: int = 0

    def __post_init__(self) -> None:
        if self.max_attempts < 0 or self.output_tokens_per_attempt < 1:
            raise ValueError("Invalid provider attempt allowance")

    @property
    def unreported_output_token_reservation(self) -> int:
        # An exception does not prove that remote inference consumed no tokens.
        return (self.attempts - self.responses) * self.output_tokens_per_attempt

    def wrap(self, client: LLMClient) -> LLMClient:
        return _BoundedClient(client, self)


class _BoundedClient:
    def __init__(self, delegate: LLMClient, budget: ProviderAttemptBudget) -> None:
        self._delegate = delegate
        self._budget = budget
        self.provider = delegate.provider
        self.capabilities = delegate.capabilities

    def complete(self, request: LLMRequest) -> LLMResponse:
        if self._budget.attempts >= self._budget.max_attempts:
            raise LLMClientError(
                LLMErrorCode.INVALID_REQUEST,
                "The capability exhausted its reserved provider attempts.",
                provider=self.provider,
                retryable=False,
            )
        bounded_request = request.model_copy(
            update={
                "options": request.options.model_copy(
                    update={
                        "max_output_tokens": min(
                            request.options.max_output_tokens,
                            self._budget.output_tokens_per_attempt,
                        ),
                        # Retry orchestration lives above this dispatch boundary.
                        "max_retries": 0,
                    }
                )
            }
        )
        self._budget.attempts += 1
        response = self._delegate.complete(bounded_request)
        self._budget.responses += 1
        return response
