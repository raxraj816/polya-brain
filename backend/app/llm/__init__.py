"""Chapter 12-A provider-neutral LLM boundary."""

from app.llm.client import LLMClient, complete_with_retry
from app.llm.contracts import (
    LLMCapabilities,
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMResponse,
    LLMRole,
    LLMTokenUsage,
)
from app.llm.errors import LLMClientError, LLMErrorCode
from app.llm.fake import FakeLLMClient

__all__ = [
    "FakeLLMClient",
    "LLMCapabilities",
    "LLMClient",
    "LLMClientError",
    "LLMErrorCode",
    "LLMMessage",
    "LLMRequest",
    "LLMRequestOptions",
    "LLMResponse",
    "LLMRole",
    "LLMTokenUsage",
    "complete_with_retry",
]
