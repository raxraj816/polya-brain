# Chapter 9 Event Trace System

Status: complete on `feature/chapter-9-event-trace-system`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 9 makes the Chapter 8 in-memory graph trace durable, ordered, sanitized,
and readable through the backend API.

This chapter does not add session creation, solve-session execution, real engine
intelligence, live streaming, frontend trace rendering, or report composition.
Those remain Chapter 10+ work.

## Implemented

- Added deterministic per-session ordering for persisted trace rows with
  `reasoning_events.sequence_number`.
- Added Alembic migration `20260620_0002` to backfill and enforce sequence
  numbers on existing trace rows.
- Added trace preparation helpers that convert `StateEvent` values into durable
  writes.
- Added recursive trace sanitization for secret-like keys and obvious
  secret-bearing strings before logging, persistence, and API response.
- Added derived `graph_router` events with `event_type="route_decision"` after
  terminal engine events that expose `status` and `recommended_route`.
- Added `SQLAlchemyTraceRepository` for appending trace events and reading them
  back in sequence order.
- Kept LangGraph execution storage-agnostic; callers persist `state["events"]`
  through the repository after a run.
- Added `GET /api/v1/sessions/{session_id}/events` for ordered trace retrieval.
- Added app-level SQLAlchemy session factory wiring for API dependencies.
- Added unit and API tests for ordering, redaction, route-decision insertion,
  endpoint output, missing sessions, and engine wrapper redaction.
- Extended database smoke checks to verify the sequence column and seed trace
  ordering.

## Trace Ordering

`created_at` remains useful for display and time auditing, but trace consumers
must order by `sequence_number`.

For each original graph event, Chapter 9 writes:

1. The sanitized original event.
2. A derived `route_decision` event when the original event is an engine
   `completed` or `failed` event with route metadata.

This preserves the graph's observable order while making routing explicit for
the future UI and report composer.

## API

```http
GET /api/v1/sessions/{session_id}/events
```

Returns:

```json
{
  "session_id": "uuid",
  "events": [
    {
      "id": "uuid",
      "sequence_number": 0,
      "engine_name": "problem_representation",
      "event_type": "started",
      "reasoning_mode": "explore",
      "summary": "Started problem_representation.",
      "metadata": {},
      "created_at": "2026-06-20T00:00:00Z"
    }
  ]
}
```

Missing sessions return `404`.

## Commands

```bash
make lint
make test
make proof
```

With Docker/Postgres available:

```bash
make docker-up
make migrate
make db-smoke
make db-test
make docker-down
```

## Deferred To Chapter 10

- `POST /api/v1/sessions`.
- `GET /api/v1/sessions/{id}`.
- `POST /api/v1/sessions/{id}/run`.
- API-owned graph execution and trace persistence after a run.
- OpenAPI examples for the complete session workflow.

## Deferred Beyond Chapter 9

- Live trace streaming.
- Frontend trace rendering.
- Real engine prompts and parsers.
- Tool-call trace integration.
- Model-call cost trace integration.
- Report composition from persisted trace.
