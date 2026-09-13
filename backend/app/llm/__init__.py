"""Chapter 12-A provider-neutral LLM boundary."""

from app.llm.client import AttemptCountingLLMClient, LLMClient, complete_with_retry
from app.llm.contracts import (
    LLMCapabilities,
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMResponse,
    LLMRole,
    LLMRouteAttemptTelemetry,
    LLMTokenUsage,
)
from app.llm.errors import LLMClientError, LLMErrorCode
from app.llm.fake import FakeLLMClient
from app.llm.openrouter import OpenRouterLLMClient

__all__ = [
    "FakeLLMClient",
    "LLMCapabilities",
    "AttemptCountingLLMClient",
    "LLMClient",
    "LLMClientError",
    "LLMErrorCode",
    "LLMMessage",
    "LLMRequest",
    "LLMRequestOptions",
    "LLMResponse",
    "LLMRouteAttemptTelemetry",
    "LLMRole",
    "LLMTokenUsage",
    "OpenRouterLLMClient",
    "complete_with_retry",
]
