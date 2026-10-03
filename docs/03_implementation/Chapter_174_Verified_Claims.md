# Chapter 174 — Verified claims and failure-pattern memory

Status: implemented and tested end to end with scripted model responses and the
real sandbox. The frozen live evaluation is built but **not yet run**: the model
provider now refuses requests with HTTP 402 (payment required), so the account
needs credits and an explicit budget. Binding decision: master plan, "Chapter 174".

## Verified claims: `polyabrain ask-data`

```bash
./polyabrain ask-data --table orders.csv --table customers.csv \
  "What is the total paid revenue from customers currently in Germany?"
```

1. **Lean answer** (`answer`): one call sees the question, each table's schema and
   five sample rows, and returns the answer text, every number as a claim with a
   precise definition and its stated value, and standard-library code computing all
   claims. The code runs on the full data in the sandbox; one bounded repair is
   allowed when it fails or omits a claim.
2. **Independent derivation** (`verifier`): a separate call sees the question,
   schema, samples and the claim definitions only (no values, no code), writes its
   own computation (preferring in-memory SQL via `sqlite3`), and must flag any
   definition that does not answer the question.
3. **Deterministic comparison** (`claim_runner@0.1.0`): both derivations run on the
   real data and on four seeded perturbed copies (shuffled, 70% subset, duplicated
   rows, jittered values) inside one isolated sandbox run. Tables reach the sandbox
   through the new `DockerPythonSandbox.execute_with_data` (compressed into the
   program stream, read-only, at most 2 MB in 16 files; no host mounts; code
   admission limits unchanged). Values compare with numeric tolerance, case- and
   space-insensitive strings, recursive lists/dicts, and booleans never equal numbers.
4. **Adjudication**: claims whose derivations disagree on any data version go to one
   bounded call; a ruling whose value contradicts the derivation it selects is
   rejected.
5. **Proof status per claim**: proven (agree on all versions and the stated value
   matches within its stated precision), corrected (the text contradicted its own
   computation, or adjudication sided with the verifier), supported after review,
   disputed (unresolved, ambiguous, or the definition misses the question), or
   unverified. Answer status: verified, corrected and verified, needs review, or
   unverified. Provider refusals are reported with an actionable reason (for example
   "payment required (check the account's credits)").

Outputs: `report.md` (corrections first, a claim-by-claim proof table, reasons,
assumptions, limits), `certificate.json`, `trace.json`, `answer_code.py`,
`verifier_code.py`. Exit 0 verified/corrected, 3 needs review, 4 unverified.

## Failure-pattern memory

`app/memory/failure_patterns.py` stores confirmed defects with the concrete trigger
and evidence: regressions from verify-change, corrected or disputed claims from
ask-data, and draft defects from verified coding. Each run records a pattern at most
once; the file is bounded to 500 patterns, written atomically, and damaged lines are
skipped. The most relevant patterns for the same domain are appended to the next
input-generator or verifier prompt as explicit hints that "are NOT requirements".
Local default `runs/memory/failure_patterns.jsonl` (`FAILURE_PATTERNS_PATH`,
`FAILURE_PATTERNS_ENABLED`); CLI runs, API sessions and the verified-coding fast
path all learn. Inspect with `./polyabrain patterns`. Whether hints improve catch
rate or cost is **unmeasured** until the with/without comparison runs.

## Frozen evaluation (ready, blocked on provider credits)

`evals/verified_claims/build_tasks.py` deterministically builds eight agent-authored
tasks with known answers and realistic traps: month, status and case-insensitive
test-account filters; NA/blank latencies with an even-count median; user-id case and
whitespace normalization (correct 7, unnormalized 1, lowercase-only 3); weighted vs
naive average price; signed month-over-month change; top-3 with alphabetical ties;
a join where the latest duplicate customer record wins; retry-duplicated
transactions. Data and tasks are hashed in `evals/verified_claims/FREEZE.json`
before any solver run (the only edit after freezing removed an unused variable and
was confirmed byte-identical).

`evals/verified_claims/run.py` scores lean (stated values) against verified (final
proven, corrected or reviewed values) on every required fact, and counts false
certifications (verified or corrected status while a required fact is missing).

```bash
PYTHONPATH=backend:. .venv/bin/python -m evals.verified_claims.run \
  --model google/gemini-3.7-flash --input-rate 0.00000075 --output-rate 0.00000375 \
  --dollars <approved cap> --output runs/verified-claims/frozen-v1
```

The single development call made this chapter (`runs/verified-claims/dev-1`) was
reported as refused with HTTP 402. The later offline campaign inventory found no
itemized provider calls or billing evidence in its saved trace, so a zero charge
is not independently established by that artifact. Earlier unexplained provider
failures in the Chapter 173 runs may have had the same cause; their unresolved cost
reservations remain retained even though they are excluded as infrastructure
failures from quality results. See [aggregate accounting](Chapter_171_Campaign_Accounting.md).

## Verification

- `backend/tests/test_verified_claims.py` (10): tolerance and boolean comparison,
  table loading bounds, proven claims (5/5 data versions, verifier never sees values
  or code), stated-value contradiction corrected, misread refund filter caught and
  corrected through adjudication, hard-coded numbers that agree on the real data but
  fail on perturbed copies, definition issues never proven, answer repair plus
  unusable verifier, provider refusal reason, and the CLI report.
- `backend/tests/test_failure_patterns.py` (3): merge, ranking, bound, damaged lines,
  and learning across runs for verify-change and ask-data.
- Full backend suite: 1,187 passed, 98 skipped (Postgres-gated); ruff and strict
  mypy (164 files) clean.

## Limits

- Both derivations are model-written from the same question; the definition check
  reduces but does not remove shared misreadings.
- Only claims stated as checkable quantities are verified; narrative is not.
- Tables are limited to 2 MB of CSV/JSON; no databases, spreadsheets or logs parsing
  beyond JSON lists yet. CLI only; API session and workbench view are next.
- The evaluation tasks are agent-authored. A public benchmark with known answers
  needs explicit approval of the dataset before download.
