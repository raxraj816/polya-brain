# Chapter 13 Problem Representation Engine

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 13 turns the tested problem-understanding prompt, parser, and provider
boundaries into the first real engine. It produces a validated canonical
`StructuredProblem`, or stops at clarification without allowing weak output to
flow downstream.

## Implemented

- Added `ProblemRepresentationEngine` on the existing `EngineRunOutput` and
  `PolyaState` boundaries.
- Added version metadata for the engine, prompt, model, provider, verifier, and
  graph.
- Added trace events for selected framing, rejected alternate framing, selected
  approach mode, deterministic fallback, and parser repair.
- Kept mode rationale, confidence, alternate framing, and wrong-problem warning
  in the audit trace rather than promoting experimental intelligence into the
  core contract.
- Selected the deeper framing only when the parser emits a wrong-problem
  warning; otherwise retained the literal framing and made the alternative
  inspectable.
- Added narrow deterministic no-model fallbacks for the exact ten Chapter 11
  examples, simple arithmetic, and a fixed set of explicitly underspecified
  requests.
- Returned `needs_input` with a `clarify` route for ambiguous inputs and omitted
  `structured_problem` from the state delta.
- Added a SQLAlchemy persistence boundary that revalidates the canonical model,
  writes only successful representations to `structured_problems`, and persists
  trace events for both successful and clarification paths.
- Left transaction commit and rollback ownership with the caller so canonical
  state and trace can be handled as one unit of work.

## Stage Gate

```text
raw input
  -> narrow deterministic fallback or prompt/client/parser
  -> contract-valid representation
  -> clarification required? -- yes --> trace only; stop safely
                            `-- no  --> state + canonical row + trace
```

Canonical persistence is refused when the engine status is not `ok`, when the
state delta has no structured problem, when contract revalidation fails, or
when the owning session does not exist.

## Live Technical Investigations

Three genuine, reproducible cases were run with the production adapter and the
same configured direct model:

1. Pagination cursor overlap using executable code and a genuine failing pytest
   log.
2. An N+1 SQLite query path using executable measurement code, query counts,
   timings, CSV output, and summary metrics.
3. OpenRouter free-model privacy routing using the repository configuration,
   official provider notes, and a genuine live policy probe.

The Polya path used the Chapter 13 representation engine followed by an
evaluation-only auditable report prompt. The direct path received the same
prepared artifacts in one normal model call. This is not yet a comparison of a
complete nine-engine PolyaBrain loop.

| Metric | Polya path | Direct model | Result |
| --- | ---: | ---: | --- |
| Correctness | 1.000 | 1.000 | Tie across all three cases |
| Evidence quality | 1.000 | 0.100 | Polya reports cited artifacts and audit sections |
| Mean time to decision | 103.2 s | 37.3 s | Mean per-case latency ratio was 3.402x |
| Mean token ratio | 4.685x direct | baseline | Material Polya overhead |
| Would-use-again proxy | 3/3 | 3/3 | No differentiating result |

The reuse result is a deterministic proxy combining correctness, evidence,
actionability, and latency. It is not user research; no human reuse feedback
was collected. The configured free model reported zero cost, so token and
latency overhead are more informative than the cost field for this run.

The honest product conclusion is that Chapter 13 improved provenance,
uncertainty visibility, and report auditability, but did not improve correctness
on these three cases and imposed large latency and token overhead.

Run artifacts and the aggregate machine-readable summary are under
`../../evals/chapter_13/runs/2026-08-09/`.

## Verification

```bash
.venv/bin/python -m pytest backend/tests/test_problem_representation_engine.py
POLYABRAIN_RUN_DB_TESTS=1 \
  .venv/bin/python -m pytest backend/tests/test_problem_representation_persistence.py
make chapter11-proof
make lint
make test
make proof
make migrate
make db-smoke
make db-test
```

Completed results:

- Full unit suite: 177 passed, 14 skipped.
- Database baseline and session suite: 14 passed.
- Chapter 13 database persistence suite: 3 passed.
- All six pre-platform proof cases passed.
- Formatting, linting, and mypy passed across 52 source files.

## Next Chapter Boundary

Chapter 15 should make the clarification route user-operable before Chapter 14
extracts constraints. Latency, token efficiency, report truncation, and actual
human reuse judgment should be treated as evaluation targets for subsequent
product work rather than hidden by the successful correctness scores.
