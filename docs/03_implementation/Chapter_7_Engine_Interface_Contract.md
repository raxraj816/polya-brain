# Chapter 7 Engine Interface Contract

Status: complete on active implementation branch.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 7 defines the shared contract every future PolyaBrain engine must use.
It gives each engine a typed result envelope, route recommendation, version
metadata, telemetry wrapper, structured logging, and trace events so weak output
cannot silently move to the next stage.

This chapter does not add real engine implementations, graph node routing, API
endpoints, database migrations, persistence adapters, tool approval flows, or
frontend screens.

## Implemented

- Added `backend/app/engines/contracts.py`.
- Added `EngineStatus` values: `ok`, `needs_input`, `needs_evidence`,
  `low_confidence`, `blocked`, `failed`, and `insufficient_evidence`.
- Added `EngineRoute` values: `continue`, `clarify`, `research`, `reframe`,
  `replan`, `retry_execution`, `finalize`, and
  `finalize_insufficient_evidence`.
- Added `TokenUsage` with non-negative input and output token counts.
- Added `EngineVersion` for engine, prompt, model, tool, verifier, and graph
  version metadata.
- Added `EngineResult` with status, confidence, missing inputs, recommended
  route, duration, errors, token usage, versions, and summary.
- Added `EngineRunOutput` for state deltas plus the auditable engine result.
- Added state-delta key validation so engine outputs can only update known
  `PolyaState` fields.
- Added `PolyaEngine` protocol with `name`, `reasoning_mode`, `version`, and
  synchronous `run(state)` interface.
- Added `run_engine` telemetry wrapper with start/completion/failure logging,
  duration capture, exception-to-failed-result conversion, and state event
  emission.
- Added `engine_event_metadata` for JSON-compatible trace metadata.
- Re-exported engine primitives from `backend/app/engines`.
- Added Chapter 7 tests in `backend/tests/test_engine_contracts.py`.

## Contract Decisions

- Engine outputs use `EngineRunOutput` rather than returning a raw state object
  directly. The output still preserves the Chapter 7 intent of `run(state)` by
  carrying a state delta that Chapter 8 can merge through LangGraph.
- Engine result duration is wrapper-owned. Engines may construct a result with a
  default duration, but `run_engine` replaces it with measured elapsed time.
- `StateEvent.metadata` carries Chapter 7 telemetry rather than promoting more
  fields into `PolyaState`.
- Malformed engine identity or version metadata fails closed with a fallback
  `unknown_engine@unknown` version instead of escaping the wrapper.
- Chapter 7 stays synchronous because the current backend, tests, and master
  plan are sync-first. Async execution can be added later only when graph/tool
  chapters need it.

## Stage-Gate Guards

- `ok` requires confidence and must route `continue`.
- `needs_input` requires missing inputs and must route `clarify`.
- `needs_evidence` must route `research`.
- `low_confidence` cannot route `continue`.
- `blocked` cannot route `continue`.
- `failed` requires error detail and cannot route `continue`.
- `insufficient_evidence` must route `finalize_insufficient_evidence`.

## Commands

```bash
make lint
make test
make proof
```

Chapter 7 does not require Docker/Postgres verification because it does not
change persistence.

## Verification Completed

- JSON round-trip tests for token usage, version metadata, engine results, and
  engine run outputs.
- Malformed data rejection tests for invalid enums, negative token counts, blank
  engine identifiers, and invalid route/status combinations.
- Stage-gate tests proving low-confidence, blocked, failed, incomplete,
  needs-input, needs-evidence, and insufficient-evidence results cannot silently
  continue.
- Wrapper tests proving duration capture, version propagation, start/completion
  events, engine-provided event preservation, no input-state mutation, and
  exception conversion to failed results.
- Regression tests proving unknown state-delta keys are rejected and malformed
  engine identity/version metadata returns an auditable failed result.

## Deferred To Chapter 8

- LangGraph skeleton.
- Graph nodes for the nine logical engines.
- Routing decisions that consume `EngineStatus` and `EngineRoute`.
- Iteration-limit handling at the graph level.
- Smoke tests proving blocked or weak stages stop safely in the graph.

## Deferred Beyond Chapter 7

- Event persistence in Postgres.
- Solve-session API.
- LLM client abstraction and model-call cost records.
- Tool definitions, tool calls, approval flows, and risk enforcement.
- Frontend rendering of engine status, routing, confidence, and trace events.
