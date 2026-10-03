# Chapter 13-P: truthful public-research budget stops

The unavailable-provider/private-boundary limitation below is historical.
[The subsequent controller 0.5.10 chapter](Chapter_13P_Public_Research_Unavailable.md)
extends truthful stops to missing, failed and privacy-blocked research, with
separate evidence and guidance. The original results below remain unchanged.

Verified locally on 2026-10-01. This closes the bounded recovery-classification
defect reproduced from the saved DART stop; it does not complete that investigation.

## Behavior

Controller `cognitive-controller-v0.5.9` retains the ordinary capability, failure,
privacy and reservation gates. When a generated autonomous candidate for an
unresolved `current_external_fact` gap cannot fit the remaining resource budget,
the fallback `ask_human` for that same target is removed. Other feasible actions,
including memory or inspection, remain eligible. Genuine user-owned clarification
and mixed requests retain their existing routes. With no eligible action, the
controller emits its existing safe stop and the kernel returns
`insufficient_evidence` without dispatching another capability.

The exact failed reservation and suppressed fallback remain in the decision trace.
CLI and persisted reports read only the latest validated decision to explain the
acquisition budget limit and recommend reviewing retained evidence, narrowing the
investigation, or explicitly authorizing a separately budgeted investigation.
This guidance does not grant that authorization or start a retry. No resource
ceiling, core contract, source admission or verification rule changes.

Execution can still be `completed` in the persisted API while verification is
`not_verified`; the browser displays these separately as “run finished” and
“not verified.” No clarification request or learned successful outcome is created.
Evidence, unresolved gaps, accumulated usage and prior failed checks remain.

## Verification and preserved failures

- **1,107 backend tests passed, zero skips**, in 100.44 seconds, using migrated
  disposable PostgreSQL and the existing pinned Docker sandbox. The 843 existing
  dependency deprecation warnings remain.
- The 18 new focused cases cover zero/consumed external allowances, model-call,
  output-token and normalized-cost reservations, affordable search/inspection/
  memory, unavailable search, private/mixed gaps, untyped gap text, malformed and
  superseded decision metadata, retained failed checks, and fresh persisted
  report readback with no clarification or episodic memory.
- The optional production-browser test reads a real seeded session through the
  API, checks the stop guidance, absence of a clarification form and verified
  badge, retained evidence, Markdown export, reload and zero mutation requests.
  **One browser test passed.** TypeScript, Ruff lint/format and strict mypy pass.
- The previous minimal DART routing probe selected `ask_human` at 3/3 external
  calls. The after-change probe selects `stop`; its 2/3-call control still selects
  `search`. Original artifacts and hashes are preserved. This is a minimal
  routing probe, not a full historical state/provider replay.

Evidence is under `runs/launch-readiness/2026-10-01-research-stop/`: full JUnit/log,
browser output, seeded session ID and after-change routing replay. The earlier
audit remains under `runs/launch-readiness/2026-10-01-dart/`. Initial verification
also preserves a nonexistent test-filename invocation and an invalid test-fixture
reservation-field failure; the unsupported fixture field was removed before the
passing full suite. No failed evaluation was overwritten or counted as success.

Use `POLYABRAIN_RUN_DB_TESTS=1` with a migrated scratch database for backend
integration. The browser fixture is
`backend/tests/fixtures/research_budget_stop.py`, run with
`PYTHONPATH=backend:backend/tests`; pass its printed session ID through
`POLYABRAIN_RESEARCH_STOP_SESSION` to `frontend/tests/research-budget.spec.ts`.
That test explicitly skips when the persisted fixture is absent.

## Limits

All evidence here is developer verification with zero paid or live provider calls.
The original DART source-coverage failure remains unsolved. This policy depends
on the existing typed gap classification and a generated candidate's reservation
denial; it does not infer public ownership from arbitrary prose or cover every
earlier routing exit. Missing providers, privacy restrictions and prior acquisition
failures retain their existing fallback behavior. General deadline reporting,
representative source selection, semantic correctness, practical baseline cost,
and independent-user evidence remain separate gates. No deployment occurred.
