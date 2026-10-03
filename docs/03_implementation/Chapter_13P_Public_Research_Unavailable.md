# Chapter 13-P: unavailable public research

Verified locally on 2026-10-02. Controller version: `cognitive-controller-v0.5.10`.

## Problem and behavior

The previous budget-only correction left missing search registration, failed,
inconclusive or blocked search observations, and privacy refusal routing a typed
public evidence gap to `ask_human`. Five before-change kernel tests reproduce
`needs_input` in those circumstances. This treated unavailable public research as
missing user-owned information.

The controller now suppresses that fallback for unresolved
`current_external_fact` targets when no safe autonomous action for the target
remains. Available autonomous routes retain their existing priority and gates;
genuine private-input clarification remains eligible in mixed requests. Untyped
public wording retains its existing behavior: this change does not infer ownership
from text. Search that fails is recorded and is not automatically repeated.

With no available action, the kernel stops with `insufficient_evidence`. Reports
distinguish an observed acquisition-budget rejection from unavailable safe
research. The latter directs users to inspect unavailable capabilities, failures
or privacy restrictions in the trace before another run. It does not claim a
specific provider outage when registration alone is absent. Existing evidence,
questions, usage and failure observations remain; no clarification, successful
reflection or episodic memory is created by the stop.

The master plan was updated before implementation. No canonical field, resource
allowance, privacy gate, source admission rule or model prompt was added/relaxed.
`research_stop_next_action` validates the latest existing decision metadata for
both report adapters. The browser consumes the persisted report unchanged.

## Verification

- Before change: **5 failed, 4 passed** in the new nine-case regression file.
  All five failures demonstrate the incorrect human-input transition.
- After change: **108 focused checks passed, zero skips**, including four
  persisted readbacks (budget, absent search, failed search, privacy restriction).
  These include controller/kernel, scope-review and page-reader regressions.
- Full backend: **1,157 passed, zero skips**, 114.47 seconds, scratch PostgreSQL
  and the existing pinned Docker sandbox; **843 dependency warnings** remain.
- Production Next.js browser: **2 passed**, 1.3 seconds, reading budget-stop and
  failed-search reports through the real API/database. Both retain evidence and
  unresolved questions, show no verified badge or clarification form, export
  the stop guidance and preserve it after reload, with zero browser POST requests.
- Ruff lint/format and strict mypy pass for the four changed runtime modules;
  frontend TypeScript and changed-test formatting pass. The existing production
  build was reused because no frontend runtime source changed in this chapter.

Artifacts under `runs/launch-readiness/` share the prefix
`2026-10-02-research-unavailable-`:

- `before.xml/.log`: preserved failures.
- `focused.xml/.log`: initial 104 passes with one database skip.
- `db.xml/.log`: 108 checks with database enabled and no skips.
- `full.xml/.log`: complete backend result.
- `replay.json`: five fixture outcomes, decisions, observations, usage and reports.
- `sessions.json`: persisted browser fixture IDs.
- `browser/` and `browser.log`: browser verification.
- `backend.log` and `frontend.log`: local server logs.

Reproduce backend checks with provider credentials blank, scratch `DATABASE_URL`,
`POLYABRAIN_RUN_DB_TESTS=1` and `PYTHONPATH=backend:backend/tests`. Browser fixtures
use `backend/tests/fixtures/research_budget_stop.py`: default cause `budget`, or
`POLYABRAIN_RESEARCH_STOP_CAUSE=failed`. Pass their session IDs as
`POLYABRAIN_RESEARCH_STOP_SESSION` and `POLYABRAIN_RESEARCH_UNAVAILABLE_SESSION`
to `frontend/tests/research-budget.spec.ts`. Use a local unauthenticated API and
unset the frontend public origin; this is not a hosted authentication test.

## Limits and next work

All new evidence is developer verification with **zero live or paid provider
calls**. Browser search failure is a deterministic fixture through the actual
kernel, persistence and report code; it does not establish provider behavior.
The fix depends on correct existing gap classification. It does not demonstrate
semantic source support, full DART recovery, held-out success or user preference.

Earlier candidate-generation exits for scope review, page reads and pending
evidence evaluation still require targeted audit, particularly invocation-specific
reservations and continuation after changed evidence. Existing regressions for
those modules passing does not prove every fallback path. Continue that bounded
audit before adding intelligence mechanisms or spending on another broad run.

Changes remain uncommitted on `feature/launch-readiness`. No deployment occurred.
