# Phase 2 Engine Output Persistence

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

This note defines how Phase 2 real engine outputs become durable without
weakening the Phase 1 trace-first architecture.

## Decision

Real engine outputs are persisted only after the producing engine has completed
successfully and its structured output has passed parser and contract validation.

For Phase 2, use a simple batch flush boundary:

1. The engine produces validated structured output.
2. The graph state is updated with that output.
3. Trace events are appended as the audit history.
4. Canonical DB rows for the engine output are written after successful engine
   execution, using the table owned by that engine's contract.

Do not persist failed, partial, low-confidence, or parser-invalid outputs as
canonical rows. Those details may appear in trace metadata, sanitized errors, or
future retry diagnostics, but they must not silently become durable product
facts.

## Chapter Ownership

- Chapter 13 persists the first real `structured_problems` row for a session.
- Chapter 14 continues to store extracted constraints in the structured problem
  contract until a later contract split proves necessary.
- Chapter 21+ persists `knowledge_gaps`.
- Research chapters persist `evidence_items`.
- Reasoning chapters persist `hypotheses` and `plan_tasks`.
- Verification chapters persist `verification_reports`.
- Artifact-producing chapters persist `artifacts`.
- Memory chapters persist `knowledge_chunks` only after ingestion, provenance,
  and retrieval behavior are implemented.

## Current Phase 1 Boundary

Chapter 10 correctly persists only:

- `problem_sessions`
- `reasoning_events`

The Chapter 10 stub graph may carry structured-looking values in `PolyaState`,
but they are not real intelligence outputs and should not be backfilled into
canonical tables.

## Rationale

This keeps the MVP auditable while avoiding premature persistence complexity.
Trace events remain the append-only history of what happened. Canonical tables
hold only validated product state that later engines, APIs, reports, or evals can
trust.

Per-step or streaming persistence is intentionally deferred until async runs,
partial recovery, or retry orchestration require it.

## Guardrails

- A DB row must have a clear producer and consumer.
- A persisted output must be contract-validated before commit.
- Each persistence adapter should be covered by tests using the fake LLM client
  or deterministic fixtures.
- The trace should explain why an output was accepted, rejected, or routed to
  clarification.
- If an engine needs user input, better evidence, or repair, it should return a
  typed route/status instead of writing weak canonical state.
