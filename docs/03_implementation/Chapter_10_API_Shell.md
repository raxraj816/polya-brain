# Chapter 10 API Shell

Status: complete on `feature/chapter-10-api-shell`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 10 exposes the first durable session workflow through the backend API.
It lets a client create a problem session, run that session synchronously through
the deterministic Chapter 10 stub graph, read the updated session summary, and
fetch the persisted ordered trace.

This chapter does not add real LLM calls, prompt parsing, live streaming,
frontend rendering, Redis-backed run state, tool execution, or persistence of
rich reasoning artifacts from stub engines.

## Implemented

- Added public API models for session creation, session summary, and run
  response.
- Added `POST /api/v1/sessions` to create durable `problem_sessions` rows.
- Added `GET /api/v1/sessions/{session_id}` to read session summaries.
- Added `POST /api/v1/sessions/{session_id}/run` to run created sessions
  synchronously through the Chapter 10 stub graph.
- Kept `GET /api/v1/sessions/{session_id}/events` as the trace read endpoint
  introduced in Chapter 9.
- Added deterministic application-level stub engines for all nine logical graph
  stages.
- Persisted run results to the session row and persisted ordered trace events
  through `SQLAlchemyTraceRepository`.
- Added an atomic `created` to `running` claim before graph execution so a
  session can only be run once.
- Protected completed or non-created sessions from duplicate runs with `409`.
- Marked failed runs as `failed` and returned sanitized API errors.
- Added API tests for create, read, run, validation, not-found, conflict, and
  trace-read behavior.
- Added database-backed service tests for session persistence, trace
  persistence, failed-run marking, duplicate-run rejection, and competing-run
  protection.
- Added a stub graph smoke test proving all nine engine stages complete.
- Added the Phase 1 debt closure hardening after initial Chapter 10 completion:
  bounded trace pagination/filtering, broader trace secret redaction, lightweight
  trace metrics, concurrent append validation, and stale-running session
  expiration.

## API

```http
POST /api/v1/sessions
```

Creates a session:

```json
{
  "raw_input": "Our API p95 latency jumped after deploy. Should we add Redis or inspect queries first?",
  "mode": "investigate",
  "domain": "software_debugging"
}
```

```http
GET /api/v1/sessions/{session_id}
```

Returns the stored session summary.

```http
POST /api/v1/sessions/{session_id}/run
```

Runs a `created` session through the Chapter 10 deterministic stub graph and
returns the updated session plus `event_count`.

```http
GET /api/v1/sessions/{session_id}/events
```

Returns persisted ordered trace events.

Optional query parameters:

- `after_sequence`: return events after a sequence number.
- `limit`: bounded page size, default `100`, maximum `500`.
- `engine_name`: filter by engine name.
- `event_type`: filter by event type.
- `reasoning_mode`: filter by reasoning mode.

## Behavior Notes

- `/run` is synchronous for Chapter 10. Queueing, streaming, and Redis run state
  remain later platform work.
- `running` is a durable observable state. The service commits `running` before
  graph execution so competing `/run` requests return `409`.
- `running` sessions record `run_started_at`. Stale runs older than the
  configured timeout are safely expired to `failed` with
  `verification_status=run_expired` and are not executed again.
- A session can be run once. Re-running a completed or otherwise non-created
  session returns `409`.
- Trace reads are bounded and filterable while preserving deterministic sequence
  ordering.
- Trace persistence exposes lightweight in-process metrics for append attempts,
  successful appends, failures, event counts, route-decision counts, redaction
  counts, and append duration.
- Chapter 10 stores only `problem_sessions` outcome fields and reasoning trace
  rows. Stub-produced structured problems, gaps, evidence, hypotheses, plan
  tasks, verification reports, and reflections are not written to their durable
  tables because they are not real engine outputs yet.
- The stub final answer explicitly states that the run is a platform wiring
  proof, not a real investigation result.

## Commands

```bash
make lint
make test
make proof
docker compose config --quiet
```

With Docker/Postgres available:

```bash
make docker-up
make migrate
make db-smoke
make db-test
make docker-down
```

## Deferred To Chapter 11+

- Problem-understanding prompt and parser.
- Output JSON schema and examples.
- Provider-neutral LLM client.
- Real problem representation engine.
- Persistence of meaningful structured engine artifacts.
- Live run streaming and frontend trace rendering.
