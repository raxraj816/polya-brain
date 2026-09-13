"""Chapter 12-A provider-neutral LLM boundary tests."""

import logging

import pytest
from pydantic import ValidationError

from app.llm import (
    FakeLLMClient,
    LLMClientError,
    LLMErrorCode,
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMResponse,
    LLMRole,
    LLMTokenUsage,
    complete_with_retry,
)
from app.tracing.sanitization import REDACTED


def request_with(**option_overrides: object) -> LLMRequest:
    options: dict[str, object] = {
        "temperature": 0.1,
        "max_output_tokens": 512,
        "json_mode": True,
        "timeout_seconds": 12.0,
        "max_retries": 2,
        "initial_retry_delay_seconds": 0.25,
        "max_retry_delay_seconds": 1.0,
    }
    options.update(option_overrides)
    return LLMRequest(
        model="fake-reasoner-v1",
        messages=[
            LLMMessage(role=LLMRole.SYSTEM, content="Return a structured problem."),
            LLMMessage(role=LLMRole.USER, content="Investigate the latency regression."),
        ],
        options=LLMRequestOptions.model_validate(options),
    )


def successful_response() -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="fake-reasoner-v1",
        text='{"core_question":"Why did latency regress?"}',
        usage=LLMTokenUsage(
            input_tokens=21,
            output_tokens=9,
            cached_input_tokens=3,
            reasoning_tokens=2,
            estimated_cost_usd=0.0004,
        ),
        response_id="fake_response_1",
        finish_reason="stop",
        duration_ms=4.5,
    )


def test_llm_contracts_round_trip_and_compute_total_usage() -> None:
    request = request_with()
    response = successful_response()

    assert LLMRequest.model_validate_json(request.model_dump_json()) == request
    assert LLMResponse.model_validate_json(response.model_dump_json()) == response
    assert response.usage.total_tokens == 30


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("temperature", -0.1),
        ("temperature", 2.1),
        ("max_output_tokens", 0),
        ("timeout_seconds", 0),
        ("total_timeout_seconds", 0),
        ("max_retries", 6),
        ("initial_retry_delay_seconds", -0.1),
    ],
)
def test_request_options_reject_invalid_bounds(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        request_with(**{field: value})


def test_request_options_reject_initial_delay_above_cap() -> None:
    with pytest.raises(ValidationError, match="initial retry delay"):
        request_with(initial_retry_delay_seconds=2.0, max_retry_delay_seconds=1.0)


def test_request_requires_messages_and_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(model="fake-reasoner-v1", messages=[])

    with pytest.raises(ValidationError):
        LLMMessage.model_validate({"role": "user", "content": "hello", "secret": "no"})


def test_fake_client_returns_scripted_response_and_records_full_request() -> None:
    response = successful_response()
    client = FakeLLMClient([response])
    request = request_with(timeout_seconds=7.5)

    result = complete_with_retry(client, request)

    assert result == response
    assert client.requests == [request]
    assert client.requests[0].options.timeout_seconds == 7.5


def test_json_mode_fails_closed_when_adapter_does_not_support_it() -> None:
    client = FakeLLMClient([successful_response()], supports_json_mode=False)

    with pytest.raises(LLMClientError) as exc_info:
        complete_with_retry(client, request_with())

    assert exc_info.value.code is LLMErrorCode.UNSUPPORTED_CAPABILITY
    assert exc_info.value.retryable is False
    assert client.requests == []


def test_retryable_failures_use_bounded_exponential_backoff() -> None:
    timeout = LLMClientError(
        LLMErrorCode.TIMEOUT,
        "Provider timed out.",
        provider="fake",
        retryable=True,
    )
    client = FakeLLMClient([timeout, timeout, successful_response()])
    delays: list[float] = []

    response = complete_with_retry(client, request_with(), sleep=delays.append)

    assert response == successful_response()
    assert delays == [0.25, 0.5]
    assert len(client.requests) == 3


def test_total_deadline_clamps_attempt_timeout_and_stops_retry_backoff() -> None:
    now = 0.0

    def clock() -> float:
        return now

    def advance(seconds: float) -> None:
        nonlocal now
        now += seconds

    timeout = LLMClientError(
        LLMErrorCode.TIMEOUT,
        "Provider timed out.",
        provider="fake",
        retryable=True,
    )
    client = FakeLLMClient([timeout, timeout, successful_response()])
    request = request_with(
        timeout_seconds=12.0,
        total_timeout_seconds=0.6,
        max_retries=2,
        initial_retry_delay_seconds=0.25,
        max_retry_delay_seconds=1.0,
    )

    with pytest.raises(LLMClientError) as exc_info:
        complete_with_retry(client, request, sleep=advance, clock=clock)

    assert exc_info.value.code is LLMErrorCode.TIMEOUT
    assert exc_info.value.retryable is False
    assert len(client.requests) == 2
    assert client.requests[0].options.timeout_seconds == pytest.approx(0.6)
    assert client.requests[1].options.timeout_seconds == pytest.approx(0.35)


def test_provider_retry_after_is_honored_within_request_delay_cap() -> None:
    rate_limit = LLMClientError(
        LLMErrorCode.RATE_LIMIT,
        "Rate limited.",
        provider="fake",
        retryable=True,
        status_code=429,
        retry_after_seconds=60,
    )
    client = FakeLLMClient([rate_limit, successful_response()])
    delays: list[float] = []

    response = complete_with_retry(client, request_with(), sleep=delays.append)

    assert response == successful_response()
    assert delays == [1.0]


def test_non_retryable_failure_stops_after_first_attempt() -> None:
    invalid = LLMClientError(
        LLMErrorCode.INVALID_REQUEST,
        "Request schema was rejected.",
        provider="fake",
    )
    client = FakeLLMClient([invalid, successful_response()])
    delays: list[float] = []

    with pytest.raises(LLMClientError) as exc_info:
        complete_with_retry(client, request_with(), sleep=delays.append)

    assert exc_info.value is invalid
    assert delays == []
    assert len(client.requests) == 1


def test_retry_exhaustion_returns_sanitized_error_without_logging_prompt(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "sk-or-v1-abcdefghijklmnopqrstuvwxyz123456"
    rate_limit = LLMClientError(
        LLMErrorCode.RATE_LIMIT,
        f"Provider rejected bearer credential {secret}",
        provider="fake",
        retryable=True,
        status_code=429,
    )
    client = FakeLLMClient([rate_limit, rate_limit])
    request = LLMRequest(
        model="fake-reasoner-v1",
        messages=[LLMMessage(role="user", content="private-user-prompt")],
        options=LLMRequestOptions(max_retries=1, initial_retry_delay_seconds=0),
    )

    with (
        caplog.at_level(logging.WARNING, logger="polyabrain.llm"),
        pytest.raises(LLMClientError) as exc_info,
    ):
        complete_with_retry(client, request, sleep=lambda _: None)

    assert secret not in str(exc_info.value)
    assert REDACTED in str(exc_info.value)
    assert "private-user-prompt" not in caplog.text
    assert secret not in caplog.text


def test_fake_client_fails_clearly_when_script_is_exhausted() -> None:
    client = FakeLLMClient([])

    with pytest.raises(LLMClientError, match="no scripted result remaining") as exc_info:
        complete_with_retry(client, request_with(json_mode=False))

    assert exc_info.value.code is LLMErrorCode.PROVIDER_ERROR
