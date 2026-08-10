"""Offline contract tests for the production OpenRouter adapter."""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings
from app.llm import (
    LLMClientError,
    LLMErrorCode,
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMRole,
    OpenRouterLLMClient,
)


def request(*, json_mode: bool = True) -> LLMRequest:
    return LLMRequest(
        model="test/model",
        messages=[
            LLMMessage(role=LLMRole.SYSTEM, content="Return a concise answer."),
            LLMMessage(role=LLMRole.USER, content="Investigate the failure."),
        ],
        options=LLMRequestOptions(
            temperature=0.1,
            max_output_tokens=321,
            json_mode=json_mode,
            timeout_seconds=4,
            max_retries=0,
        ),
    )


def test_openrouter_adapter_normalizes_response_usage_and_json_policy() -> None:
    captured: dict[str, object] = {}

    def handler(http_request: httpx.Request) -> httpx.Response:
        captured["url"] = str(http_request.url)
        captured["authorization"] = http_request.headers["Authorization"]
        captured["title"] = http_request.headers["X-OpenRouter-Title"]
        captured["referer"] = http_request.headers["HTTP-Referer"]
        captured["payload"] = json.loads(http_request.content)
        return httpx.Response(
            200,
            json={
                "id": "gen_test_123",
                "model": "test/model:provider",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": '{"answer":"ok"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 25,
                    "cost": 0.00125,
                    "prompt_tokens_details": {"cached_tokens": 40},
                    "completion_tokens_details": {"reasoning_tokens": 7},
                },
            },
        )

    client = OpenRouterLLMClient(
        api_key="test-secret-key",
        base_url="https://openrouter.test/api/v1/",
        app_url="https://polyabrain.test",
        app_title="PolyaBrain Test",
        data_collection="deny",
        zdr=True,
        transport=httpx.MockTransport(handler),
    )

    response = client.complete(request())

    assert response.provider == "openrouter"
    assert response.model == "test/model:provider"
    assert response.text == '{"answer":"ok"}'
    assert response.response_id == "gen_test_123"
    assert response.finish_reason == "stop"
    assert response.usage.input_tokens == 100
    assert response.usage.output_tokens == 25
    assert response.usage.cached_input_tokens == 40
    assert response.usage.reasoning_tokens == 7
    assert response.usage.estimated_cost_usd == pytest.approx(0.00125)
    assert response.duration_ms >= 0
    assert captured["authorization"] == "Bearer test-secret-key"
    assert captured["title"] == "PolyaBrain Test"
    assert captured["referer"] == "https://polyabrain.test"
    assert captured["url"] == "https://openrouter.test/api/v1/chat/completions"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["max_completion_tokens"] == 321
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["provider"] == {
        "data_collection": "deny",
        "require_parameters": True,
        "zdr": True,
    }


@pytest.mark.parametrize(
    ("status_code", "error_type", "expected_code", "retryable"),
    [
        (400, "invalid_request", LLMErrorCode.INVALID_REQUEST, False),
        (401, "authentication", LLMErrorCode.AUTHENTICATION, False),
        (402, "payment_required", LLMErrorCode.PERMISSION, False),
        (403, "permission_denied", LLMErrorCode.PERMISSION, False),
        (429, "rate_limit_exceeded", LLMErrorCode.RATE_LIMIT, True),
        (503, "provider_unavailable", LLMErrorCode.UNAVAILABLE, True),
        (504, "timeout", LLMErrorCode.TIMEOUT, True),
    ],
)
def test_openrouter_adapter_maps_typed_provider_errors_without_body_leakage(
    status_code: int,
    error_type: str,
    expected_code: LLMErrorCode,
    retryable: bool,
) -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        del http_request
        return httpx.Response(
            status_code,
            json={
                "error": {
                    "code": status_code,
                    "message": "sensitive upstream detail sk-or-v1-secret-value",
                    "metadata": {"error_type": error_type},
                }
            },
        )

    client = OpenRouterLLMClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMClientError) as exc_info:
        client.complete(request())

    assert exc_info.value.code is expected_code
    assert exc_info.value.retryable is retryable
    assert exc_info.value.status_code == status_code
    assert "sensitive upstream detail" not in str(exc_info.value)
    assert "sk-or-v1-secret-value" not in str(exc_info.value)


def test_openrouter_adapter_maps_error_inside_http_200_response() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        del http_request
        return httpx.Response(
            200,
            json={
                "error": {
                    "code": 429,
                    "message": "provider throttled",
                    "metadata": {"error_type": "rate_limit_exceeded"},
                }
            },
        )

    client = OpenRouterLLMClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMClientError) as exc_info:
        client.complete(request())

    assert exc_info.value.code is LLMErrorCode.RATE_LIMIT
    assert exc_info.value.retryable is True


def test_openrouter_adapter_captures_retry_after_hint() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        del http_request
        return httpx.Response(
            429,
            headers={"Retry-After": "12.5"},
            json={
                "error": {
                    "code": 429,
                    "message": "rate limited",
                    "metadata": {"error_type": "rate_limit_exceeded"},
                }
            },
        )

    client = OpenRouterLLMClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMClientError) as exc_info:
        client.complete(request())

    assert exc_info.value.retry_after_seconds == 12.5


def test_openrouter_adapter_maps_network_timeout() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("upstream timeout", request=http_request)

    client = OpenRouterLLMClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMClientError) as exc_info:
        client.complete(request())

    assert exc_info.value.code is LLMErrorCode.TIMEOUT
    assert exc_info.value.retryable is True
    assert "upstream timeout" not in str(exc_info.value)


def test_openrouter_adapter_requires_key_and_valid_data_policy() -> None:
    with pytest.raises(LLMClientError) as missing_key:
        OpenRouterLLMClient(api_key=" ")
    with pytest.raises(LLMClientError) as invalid_policy:
        OpenRouterLLMClient(api_key="test-key", data_collection="sometimes")

    assert missing_key.value.code is LLMErrorCode.AUTHENTICATION
    assert invalid_policy.value.code is LLMErrorCode.INVALID_REQUEST


def test_openrouter_adapter_loads_environment_backed_settings() -> None:
    settings = Settings(
        OPENROUTER_API_KEY="environment-secret",
        OPENROUTER_BASE_URL="https://router.example/api/v1",
        OPENROUTER_MODEL="configured/model",
        OPENROUTER_APP_URL="https://polyabrain.example",
        OPENROUTER_APP_TITLE="Configured PolyaBrain",
        OPENROUTER_DATA_COLLECTION="allow",
        OPENROUTER_ZDR=True,
        OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=False,
    )

    client = OpenRouterLLMClient.from_settings(settings)

    assert client.provider == "openrouter"
    assert settings.openrouter_model == "configured/model"
    assert settings.openrouter_api_key.get_secret_value() == "environment-secret"
    assert settings.openrouter_require_parameters_for_json is False
