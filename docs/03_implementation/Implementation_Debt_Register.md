# Implementation Debt Register

This register tracks accepted implementation shortcuts, known gaps, and residual
technical debt introduced while completing chapters.

Source of truth for chapter scope remains
`../../PolyaBrain_Product_Implementation_Master_Plan.md`. Planned future chapter
work is not debt by itself. Record an item here only when the current
implementation knowingly leaves a shortcut, warning, workaround, incomplete
verification path, or risk that should be revisited.

## Deferral And Debt Admission Rules

Do not record normal future chapter scope as debt. A deferred item is acceptable
only when all of these are true:

1. The master plan assigns it to a later chapter or it clearly belongs to a
   later integration layer.
2. The current chapter still satisfies its exit criteria without it.
3. The omission does not weaken product behavior, safety, verification,
   auditability, or user trust for the current chapter.
4. The next owner and target chapter are clear in the chapter backlog or chapter
   notes.

Record an item in this debt register only when at least one of these is true:

1. A shortcut changes behavior or correctness.
2. A known gap can break a future chapter if forgotten.
3. A warning indicates product, security, data, compatibility, or verification
   risk.
4. A workaround exists because the ideal implementation is blocked.
5. A check could not be run and the missing verification matters.

Do not keep tiny non-actionable dependency noise open as implementation debt. If
it is harmless and only affects local test readability, leave it visible and
revisit only if it becomes a failing check, runtime behavior problem, or upgrade
blocker.

## Entry Format

- ID:
- Chapter introduced:
- Type: shortcut | known gap | residual warning | accepted risk
- Description:
- Why accepted now:
- Owner:
- Target chapter:
- Exit criteria:
- Status: open | closed

## Open Items

No open implementation debt remains for completed Phase 0 or Phase 1 chapters.

## Closed Items

### DEBT-0006: Recover Or Expire Stale Running Sessions

- ID: DEBT-0006
- Chapter introduced: Chapter 10
- Type: accepted risk
- Description: Chapter 10 committed sessions from `created` to `running` before
  synchronous graph execution without a stale-running recovery path.
- Resolution: Added `problem_sessions.run_started_at`, a configurable stale-run
  timeout, safe expiration to `failed` with `verification_status=run_expired`,
  and DB-backed tests proving expired runs are not executed again.
- Status: closed

### DEBT-0005: Revisit Per-Session Trace Append Locking Under Concurrency

- ID: DEBT-0005
- Chapter introduced: Chapter 9
- Type: accepted risk
- Description: Trace append uses a row-level lock on the owning
  `problem_sessions` row before assigning sequence numbers.
- Resolution: Kept the per-session serialized writer policy and added
  DB-backed concurrency coverage proving competing appends preserve unique,
  ordered sequence numbers. The row lock remains the accepted Chapter 9/10
  design until a future async/streaming architecture introduces multiple
  intentional writers per session.
- Status: closed

### DEBT-0004: Add Trace Persistence Metrics

- ID: DEBT-0004
- Chapter introduced: Chapter 9
- Type: known gap
- Description: Trace persistence had deterministic storage but no runtime
  counters for append attempts, success/failure, persisted events,
  route-decision events, redactions, or append duration.
- Resolution: Added lightweight in-process trace metrics with focused tests.
  This intentionally stops short of a full observability backend, which belongs
  to a later observability chapter.
- Status: closed

### DEBT-0003: Add Trace Pagination And Filtering

- ID: DEBT-0003
- Chapter introduced: Chapter 9
- Type: known gap
- Description: `GET /api/v1/sessions/{session_id}/events` returned the full
  ordered trace without pagination or filters.
- Resolution: Added bounded trace reads with `after_sequence`, `limit`,
  `engine_name`, `event_type`, and `reasoning_mode` filters plus pagination
  metadata, while preserving no-param read behavior.
- Status: closed

### DEBT-0002: Broaden Trace Secret Redaction Patterns

- ID: DEBT-0002
- Chapter introduced: Chapter 9
- Type: known gap
- Description: Trace redaction covered secret-like keys, bearer tokens, and
  OpenAI-style API keys but not broader connector/tool secret families.
- Resolution: Added redaction coverage and tests for AWS access keys, GitHub
  tokens, Slack tokens and webhooks, JWTs, database and credential-bearing URLs,
  private-key blocks, and nested secret-bearing metadata.
- Status: closed

### DEBT-0001: LangGraph Dependency Deprecation Warning

- ID: DEBT-0001
- Chapter introduced: Chapter 6
- Type: residual warning
- Description: Importing `langgraph.graph.StateGraph` emits a dependency-level
  `LangChainPendingDeprecationWarning` about the future default for
  `allowed_objects`.
- Resolution: Reclassified as non-actionable dependency noise, not product
  implementation debt. It remains visible during tests and should be revisited
  only if it becomes a failing check, runtime behavior problem, or dependency
  upgrade blocker.
- Status: closed

## Non-Debt Deferred Scope

The following Chapter 6 deferrals are intentional chapter boundaries, not debt:

- Engine interface contract, engine result statuses/routes, telemetry wrapper,
  version metadata, and structured logging helpers belong to Chapter 7.
- Graph skeleton and node routing belong to Chapter 8.
- Event persistence belongs to Chapter 9 or the persistence chapter that wires
  trace events into Postgres.
- Solve-session API belongs to Chapter 10.
- Tool definitions, tool calls, approval flows, and risk enforcement belong to
  later tool-safety chapters.
- Frontend rendering belongs to the frontend chapter block.
