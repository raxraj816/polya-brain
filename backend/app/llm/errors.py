"""Typed, sanitized errors for the provider-neutral LLM boundary."""

from __future__ import annotations

from enum import StrEnum

from app.tracing.sanitization import sanitize_text


class LLMErrorCode(StrEnum):
    """Stable error categories used for retry and engine routing decisions."""

    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_ERROR = "provider_error"


class LLMClientError(RuntimeError):
    """Safe error envelope adapters return instead of leaking provider details."""

    def __init__(
        self,
        code: LLMErrorCode,
        message: str,
        *,
        provider: str,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.safe_message = sanitize_text(message).strip() or "LLM request failed"
        self.provider = sanitize_text(provider).strip() or "unknown"
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(f"{self.code.value}: {self.safe_message}")
