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

None.

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
