# Chapter 13-P coding execution gate

## Matched tool-access development pilot

`matched-cases.json` freezes a scheduling problem before live execution. Its
independent checks include 1,200 randomized calendar sets, boundary cases, input
immutability and a sparse large-time-range case. These checks are withheld from
both solver prompts. The case is developer-authored, not independently held out.

```bash
PYTHONPATH=backend:. .venv/bin/python -m evals.chapter_13p.coding_execution.matched \
  --model google/gemini-3.7-flash --repeats 2 \
  --output runs/coding-readiness/matched-common-slot-NEW
```

The lean arm asks one model for code, assertions and explanation, executes it,
and uses failures for bounded repair. The Polya arm uses the production public
runtime. Both use the same route, exact problem text, networkless standard-library
Docker image, and common outer ceilings: six provider calls, 20,000 output tokens,
6,000 output tokens per request, four sandbox calls and 240 seconds. Sandbox
attempts have five seconds and 64 MB each. Hidden retries and route fallbacks are
disabled. Input tokens are measured; Polya retains its internal scheduling and
verification policy. There is no shared pre-request input-token ceiling.

The runner alternates arm order across repeats, preserves each request before
calling the provider/tool, and records each response or failure separately. It
scores delivered code only after both arms finish. It reports Polya's additional
execution-contract acceptance separately from the common independent code score.
If a provider call fails with unknown usage, that arm stops further model spend.
An interrupted experiment retains its manifest and partial per-arm artifacts;
it is incomplete, not a passing experiment. Choose a new directory for each run.

This pilot tests whether the orchestration earns its overhead with comparable
execution access. Two repetitions of one known case cannot establish broad
superiority, calibrated reliability, or semantic correctness of explanations.

## Generated-check and fresh-graph follow-ups

The signed-array progression is preserved in
`runs/coding-readiness/matched-derived-checks-transfer-v1` (Polya 1/2),
`matched-check-admission-transfer-v1` (1/2), and
`matched-check-admission-transfer-v2` (2/2). Lean passes both repeats in each.
The latest repair reports unsupported hypothesis selection and unsourced literal
checks together within the original attempt limit. Its delivered implementations
pass the unchanged withheld checks; this does not establish a cost or latency win.

The runner records `python_checks@0.2.0`: a submitted single Boolean expression
that evaluates to false now fails. Both arms share this harness. Generated-check
source screening and semantic review are Polya runtime behavior; they do not
alter the independent checks or feed them back into either solver.

`fresh-graph-cases.json` was frozen before its first live attempt. It asks for
finite directed-walk counts with relevant cycles, parallel edges, self-loops,
empty walks and large chains. The withheld oracle uses transitive closure and
bounded walk-length counting on 600 seeded small multigraphs plus eight boundary
and scale checks. Its regressions accept an independent implementation and reject
five mutants. This is a fresh developer task, not an external holdout.
The first live pilot, `matched-check-admission-graph-v1`, completes 2/2 in both
arms with independent checks passing. Polya also passes runtime acceptance but
uses four calls per attempt versus lean's one. Full usage and elapsed-time records
are retained in its summary and the Chapter 13-P delivery notes.

```bash
PYTHONPATH=backend:. .venv/bin/python -m evals.chapter_13p/coding_execution.matched \
  --cases evals/chapter_13p/coding_execution/fresh-graph-cases.json \
  --model google/gemini-3.7-flash --repeats 2 \
  --output runs/coding-readiness/NEW-graph-run
```

## Compact interface and browser delivery

For the subsequent compact-interface and bounded response-edit experiments, see
[Chapter 13-P compact interface](../../../docs/03_implementation/Chapter_13P_Compact_Model_Interface.md).
The preserved `matched-edit-repair-transfer-v1` and `matched-edit-repair-graph-v1`
directories under `runs/coding-readiness` each contain two passing attempts per
arm. Both graph attempts use real structural repair; neither signed-array attempt
needs repair. Keep these distinctions when interpreting token reductions.
`wire_audit.py` performs a no-provider-call request-byte replay; its original
7.78% result predates edit repair and is not a live token-cost measurement.

The separate `browser-edit-repair-graph-v1` directory preserves a real saved
workbench session, exact downloaded report, browser verification notes and
independent replay results. Its `state.json` is reconstructed from persisted plan
records and public API responses. Recheck it without model calls:

```sh
PYTHONPATH=backend:. .venv/bin/python -m evals.chapter_13p.coding_execution.verify \
  finite_routes runs/coding-readiness/browser-edit-repair-graph-v1
```

## Historical one-call comparison

The follow-up `transfer-cases.json` freezes a signed-array shortest-subarray task.
Use the same matched runner with `--cases` pointing to that file. Its withheld
checks include 3,000 small brute-force comparisons and boundary/scale cases.
`backend/tests/test_transfer_coding_checks.py` checks the oracle against a
reference and targeted mutants. The first two live Polya attempts failed their
own incorrect expected value; both lean attempts passed. Saved undelivered
Polya candidates pass withheld checks in a separate diagnostic, which does not
change the failed product scores. Full results and delivery changes are in
`docs/03_implementation/Chapter_13P_Code_Delivery_And_Transfer.md`.

This benchmark checks whether the production Cognitive Runtime can turn a
fully specified coding problem into a plan, execute the proposed code in the
isolated Python sandbox, verify the recorded result, and deliver the exact code
that was executed.

The independent checks in `verify.py` are developer-authored and remain outside
the model prompt. They cover correctness and selected complexity or scale
properties for each case. `gate.py` requires every declared case to have a run,
requires the runtime report and independent checks to pass, and requires the
delivered code block to match the executed code byte-for-byte after trimming.

Run the gate after producing one run directory per case:

```bash
PYTHONPATH=backend:. .venv/bin/python evals/chapter_13p/coding_execution/gate.py \
  --case median=runs/coding-readiness/median-gemini-v5 \
  --case integer_coverage=runs/coding-readiness/integer-coverage-gemini-v1 \
  --case lexicographic_toposort=runs/coding-readiness/toposort-gemini-v1
```

The gate replays the exact delivered code and applies current execution/recovery
rules to saved state. It rejects ambiguous code, duplicate assignments, missing
cases, incomplete or truncated execution, and unretired failed tasks. It does not
rerun model reasoning or prove complexity. The historical paths above now fail
the gate: the interval run changed a test oracle and lacks an explicit recovery
link. The independent code checks still pass for that case; code correctness on
these checks and runtime acceptance are distinct observations.

Run the same-model direct baseline and compare resource use with the PolyaBrain
runs:

```bash
PYTHONPATH=backend:. .venv/bin/python \
  evals/chapter_13p/coding_execution/direct_baseline.py \
  --model google/gemini-3.7-flash \
  --output runs/coding-readiness/direct-gemini-baseline-v2.json

PYTHONPATH=backend:. .venv/bin/python \
  evals/chapter_13p/coding_execution/compare.py \
  --baseline runs/coding-readiness/direct-gemini-baseline-v2.json \
  --polya median=runs/coding-readiness/median-gemini-v5 \
  --polya integer_coverage=runs/coding-readiness/integer-coverage-gemini-v1 \
  --polya lexicographic_toposort=runs/coding-readiness/toposort-gemini-v1 \
  --output runs/coding-readiness/coding-baseline-comparison-v2.json
```

Use new output paths for every experiment. The direct runner reserves its output
exclusively, checkpoints the case being attempted before the provider call, and
saves each finished result atomically. It preserves prompt, response, code,
SHA-256 bindings, check version, usage and failures. Hidden provider retries are
disabled. Missing usage remains null. Digests detect inconsistent artifacts; they
are not signatures or protection against deliberate rewriting of the entire file.

The comparison independently replays both delivered implementations. It reports
saved success separately from replay acceptance and compares each input hash with
the declared case. It cannot establish equal model routing, tool access, budgets,
or inclusion of all development attempts. No superiority claim follows from it.

`historical-audit.json` records the real Docker replay after this repair. All
three Polya implementations passed independent checks; only median and topological
ordering met the current execution contract. All three historical direct answers
are unverified because their response/code artifacts were not saved. That is
missing evidence, not evidence that their implementations were wrong. The median
Polya prompt also differs from the declared baseline prompt. The earlier all-pass
comparison must not be used as a competitive result.

Current verification-boundary regressions run without a paid model:

```bash
.venv/bin/python -m pytest backend/tests/test_coding_execution.py backend/tests/test_coding_eval_evidence.py
```

The Docker recovery cases execute a deliberately incorrect count function and
its correction through the public runtime with scripted model responses. They
require the pinned sandbox image; pytest reports them as skipped if unavailable.
They check unchanged assertions, preserved failure history, zero reviewer calls
on failed execution, semantic review after successful execution, and exact code
delivery. Plausible invariant/complexity metadata never bypasses review. This is
runtime regression evidence, not an autonomous repair or competitive benchmark.

Verification-boundary checkpoint: the full backend suite passed with 726 tests
passing and 62 skipped. Both Docker recovery variants ran successfully (with and
without an explicit execution unknown). Ruff passed; mypy passed for 134 source
files. Skipped integration tests are not counted as verified. The recovery
sequence uses four scripted model requests: framing, proposal, replacement plan,
and final review. Its first failed execution adds no reviewer request. A successful
first attempt still uses three requests; no correctness claim is inferred from
the presence of an algorithm explanation.
