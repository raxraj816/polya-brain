# Chapter 13-P: exact code delivery and transfer evidence

User priority: build a winning product; demo presentation can wait. The relevant
target is verified useful outcomes at competitive total cost, not feature count.

## Implemented

The conclusion reviewer can now reference executed code instead of generating it
again. The runtime attaches exact code after semantic review and validates the
delivered implementation. Execution events bind the exact source, test list and
result by SHA-256. Delivery events bind task IDs, code, raw provider answer and
assembled answer. No core contract fields were added.

Unknown, stale, duplicate, incomplete, embedded and mixed-code references fail
closed. Failed execution or review cannot publish a successful answer or lesson.
Full-code model responses remain supported. References do not waive correctness,
complexity, criterion coverage or independent execution checks.

One live scheduling run used the reference path and attached 1,864 implementation
characters without asking the reviewer to copy them. This is a measured reduction
in copying work, **not evidence of lower total tokens or a competitive win**.

The other scheduling run exposed an existing dependence on a free-form framing
label: `interval_intersection_scheduling` did not enable code delivery checks.
Reference availability now depends on bound sandbox records. Delivered Python
blocks are identity-checked regardless of problem label; analyses that merely use
Python as a tool may still return prose. Replaying both saved executions confirms
references are now available for both labels. This label correction happened
after the live pilot; its production behavior is covered by regression tests.

## Preserved live measurements

Both arms use `google/gemini-3.7-flash`, common six-call / 20,000-output-token /
four-sandbox / 240-second ceilings, with hidden retries and fallback routes off.
The existing scheduling case and a newly frozen signed-array shortest-subarray
task each ran twice. Both are developer-authored; neither is an independent
holdout. The two experiment processes overlapped for part of their runs, so their
wall times are observations under concurrent load, not isolated latency estimates.

| Task / repeat | Polya completed and checked | Lean checked | Polya calls / total tokens | Lean calls / total tokens |
| --- | --- | --- | --- | --- |
| Scheduling 0 | Pass | Pass | 3 / 20,011 | 1 / 4,671 |
| Scheduling 1 | Pass | Pass | 4 / 28,029 | 1 / 5,064 |
| Signed-array span 0 | Fail | Pass | 3 / 18,116 | 3 / 11,471 |
| Signed-array span 1 | Fail | Pass | 3 / 18,542 | 1 / 3,088 |

Artifacts remain under `runs/coding-readiness/matched-code-delivery-v1` and
`runs/coding-readiness/matched-code-delivery-transfer-v1`. Each preserves inputs,
provider requests/responses, tool requests/results, traces, delivered outcomes and
independent scores. Earlier unsuccessful pilots remain untouched.

The new independent oracle runs 3,000 seeded brute-force comparisons plus nine
boundary/scale checks. Its own regression checks accept an independently written
reference and reject four faulty strategies: empty-subarray acceptance, strict
threshold comparison, mutation and a positive-only sliding window.

## Observed generated-check bottleneck

Both Polya attempts generated the same incorrect assertion:

```python
assert shortest_span([-1, -2, -3], -5) == 2
```

The correct length is 1: `[-1]` is nonempty and its sum is at least -5.
Polya correctly withheld its answer when the declared test failed, but could not
resolve the bad expectation. One attempt retried implementation against the same
bad test; another could not admit recovery within its remaining reservation.

The separate `candidate-diagnostic.json` replays all three executed candidate
snapshots against unchanged withheld checks. All pass those checks. These are
undelivered candidates, so the public outcome remains **0/2**, not 2/2.

This failure motivated generated-check admission and bounded recovery. Original
failure history remains intact; the runtime cannot silently rewrite a failed
test to match the candidate.

## Generated-check admission and recovery

The proposal instructions now require invented examples to use a simple executable
reference derived from the specification, separate from the delivered algorithm.
The reference must not invoke the candidate. Final review inspects independence,
specification fidelity and whether comparisons actually execute as assertions.

A narrow static screen rejects assertions that compare a function call to a
literal unless that expression appears in the user's input or the check is
unchanged from an earlier admitted plan. Initial and repair responses receive the
same screen. Nested schema errors and independently detectable test-source errors
are reported together, so the existing bounded repair sees both problems.
`generated_check_sources_screened` records the screen version and task IDs;
it explicitly retains the need for semantic review.

This is not a general oracle verifier: it can reject paraphrased examples and
does not track expectations hidden behind variables or prove a dynamic reference
correct. Regression tests explicitly demonstrate that an incorrect dynamic oracle
can pass this origin screen. Execution and review remain necessary, and shared
model mistakes remain possible.

The sandbox now fails a submitted single Boolean expression when it evaluates to
False, instead of silently discarding its value. Statement suites still execute
normally; arbitrary ignored expressions inside statement suites are not certified.
The harness version is recorded in execution traces and evaluation manifests.

Recovery planning reserves only the provider attempts that fit remaining calls
and full per-request output allowances. Retry, schema repair and fallback share
that limit. Exhausted budgets fail before calling the model, and unknown output
usage remains reserved. Original failed tests and explicit replacement links
remain mandatory.

Adversarial regressions cover incorrect implementations, incorrect references,
ignored false expressions, changed user expectations, combined repair diagnostics,
last-call recovery and exhausted budgets. The fresh directed-walk task was frozen
before its first live run. Its independent oracle uses transitive closure and
walk-length enumeration; checks cover 600 seeded multigraphs, relevant versus
irrelevant cycles, parallel edges, input preservation and long-chain scale cases.
The oracle accepts a separately written reference and rejects five targeted
mutants. Both tasks remain developer-authored, not independent holdouts.

## Preserved follow-up attempts

All follow-ups retain the same model and outer budgets. Each pair is run
sequentially with arm order alternated across repetitions. Prompt-only changes
and admission changes were evaluated separately; failed attempts remain scored
as failures.

| Experiment | Polya completed / checked | Lean checked | Polya calls / total tokens by repeat | Lean calls / total tokens by repeat |
| --- | --- | --- | --- | --- |
| `matched-derived-checks-transfer-v1` | 1/2 | 2/2 | 5 / 42,147; 3 / 17,157 | 1 / 2,849; 2 / 6,674 |
| `matched-check-admission-transfer-v1` | 1/2 | 2/2 | 4 / 27,499; 3 / 20,282 | 1 / 2,770; 1 / 3,060 |
| `matched-check-admission-transfer-v2` | 2/2 | 2/2 | 4 / 27,908; 4 / 26,471 | 1 / 2,848; 1 / 2,792 |
| `matched-check-admission-graph-v1` | 2/2 | 2/2 | 4 / 33,455; 4 / 34,331 | 1 / 3,710; 1 / 3,961 |

The prompt-only failure repeated invented wrong expectations and later changed
checks without retiring the original failed work. The runtime withheld success.
The first admission experiment repaired one proposal successfully; the other
exhausted its repair after nested hypothesis validation hid an unsourced literal
check. The combined-diagnostic repair addresses that observed failure without
adding a provider attempt. These are development measurements, not a causal
ablation or an estimate of general reliability.

The combined-diagnostic follow-up completes both signed-array attempts and passes
all 3,000 independent comparisons and nine boundary/scale checks. Both require
one proposal repair; the second receives both hypothesis and test-source errors
in that repair. Polya takes 70.70 / 69.95 seconds versus lean's 20.36 / 16.49.
Completion improved on the frozen regression; token use and latency remain worse.
Local backend tests overlapped part of this pilot; elapsed times are observations,
not controlled performance estimates.

Both first live attempts on the fresh directed-walk task deliver code that passes
all 600 independent multigraph comparisons and eight boundary/scale checks,
including 100,000 vertices and duplicate-edge modular counting. Runtime acceptance
also passes, with exact delivered/executed code identity. Polya uses four calls
in each attempt and 78.32 / 91.04 seconds; lean passes with one call each and
20.46 / 22.57 seconds. Each Polya proposal needs one repair. In the first graph
attempt, the repair feedback includes both unsupported selection and an unsourced
literal expectation. The experiment follows the completed signed-array pilot,
without concurrent live benchmark processes.

The latest build therefore completes four of four attempts across these two
developer tasks, as does the lean baseline. This small sample supports the
specific completion fix and transfer to one fresh task. It does not establish
broad superiority or repeat-user value. The next measured bottleneck is the
avoidable proposal repair plus framing/proposal/review overhead. Preserve these
checks while measuring ways to reduce that overhead and reuse verified work;
further polishing a known case alone will not establish product advantage.

## Reproduction

```bash
PYTHONPATH=backend:. .venv/bin/python -m evals.chapter_13p.coding_execution.matched \
  --model google/gemini-3.7-flash --repeats 2 \
  --output runs/coding-readiness/NEW-scheduling-run

PYTHONPATH=backend:. .venv/bin/python -m evals.chapter_13p.coding_execution.matched \
  --cases evals/chapter_13p/coding_execution/transfer-cases.json \
  --model google/gemini-3.7-flash --repeats 2 \
  --output runs/coding-readiness/NEW-transfer-run

.venv/bin/python -m pytest backend/tests/test_code_delivery.py \
  backend/tests/test_coding_execution.py backend/tests/test_bounded_verification.py \
  backend/tests/test_transfer_coding_checks.py backend/tests/test_coding_eval_evidence.py
```

Use new output paths. Model calls are paid and use the existing configured
provider; tests use fake model proposals and real Docker where applicable.

Final verification: 935 backend tests passed with PostgreSQL tests enabled and
Docker available; Ruff passed and strict mypy passed for 137 production files.
Existing dependency deprecation warnings remain. No commits or pushes were made.
