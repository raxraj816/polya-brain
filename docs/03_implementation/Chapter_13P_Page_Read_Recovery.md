# Chapter 13-P: recovery through a different document

Implementation date: 2026-10-02. Controller `cognitive-controller-v0.5.11`;
page reader `public_page_reader@0.2.3`.

## Defect and repair

A failed page read previously disabled the reader for that gap forever. Even a
later evaluated discovery of a different admitted document could not restore the
route: both `page_read_target` and the controller's generic failure history veto
blocked it. This contradicted the intended bounded recovery through fresh research.

The reader now requires a fresh web-search acquisition and its completed unresolved
evaluation after the attempted read. For a known failed read, its observation must
also bind to a recorded URL attempt through the action ID. That binding is optional
trace metadata, not a new core contract. Unknown errors, absent/mismatched attempts
and legacy failed traces without a binding remain blocked.

Only an admitted, untried URL may be selected. Existing source nomination, public
network safeguards, shared budgets, privacy checks and the two-attempt run ceiling
still apply. The controller bypasses its generic failure veto only when the stricter
page-read eligibility function authorizes that distinct read. Other capabilities
retain their existing failure policy. Successful reading stages candidates; it does
not fill the gap or bypass evidence evaluation.

## Evidence

The initial recovery file preserved **3 failed, 8 passed** before implementation.
The failures expose the absent fresh-source route, including the eligibility setup
needed to test budget/privacy refusal independently.

The final focused group passes **118 checks** (page recovery, page reader,
scope review, controller and acquisition), including **14 recovery cases**. Ruff
lint/format, strict mypy for both changed runtime modules and `git diff --check`
pass. Full backend verification: **1,171 passed, zero skips**, 111.97 seconds,
with **843 existing dependency warnings**.

The integration fixture begins with an evaluated but incomplete source and one
recorded prior search allowance. The real reader receives a simulated HTTP 404.
The real controller then executes web search, separate source evaluation, a read
of the newly admitted document and another separate evaluation, followed by a
truthful resource stop. Search, evaluation and HTTP responses are fixtures; the
controller, acquisition adapters, source admission, usage accounting and report
export are actual application code.

The trace retains the failed read. Total accounting is four external calls
(including the seeded prior search) and two fake model evaluations. Exactly two
page requests occur, to distinct URLs. The final report contains the new evidence
but no verified conclusion, filled gap or successful reflection. The user objective
was not solved by this fixture. The export's zero elapsed time is a test input,
not a performance measurement.

Artifacts under `runs/launch-readiness/` share the prefix
`2026-10-02-page-recovery-`:

- `before.xml/.log`: original failures.
- `focused.xml/.log`: first 115 passing checks.
- `pipeline.xml/.log` and `pipeline-temp/`: initial integration export failure;
  the test omitted the export directory required by the existing writer. The
  fixture now creates it; no export behavior was changed to accommodate the test.
- `final.xml/.log` and `final-temp/`: 118 passing checks and exported state, trace,
  evidence and report under `test_actual_search_evaluation_0/recovered-investigation/`.
- `full.xml/.log`: complete backend regression result.
- `verification.json`: test totals and hashes of changed runtime/test files and
  retained evidence artifacts; this is a local reproducibility record, not a signature.

Reproduce with blank provider credentials and `PYTHONPATH=backend:backend/tests`:
run `backend/tests/test_page_read_recovery.py` together with the page-reader,
scope-review, cognitive-controller and knowledge-acquisition test modules. The
focused cases require no database or network. Full backend checks additionally
use migrated scratch PostgreSQL and the pinned Docker sandbox.

## Limits and next work

This is developer recovery evidence with no live provider calls or spending.
It does not establish semantic correctness, source-selection quality, full DART
recovery, baseline advantage or real-user preference. The serialized-state test
checks preservation of eligibility metadata, not process-kill recovery during a
network call. Existing interrupted-call refusal remains authoritative.

Earlier scope-review and pending-evaluation exits, and invocation-specific
reservation handling, remain separate audit work. No frontend runtime behavior
changed, so unchanged passing browser/build checks were not repeated. Work remains
uncommitted on `feature/launch-readiness`; nothing was deployed.
