# Chapter 6 LangGraph State Object

Status: complete on active implementation branch.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 6 defines the first LangGraph-compatible state object for the MVP
Polya loop. It turns raw problem input into a complete initial state and gives
future graph nodes a typed place to accumulate representation, gaps, evidence,
hypotheses, plans, execution outputs, verification, reflection, final answer,
and trace events.

This chapter does not add engine result contracts, graph nodes, API endpoints,
database migrations, persistence adapters, tool approval flows, or frontend
screens.

## Implemented

- Added `backend/app/graph/state.py`.
- Added `PolyaState` as a `TypedDict` compatible with LangGraph state schemas.
- Added `StateEvent` for append-only graph event messages.
- Added `ExecutionOutput` for task execution results before persistence exists.
- Added JSON-compatible event metadata and execution output payloads.
- Added `append_state_events` as the event reducer for the `events` state field,
  including runtime validation/coercion of graph event updates.
- Added `create_initial_state` to validate raw input and produce a complete
  initial state with fresh mutable collections.
- Added a default iteration budget of `3`.
- Re-exported the graph state primitives from `backend/app/graph`.
- Added Chapter 6 tests in `backend/tests/test_polya_state.py`.

## State Decisions

- `PolyaState` is graph-owned working memory, not a database model and not an API
  response contract.
- Existing Chapter 5 Pydantic contracts remain the core artifact types inside
  graph state.
- `raw_input` is stored directly in state because the Chapter 6 done condition
  requires raw input to become a valid initial state.
- Event messages are Pydantic models so malformed trace artifacts fail before
  later graph chapters expose them.
- Execution outputs keep large or non-JSON artifacts out of graph state by using
  JSON-compatible payloads plus artifact references.
- Engine status, routing values, telemetry wrappers, and version metadata remain
  deferred to Chapter 7.

## Commands

```bash
make lint
make test
make proof
```

Chapter 6 does not require Docker/Postgres verification because it does not
change persistence.

## Verification Completed

- Raw input becomes a complete valid initial state.
- Blank raw input, blank session id, and invalid iteration budgets fail clearly.
- Caller-provided session id and iteration budget are preserved.
- Mutable state collections are isolated between initial states.
- Event reducer appends in order without mutating existing lists.
- Event reducer handles no-op, single-event, dict-shaped, and list updates.
- Event reducer rejects malformed event updates.
- `StateEvent` and `ExecutionOutput` reject malformed or non-JSON data.
- `StateGraph(PolyaState)` accepts the state schema.
- A compiled LangGraph smoke graph accumulates reducer events in order.

## Deferred To Chapter 7

- Engine interface contract.
- Engine result status and route values.
- Telemetry wrapper.
- Version metadata for engine, prompt, model, tool, verifier, and graph versions.
- Structured logging helpers.

## Deferred Beyond Chapter 6

- Graph skeleton and node routing.
- Event persistence in Postgres.
- Solve-session API.
- Tool definitions, tool calls, approval flows, and risk enforcement.
- Frontend rendering of state, trace, evidence, hypotheses, and reports.
