# Chapter 175 — Stop explanations and truncation recovery

Status: implemented and verified. Binding decision: master plan, "Chapter 175".

## The failure it fixes

Session `89347a18-…` (exactly-once money movement) framed the problem, found 17
constraints and no blocking gaps, then failed at solution design: two deliberator
responses of exactly 3,200 tokens each (the per-call cap without the sandbox) were cut
off mid-JSON. The structural repair resent the truncated text under the same cap, so
it was cut off too; the broker reported `schema_validation`/`malformed_response`; the
controller would not repeat the failed action and stopped; the report said "None
recorded" everywhere and "Gather the missing evidence". The input had first been a
bare ChatGPT share link, which cost a model call to discover it could not be read.

## Changes

- `model_gateway.py`: `response_truncated()` recognises provider length stops
  (`length`, `max_tokens`, `max_output_tokens`, `model_length`). A truncated invalid
  response triggers one compact full-answer retry with the original user message and
  the same token limit; a second truncation raises `ModelOutputTruncatedError`.
  Non-truncated malformed responses keep the existing edit-based repair.
- `semantic_broker.py`: route and terminal failure kind `output_truncated`.
- `on_demand_capabilities.py`: deliberator per-call output 6,000 in both modes.
- `input_links.py` + `adapters.py`: share-link-only input returns a blocked
  observation with a precise question and zero model calls. Resumed input appends
  the clarification, so it is never mistaken for a bare link.
- `stop_explanation.py`: progress, failure and next action from trace events, used by
  `sessions/service.py` (API report and markdown export), `session_runner.py` (final
  answer) and `investigator/artifacts.py` (CLI report).

## Verification

- `backend/tests/test_stop_and_truncation.py` (20): compact retry under the same
  limit without resending truncated text, repeated truncation labelled, unchanged
  repair path, finish-reason variants, broker terminal label, deliberator allowance,
  share-link detection and the zero-call question, an event-for-event reconstruction
  of the failed session, truncation and provider-refusal explanations, session final
  answer and CLI report.
- The new report code was run read-only against the stored failed session in the
  local development database: it lists the three completed steps (including the 17
  constraints), the failed solution-design step and a specific next action. (That
  session predates truncation detection, so it is labelled as a structure failure.)
- Full backend suite against an isolated, freshly migrated `polyabrain_test` database
  (created for the run and dropped afterwards): 1,305 passed, 0 skipped, 0 failed.
  Ruff, format and strict mypy (166 files) clean; frontend 35 tests pass.

## Limits

- The compact retry depends on providers reporting a length stop; when a provider
  omits it, the existing repair path runs as before.
- A design answer that still exceeds 6,000 tokens after the compact retry stops with
  an explicit truncation reason and the advice to ask in parts; splitting is not yet
  automatic.
- The running Docker backend must be rebuilt to pick up these changes.
