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

### DEBT-0002: Broaden Trace Secret Redaction Patterns

- ID: DEBT-0002
- Chapter introduced: Chapter 9
- Type: known gap
- Description: Chapter 9 redacts secret-like keys, bearer tokens, and
  OpenAI-style API keys, but it is not a complete secret scanner. Future tool
  and connector work may introduce additional secret formats such as AWS access
  keys, private keys, GitHub tokens, Slack tokens, JWTs, and database URLs.
- Why accepted now: Chapter 9 satisfies the immediate trace/log safety gate for
  current engine metadata and local proof workflows. Broader secret coverage
  should be added when real external tools/connectors are introduced.
- Owner: backend/platform
- Target chapter: tool registry, connector, or observability hardening chapter
- Exit criteria: Redaction tests cover the secret families used by active
  integrations, and persisted/API/log trace paths share the same sanitizer.
- Status: open

### DEBT-0003: Add Trace Pagination And Filtering

- ID: DEBT-0003
- Chapter introduced: Chapter 9
- Type: known gap
- Description: `GET /api/v1/sessions/{session_id}/events` returns the full
  ordered trace. Large traces will eventually need pagination and filters by
  sequence range, engine name, event type, and reasoning mode.
- Why accepted now: Chapter 9 traces are small and the endpoint exists to prove
  inspectable auditability. Session APIs and larger run workflows begin in
  Chapter 10.
- Owner: backend/API
- Target chapter: Chapter 10 or trace UI/API hardening chapter
- Exit criteria: Trace reads support bounded result size and documented filters
  without breaking deterministic sequence ordering.
- Status: open

### DEBT-0004: Add Trace Persistence Metrics

- ID: DEBT-0004
- Chapter introduced: Chapter 9
- Type: known gap
- Description: Trace persistence currently has tests and deterministic storage
  but no runtime metrics for append latency, write counts, redaction counts,
  route-decision counts, sequence allocation, or persistence failures.
- Why accepted now: Chapter 9 is the durable trace layer; full metrics belong
  with observability and run instrumentation after the API shell starts invoking
  graph runs.
- Owner: observability/backend
- Target chapter: observability or Chapter 10+ run instrumentation
- Exit criteria: Trace persistence emits structured metrics or counters that can
  be used to monitor latency, failures, and trace volume.
- Status: open

### DEBT-0005: Revisit Per-Session Trace Append Locking Under Concurrency

- ID: DEBT-0005
- Chapter introduced: Chapter 9
- Type: accepted risk
- Description: Trace append uses a row-level lock on the owning
  `problem_sessions` row before assigning sequence numbers. This protects
  deterministic ordering but may become a bottleneck if multiple writers append
  to the same session concurrently.
- Why accepted now: Current expected behavior is one graph/run writer per
  session. Deterministic audit ordering is more important than high-concurrency
  trace writes at this stage.
- Owner: backend/platform
- Target chapter: Chapter 10+ run execution or streaming trace chapter
- Exit criteria: If concurrent per-session writers are introduced, validate the
  lock remains acceptable or replace it with retry-on-conflict, advisory locks,
  or a queued/session-serialized trace writer.
- Status: open

## Closed Items

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
