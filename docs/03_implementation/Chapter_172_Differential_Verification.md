# Chapter 172 — Differential verification and lean-first escalation

Status: implemented and evaluated on two frozen, agent-authored held-out sets.
Independent human tasks, blinded review and real-user return remain pending.
Binding decision: master plan, "Chapter 172: Differential verification and
lean-first escalation".

## Why this chapter exists

The Chapter 171 evidence showed the kernel losing to a one-call lean loop on
every known coding case (lean 12/12 twice; kernel 5/12 then 11/12) at roughly 3x
cost, 5x tokens and 2.3x time. Re-deriving answers the model already gets right
cannot win. A verification layer only earns its cost where the model is
confidently wrong, and must be nearly free where it is not.

The observable failure of a lean loop is structural: it writes its own tests, so
its tests share its misreading of the problem. If it pattern-matches a familiar
problem (classic LRU, LeetCode median, half-open intervals) while the user's
specification differs, its own assertions pass and the bug ships.

## Mechanism

For self-contained implementation tasks (a requested function or class with a
stated signature, sandbox execution enabled, no seed evidence):

1. **Lean solve** (`pipeline.solve`): the exact matched-baseline prompt; the model
   returns code, assertions and an explanation; failures of its own assertions
   get bounded repair.
2. **Independent oracle** (`pipeline._oracle`): a separate call that never sees
   the candidate returns a literal brute-force reference, a seeded adversarial
   input generator, the problem's stated examples as executable calls, optional
   scale inputs and stated interpretation assumptions. Examples whose call and
   expected text are not present in the problem are dropped (`sourced_examples`).
   An unusable oracle gets one retry with the concrete defect.
3. **Differential harness** (`harness.py`): deterministic code, not a model, runs
   candidate and reference in separate namespaces inside the networkless sandbox:
   stated examples, pinned regressions, up to 3,000 generated inputs smallest size
   first with per-call time limits, exception parity, int/float/bool type
   strictness and input-mutation detection; then candidate-only timing on scale
   inputs. The payload is zlib/base64 compressed to fit the 20,000-character
   sandbox admission.
4. **Adjudication** (`pipeline._adjudicate`): the most decisive finding (stated
   example, then regression, mutation, smallest generated disagreement, then scale)
   goes to one bounded call that sees the problem, the input, both outputs and both
   codes, and must return a verdict, the expected literal, a verbatim quoted
   governing requirement, and a repair for the side ruled wrong. Rulings are
   rejected (status disputed, nothing applied) when the quote is not problem text,
   the expected value is not a literal, it contradicts a stated example, or it
   contradicts the side the verdict selects. Applied repairs are re-verified from
   scratch with the counterexample pinned. Two rounds by default.
5. **Certificate** (`contracts.Certificate`): verified, repaired and verified,
   disputed, ambiguous specification (with the concrete question), unverified, or
   no candidate. Sandbox outages raise `SandboxUnavailable` and stop the run; they
   are never shown to a model as failing code.

## Product integration

- `CognitiveRuntime.run_state` hands a fresh state (no events, framing or plan) to
  `VerifiedCodingFastPath` when `VERIFIED_CODING_ENABLED`, code execution and a
  model are configured and source-patch mode is off; everything else, including
  resumed runs and seed evidence, stays in the kernel. API sessions and the local
  CLI share this path.
- `route_reason` requires an implement/write request and a Python signature with a
  return annotation (or "class X with method y"), and excludes repository,
  traceback, production and file references.
- `projection.py` maps the outcome into existing contracts: evidence (stated
  examples 0.95, differential agreement 0.85, scale timing 0.8, solver self-tests
  0.6), findings as evidence against the first draft, hypotheses, plan tasks and
  execution outputs, a `VerificationReport`, a reflection with reusable
  "requirement easy to misread" lessons, budget and usage events, and a
  `verified_coding_certificate` trace event. No core contract changed.
- The delivered answer contains exactly one code block plus findings, checks,
  assumptions and limits. Disputed, ambiguous and unverified outcomes say "Not
  verified" first and end as `insufficient_evidence`.
- Frontend `VerificationCard` shows live steps, the verdict, comparison counts and
  each finding with input, draft output, correct result and the quoted
  requirement.

## Evaluation

Model `google/gemini-3.7-flash` through OpenRouter, zero retries, one serial spend
guard per shard. Lean, self-review and verified arms share the same first answer per
attempt; the kernel is an independent production-runtime attempt (once per task).
Artifacts: `runs/verified-coding/2026-10-02-heldout-v1/` and `-v2/` (gitignored);
`report-rescored.json` in each; ledger `runs/verified-coding/campaign-ledger.json`.

Two frozen held-out sets, authored and hashed before any solver run
(`evals/verified_coding/FREEZE.json`):

- **v1**: ten "familiar problem with an explicit twist" tasks, two repeats.
- **v2**: five dense-rule tasks (npm-style range matching, multi-window limiter,
  overdraft ledger, cron next-fire with the Vixie OR rule, bracket tax with
  phase-out and single half-up rounding), authored after v1 showed no lean
  failures, frozen with the pipeline source hashes, two repeats.

Corrected results (isolated scorer, SHA-verified delivered code):

| Arm | v1 | v2 | Provider-reported USD (v1+v2) | Per task |
| --- | ---: | ---: | ---: | ---: |
| Lean | 20/20 | 10/10 | 0.48628 | 0.0162 |
| + self-review (incremental) | 20/20 | 10/10 | +0.42245 | +0.0141 |
| + differential verification (incremental) | 20/20 | 10/10 | +0.30399 | +0.0101 |
| Kernel (independent, 1 repeat) | 10/10 | 4/5 | 0.66154 | 0.0441 |

- Paired against the same lean answers: verification fixed 0 and harmed 0;
  self-review fixed 0 and harmed 0. There were no lean failures to fix.
- Certificate calibration: 29 certified and correct, 0 certified but wrong,
  1 reported "unverified" while correct (the shard's local spend cap blocked its
  oracle call; the pipeline correctly refused to certify).
- Verification added about 1.05 calls, 0.0101 USD and 19 seconds per task on top
  of lean. Lean plus verification (about 0.026 USD per task) cost about 40% less
  than one kernel attempt (0.044 USD), and the kernel failed to deliver on one task.
- Dev evidence only: on `csv_fields` the oracle's own reference was wrong on a
  stated example; adjudication quoted the problem, repaired the reference, and
  re-verified 3,000 inputs without touching the correct candidate.

**Measurement error found and corrected.** The original v2 scoring reported lean
failing `cron_next` twice and verification issuing two false certifications. The
cause was the withheld check, not the code: checks and candidate shared one
namespace, and the check's `from datetime import datetime` overwrote the
candidate's `import datetime` module binding. The cron check now uses private
aliases; all checks run through `scoring.py`, which executes them in a private copy
of the candidate namespace; all 21 check sets were revalidated (correct solutions
pass, every mutant fails, including an `import datetime`-style correct solution);
and every saved artifact was re-scored without model calls, accepting delivered
code only when its SHA-256 matched the original record. v1 results were unchanged.
The original reports remain beside the corrected ones.

**What this does and does not show.** On clearly specified self-contained tasks,
this model's lean loop was right every time, so this evaluation cannot show that
differential verification catches confident errors on held-out work; it shows the
layer is cheap, does no harm, and its certificates were calibrated on these 30
attempts. Its error-catching path is demonstrated only by deterministic tests and
one development self-correction. The decisive evidence must come from real users'
specifications, which are rarely this explicit. No superiority claim follows.

## Verification performed

- `backend/tests/test_verified_coding.py`: 26 tests covering example sourcing,
  quote grounding, ruling consistency, harness size bounds, sandboxed verified,
  repaired, wrong-reference, unsupported-ruling, ambiguous, unusable-oracle and
  oracle-retry paths, routing, the runtime fast path with trace usage accounting,
  projection and report rendering, oracle self-correction labeling, sandbox outage
  handling, and solver schema coercion.
- Full backend suite: 1,111 passed, 98 skipped (database and Docker-inspect gated)
  before the held-out run; ruff, format and strict mypy (152 files) clean.
- Frontend: typecheck, Prettier and 35 vitest tests, including
  `verification-card.test.ts`; the card was rendered and inspected visually.
- Live CLI smoke through `build_cognitive_runtime`: verified certificate on 3,000
  inputs, two model calls, 0.0088 USD, readable `report.md`.
- `validate_checks.py` (isolated scorer): 21 check sets valid; one equivalent
  semver mutant was identified by analysis and replaced.

## Known limits and next steps

The subsequent [adversarial verification chapter](Chapter_172_Adversarial_Verification.md)
records 32 new developer controls and the 0.2.0 harness repair for false agreement,
incomplete iterators, required-check omission and failed sandbox results. The
historical live results above are preserved; they were not rerun or retroactively
upgraded by these mechanism checks.

- Held-out tasks are agent-authored. They are frozen and hashed before any solver
  ran (`evals/verified_coding/FREEZE.json`) but are not independent human tasks.
- The oracle shares the model family. Sourced examples and concrete adjudication
  reduce shared misreadings; they do not remove them.
- Routing is a conservative heuristic; implementation requests without a stated
  signature stay in the kernel.
- Ambiguous specifications are reported as an open question and an
  `insufficient_evidence` run; they do not yet pause for a structured clarification
  and resume.
- Next: apply the same independent-recomputation pattern to data-analysis and
  calculation claims inside investigations, where a second, deliberately simple
  derivation can be executed and compared.
