# Chapter 12-B Production OpenRouter Adapter

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 12-B adds the first production provider implementation behind the
Chapter 12-A `LLMClient` boundary. OpenRouter was selected because it is the
provider configured for this repository and requested for this implementation.
The adapter is synchronous and non-streaming to match the current graph and
engine contracts.

## Implemented

- Added a real OpenRouter Chat Completions adapter using the exact configured
  `/api/v1/chat/completions` endpoint.
- Added environment-backed API key, base URL, model, application identity,
  data-collection, ZDR, and JSON-parameter routing settings.
- Kept the API key in `SecretStr` and excluded prompts and raw provider bodies
  from failures and retry logs.
- Added bearer authentication plus OpenRouter application attribution headers.
- Added JSON object response mode, `max_completion_tokens`, request timeout,
  and provider routing controls.
- Defaulted data collection to `deny` and JSON parameter support to required.
- Normalized HTTP failures, embedded provider failures, choice failures,
  timeouts, network failures, malformed JSON, missing choices, and missing text
  into typed Chapter 12-A errors.
- Captured input, output, cached-input, and reasoning token counts plus provider
  cost metadata when returned.
- Honored numeric `Retry-After` guidance within the existing bounded retry cap.
- Normalized string and multipart text content without accepting empty output.

## Provider Policy Finding

The configured free model,
`nvidia/nemotron-3-ultra-550b-a55b:free`, could not satisfy the production
defaults during a genuine live smoke test:

- `data_collection=deny` returned a no-endpoint match for the free model's
  training policy.
- After allowing data collection, strict JSON-parameter routing also returned
  no compatible endpoint.

The adapter therefore correctly fails closed under the production settings.
Only the non-confidential Chapter 13 benchmark was run with process-local
`data_collection=allow` and `require_parameters=false`. Those overrides are an
evaluation compatibility measure, not the production policy.

## Failure Guardrails

- No adapter is created without a nonblank key and base URL.
- Provider data collection accepts only `allow` or `deny`.
- Raw provider messages and response bodies are never surfaced in normalized
  errors.
- Authentication, permission, and invalid-request failures are not retried.
- Rate-limit, timeout, and service-availability failures are retryable only
  through the bounded Chapter 12-A policy.
- A successful HTTP response containing an embedded or choice-level error is
  still treated as failure.
- Missing or malformed model output never becomes an `LLMResponse`.

## Verification

```bash
.venv/bin/python -m pytest backend/tests/test_openrouter_adapter.py
make lint
make test
make proof
docker compose config --quiet
```

The live Chapter 13 run also exercised the adapter end to end against the
configured OpenRouter model. Its inputs, responses, usage, metrics, and policy
limitations are stored under `../../evals/chapter_13/runs/2026-08-09/`.

## Deferred

- A paid or otherwise compatible production model must be selected before
  confidential workload testing under deny/ZDR and strict JSON routing.
- Streaming, async cancellation, Redis-backed rate limiting, provider fallback,
  and additional provider adapters remain later chapter scope.
