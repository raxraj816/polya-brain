"""Provider-neutral contracts for the Chapter 12-A LLM boundary."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from app.models.contracts import ContractModel, NonEmptyStr

NonNegativeInt = Annotated[int, Field(ge=0)]
BoundedRetryCount = Annotated[int, Field(ge=0, le=5)]
PositiveTokenCount = Annotated[int, Field(gt=0)]
PositiveSeconds = Annotated[float, Field(gt=0.0)]
NonNegativeSeconds = Annotated[float, Field(ge=0.0)]
Temperature = Annotated[float, Field(ge=0.0, le=2.0)]
NonNegativeCost = Annotated[float, Field(ge=0.0)]


class LLMRole(StrEnum):
    """Message roles supported by the first provider-neutral boundary."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(ContractModel):
    """One ordered message sent to a language model."""

    role: LLMRole
    content: NonEmptyStr


class LLMRequestOptions(ContractModel):
    """Per-request generation, timeout, and bounded retry controls."""

    temperature: Temperature = 0.0
    max_output_tokens: PositiveTokenCount = 1024
    json_mode: bool = False
    timeout_seconds: PositiveSeconds = 30.0
    max_retries: BoundedRetryCount = 2
    initial_retry_delay_seconds: NonNegativeSeconds = 0.25
    max_retry_delay_seconds: PositiveSeconds = 4.0

    @model_validator(mode="after")
    def retry_delay_must_fit_cap(self) -> LLMRequestOptions:
        """Reject retry settings whose first delay already exceeds the cap."""
        if self.initial_retry_delay_seconds > self.max_retry_delay_seconds:
            raise ValueError("initial retry delay cannot exceed maximum retry delay")
        return self


class LLMRequest(ContractModel):
    """Provider-neutral completion request consumed by an LLM client."""

    model: NonEmptyStr
    messages: list[LLMMessage] = Field(min_length=1)
    options: LLMRequestOptions = Field(default_factory=LLMRequestOptions)


class LLMCapabilities(ContractModel):
    """Capabilities an adapter must declare before accepting requests."""

    supports_json_mode: bool = False


class LLMTokenUsage(ContractModel):
    """Normalized token and optional provider-reported cost usage."""

    input_tokens: NonNegativeInt = 0
    output_tokens: NonNegativeInt = 0
    cached_input_tokens: NonNegativeInt = 0
    reasoning_tokens: NonNegativeInt = 0
    estimated_cost_usd: NonNegativeCost | None = None

    @property
    def total_tokens(self) -> int:
        """Return billable input and output tokens without storing redundant state."""
        return self.input_tokens + self.output_tokens


class LLMResponse(ContractModel):
    """Normalized successful response returned by every provider adapter."""

    provider: NonEmptyStr
    model: NonEmptyStr
    text: NonEmptyStr
    usage: LLMTokenUsage = Field(default_factory=LLMTokenUsage)
    response_id: NonEmptyStr | None = None
    finish_reason: NonEmptyStr | None = None
    duration_ms: Annotated[float, Field(ge=0.0)] = 0.0
