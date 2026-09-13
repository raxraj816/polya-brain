"""Production OpenRouter adapter for the provider-neutral LLM boundary."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.llm.contracts import (
    LLMCapabilities,
    LLMRequest,
    LLMResponse,
    LLMTokenUsage,
)
from app.llm.errors import LLMClientError, LLMErrorCode

OPENROUTER_PROVIDER = "openrouter"


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _non_negative_cost(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        return None
    return float(value)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _provider_error_type(payload: Mapping[str, Any]) -> str | None:
    error = _mapping(payload.get("error"))
    metadata = _mapping(error.get("metadata"))
    value = metadata.get("error_type")
    return value if isinstance(value, str) and value.strip() else None


def _status_code_from_payload(payload: Mapping[str, Any], fallback: int) -> int:
    error = _mapping(payload.get("error"))
    code = error.get("code")
    return code if isinstance(code, int) and not isinstance(code, bool) else fallback


def _error_category(status_code: int, error_type: str | None) -> tuple[LLMErrorCode, bool]:
    if error_type == "authentication" or status_code == 401:
        return LLMErrorCode.AUTHENTICATION, False
    if error_type in {"permission_denied", "payment_required"} or status_code in {402, 403}:
        return LLMErrorCode.PERMISSION, False
    if error_type == "rate_limit_exceeded" or status_code == 429:
        return LLMErrorCode.RATE_LIMIT, True
    if error_type == "timeout" or status_code in {408, 504}:
        return LLMErrorCode.TIMEOUT, True
    if error_type in {"provider_overloaded", "provider_unavailable", "server", "unmapped"}:
        return LLMErrorCode.UNAVAILABLE, True
    if status_code in {500, 502, 503}:
        return LLMErrorCode.UNAVAILABLE, True
    if 400 <= status_code < 500:
        return LLMErrorCode.INVALID_REQUEST, False
    return LLMErrorCode.PROVIDER_ERROR, status_code >= 500


def _typed_provider_error(
    payload: Mapping[str, Any],
    *,
    status_code: int,
    retry_after_seconds: float | None = None,
) -> LLMClientError:
    resolved_status = _status_code_from_payload(payload, status_code)
    error_type = _provider_error_type(payload)
    code, retryable = _error_category(resolved_status, error_type)
    detail = error_type or f"http_{resolved_status}"
    return LLMClientError(
        code,
        f"OpenRouter request failed ({detail}).",
        provider=OPENROUTER_PROVIDER,
        retryable=retryable,
        status_code=resolved_status,
        retry_after_seconds=retry_after_seconds,
    )


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw_value = response.headers.get("Retry-After")
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except ValueError:
        return None
    return value if value >= 0 else None


def _decode_payload(response: httpx.Response) -> Mapping[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise LLMClientError(
            LLMErrorCode.MALFORMED_RESPONSE,
            "OpenRouter returned a non-JSON response.",
            provider=OPENROUTER_PROVIDER,
            status_code=response.status_code,
        ) from exc
    if not isinstance(payload, Mapping):
        raise LLMClientError(
            LLMErrorCode.MALFORMED_RESPONSE,
            "OpenRouter returned a non-object response.",
            provider=OPENROUTER_PROVIDER,
            status_code=response.status_code,
        )
    return payload


def _message_text(message: Mapping[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if not isinstance(item, Mapping):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
        if chunks:
            return "\n".join(chunks)
    raise LLMClientError(
        LLMErrorCode.UNAVAILABLE,
        "OpenRouter returned no text content.",
        provider=OPENROUTER_PROVIDER,
        retryable=True,
    )


def _usage(payload: Mapping[str, Any]) -> LLMTokenUsage:
    usage = _mapping(payload.get("usage"))
    prompt_details = _mapping(usage.get("prompt_tokens_details"))
    completion_details = _mapping(usage.get("completion_tokens_details"))
    return LLMTokenUsage(
        input_tokens=_non_negative_int(usage.get("prompt_tokens")),
        output_tokens=_non_negative_int(usage.get("completion_tokens")),
        cached_input_tokens=_non_negative_int(prompt_details.get("cached_tokens")),
        reasoning_tokens=_non_negative_int(completion_details.get("reasoning_tokens")),
        estimated_cost_usd=_non_negative_cost(usage.get("cost")),
    )


class OpenRouterLLMClient:
    """Synchronous, non-streaming OpenRouter Chat Completions adapter."""

    provider = OPENROUTER_PROVIDER
    capabilities = LLMCapabilities(supports_json_mode=True)

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        app_url: str | None = None,
        app_title: str = "PolyaBrain",
        data_collection: str = "deny",
        zdr: bool = False,
        require_parameters_for_json: bool = True,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        normalized_key = api_key.strip()
        if not normalized_key:
            raise LLMClientError(
                LLMErrorCode.AUTHENTICATION,
                "OPENROUTER_API_KEY is not configured.",
                provider=self.provider,
            )
        normalized_base_url = base_url.strip().rstrip("/")
        if not normalized_base_url:
            raise LLMClientError(
                LLMErrorCode.INVALID_REQUEST,
                "OPENROUTER_BASE_URL is not configured.",
                provider=self.provider,
            )
        if data_collection not in {"allow", "deny"}:
            raise LLMClientError(
                LLMErrorCode.INVALID_REQUEST,
                "OpenRouter data collection must be allow or deny.",
                provider=self.provider,
            )
        self._api_key = normalized_key
        self._base_url = normalized_base_url
        self._chat_completions_url = f"{normalized_base_url}/chat/completions"
        self._app_url = app_url.strip() if app_url and app_url.strip() else None
        self._app_title = app_title.strip() or "PolyaBrain"
        self._data_collection = data_collection
        self._zdr = zdr
        self._require_parameters_for_json = require_parameters_for_json
        self._transport = transport

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> OpenRouterLLMClient:
        """Create an adapter from environment-backed backend settings."""
        resolved = settings or get_settings()
        return cls(
            api_key=resolved.openrouter_api_key.get_secret_value(),
            base_url=resolved.openrouter_base_url,
            app_url=resolved.openrouter_app_url,
            app_title=resolved.openrouter_app_title,
            data_collection=resolved.openrouter_data_collection,
            zdr=resolved.openrouter_zdr,
            require_parameters_for_json=resolved.openrouter_require_parameters_for_json,
            transport=transport,
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": self._app_title,
        }
        if self._app_url is not None:
            headers["HTTP-Referer"] = self._app_url
        return headers

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        provider: dict[str, Any] = {
            "data_collection": self._data_collection,
        }
        if request.options.json_mode:
            provider["require_parameters"] = self._require_parameters_for_json
        if self._zdr:
            provider["zdr"] = True
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [message.model_dump(mode="json") for message in request.messages],
            "temperature": request.options.temperature,
            # OpenRouter's provider eligibility metadata currently standardizes
            # this portable field as ``max_tokens``. Using the newer alias can
            # eliminate otherwise compatible routes when require_parameters is on.
            "max_tokens": request.options.max_output_tokens,
            "stream": False,
            "provider": provider,
        }
        if request.options.json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Send one request and normalize the successful OpenRouter response."""
        started_at = perf_counter()
        try:
            with httpx.Client(
                timeout=request.options.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(
                    self._chat_completions_url,
                    headers=self._headers(),
                    json=self._payload(request),
                )
        except httpx.TimeoutException as exc:
            raise LLMClientError(
                LLMErrorCode.TIMEOUT,
                "OpenRouter request timed out.",
                provider=self.provider,
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise LLMClientError(
                LLMErrorCode.UNAVAILABLE,
                "OpenRouter could not be reached.",
                provider=self.provider,
                retryable=True,
            ) from exc

        payload = _decode_payload(response)
        if response.status_code >= 400 or isinstance(payload.get("error"), Mapping):
            raise _typed_provider_error(
                payload,
                status_code=response.status_code,
                retry_after_seconds=_retry_after_seconds(response),
            )

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            raise LLMClientError(
                LLMErrorCode.MALFORMED_RESPONSE,
                "OpenRouter response did not include a valid completion choice.",
                provider=self.provider,
                status_code=response.status_code,
            )
        choice = choices[0]
        choice_error = choice.get("error")
        if isinstance(choice_error, Mapping) or choice.get("finish_reason") == "error":
            raise _typed_provider_error(
                {"error": choice_error if isinstance(choice_error, Mapping) else {}},
                status_code=502,
            )
        message = choice.get("message")
        if not isinstance(message, Mapping):
            raise LLMClientError(
                LLMErrorCode.MALFORMED_RESPONSE,
                "OpenRouter response did not include an assistant message.",
                provider=self.provider,
                status_code=response.status_code,
            )

        model = payload.get("model")
        response_id = payload.get("id")
        finish_reason = choice.get("finish_reason")
        return LLMResponse(
            provider=self.provider,
            model=model if isinstance(model, str) and model.strip() else request.model,
            text=_message_text(message),
            usage=_usage(payload),
            response_id=(
                response_id if isinstance(response_id, str) and response_id.strip() else None
            ),
            finish_reason=(
                finish_reason if isinstance(finish_reason, str) and finish_reason.strip() else None
            ),
            duration_ms=(perf_counter() - started_at) * 1000,
        )
