# Chapter 12-A LLM Client Boundary

Status: complete on `feature/chapter-12-llm-client`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 12-A creates the provider-neutral, fake-testable boundary required before
prompt parsing and real engine work. It does not add a production provider
adapter, prompt templates, JSON repair, engine integration, or canonical engine
output persistence.

The pre-platform proof harness also accepts OpenRouter as a direct-model
baseline provider. That small validation integration is separate from the
production adapter planned for Chapter 12-B.

## Implemented

- Added strict provider-neutral contracts for messages, requests, request
  options, adapter capabilities, responses, and normalized token/cost usage.
- Added the synchronous `LLMClient` protocol aligned with the current
  synchronous engine and graph contracts.
- Added a deterministic `FakeLLMClient` that records requests and returns
  scripted responses or typed failures.
- Added explicit JSON-mode capability declaration and fail-closed capability
  validation before an adapter is called.
- Added per-request temperature, output-token, timeout, retry-count, and
  exponential-backoff controls.
- Added bounded retry behavior for typed retryable failures. Invalid requests,
  unsupported capabilities, and other non-retryable failures stop immediately.
- Added typed error categories for invalid requests, authentication,
  permissions, rate limits, timeouts, availability, malformed responses, and
  provider errors.
- Sanitized client errors using the shared trace redaction policy and kept
  prompts and provider messages out of retry logs.
- Added JSON round-trip, malformed-input, fake-client, capability, timeout,
  retry, backoff, exhaustion, redaction, and logging tests.
- Added an offline HTTP contract test for the OpenRouter baseline client.

## Contract Boundary

Future engines should create an `LLMRequest`, then call
`complete_with_retry(client, request)`. Provider adapters must normalize a
successful response into `LLMResponse` and map provider failures into
`LLMClientError`.

The timeout value is part of every request and must be honored by the provider
adapter's network call. The Chapter 12-A wrapper owns bounded retry decisions;
it does not attempt to cancel arbitrary synchronous provider code from another
thread.

## Failure Guardrails

- JSON mode cannot be requested from an adapter that did not declare support.
- Retry count is capped at five per request.
- Retry delays use deterministic exponential backoff with a configured cap.
- Only typed, explicitly retryable failures are retried.
- Error text is sanitized before it can be exposed to callers.
- Retry logs contain provider, model, attempt, error code, timeout, and delay,
  but never prompt content or provider error bodies.
- The fake client fails clearly when its scripted results are exhausted.

## Verification

```bash
make lint
make test
make proof
docker compose config --quiet
```

Focused tests:

```bash
.venv/bin/python -m pytest backend/tests/test_llm_client.py
.venv/bin/python -m pytest backend/tests/test_pre_platform_baseline_clients.py
```

## Deferred

- Chapter 11 owns problem-understanding prompts, schemas, parsing, repair, and
  prompt examples.
- Chapter 12-B owns the first production provider adapter, provider error
  mapping, environment-driven model selection, and live local smoke test.
- Chapter 13 owns the first real engine and validated structured-problem
  persistence.
- Redis caching, streaming, multiple adapters, and model routing remain outside
  this chapter.
