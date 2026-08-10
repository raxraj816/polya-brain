# Chapter 13-C General Cognitive Control Proof

Status: in progress on `feature/chapter-12b-13-openrouter-representation`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Purpose

Chapter 13-C establishes the first executable distinction between PolyaBrain and
an LLM workflow. PolyaBrain owns the state-dependent action decision. Models,
search, memory, calculators, code, databases, simulations, and human input are
capabilities that return observations.

## Implemented

- Experimental cognitive-action taxonomy outside the core contracts.
- Typed action candidates with target, purpose, expected observation,
  usefulness, cost, risk, capability, and success/failure conditions.
- Typed action decisions with state fingerprints and rejected-candidate reasons.
- Capability registry with declared supported actions, version, risk, approval,
  timeout, cost, and fail-closed execution.
- Sanitized capability exceptions without provider or secret payloads.
- Deterministic controller policy driven by `PolyaState`, gap priority, gap
  nature, capability availability, cost, risk, and failed-action history.
- Bounded cognitive kernel that records decision and observation events, applies
  typed state updates, and stops safely.
- Verification and reflection required before a run can finish as completed.
- Failed search recovery that selects inspection rather than repeating the
  failed action.
- Failed-verification recovery that invalidates the stale verification report,
  replans, executes a revised check, and verifies again.
- Explicit `needs_input` termination when clarification cannot proceed without a
  human response.
- Experimental procedural memory that learns only from verified completed runs
  and changes a related future action from search to inspection.
- Durable governed semantic, episodic, and procedural memory in the persisted
  runtime, with relevance-gated recall and verified-only strategy preference.
- Raw-input `CognitiveRuntime` plus a typed adapter that exposes the real Chapter
  13 Problem Representation Engine as the subordinate `interpret` capability.
  Engine trace, token, version, framing, and clarification metadata remain
  inspectable; model output does not take controller ownership.
- A minimum production capability suite for gap detection, hypotheses, planning,
  bounded analytic execution, verification, reflection, exact local arithmetic,
  and human input. Model outputs are schema-checked and get at most one bounded
  repair; an unchanged failed action is never repeated as fake progress.
- Deterministic procedures for fully specified binary arithmetic, so exact work
  uses a calculator, repeated calculation, and inverse-identity verification
  without spending model tokens.
- Canonical persistence for gaps, evidence, hypotheses, plans, and verification,
  plus full reflection metadata in the audit trace.
- `GET /api/v1/sessions/{session_id}/report` exposing conclusion, confidence,
  evidence for and against, checks, contradictions, open questions, next action,
  reflection, and audit path.
- Production paths for bounded web acquisition, local artifact inspection,
  table measurement/querying, safe Python, deterministic simulation, and
  controlled experiment evaluation.
- A six-category full-outcome harness that alternates condition order and gives
  PolyaBrain and the direct model the same configured model, explicit state,
  typed tools/observations, six-call budget, and per-call output limit.

## Offline Structural Proof

Run:

```bash
make cognitive-proof
```

The proof covers:

- ambiguous input -> clarify;
- mathematics -> calculate;
- current technical research -> search;
- software debugging -> inspect;
- data analysis -> measure;
- planning -> simulate;
- scientific reasoning -> experiment;
- contradictory input -> reframe;
- analogical transfer -> retrieve memory;
- creative synthesis -> hypothesize.

Every case continues through a registered capability, state update, hypothesis,
plan, execution, independent verification, reflection, and controller-owned
stop. The current technical-research case deliberately fails search and verifies
recovery through inspection.

The mathematics case deliberately fails its first independent check. The kernel
must follow `verify -> replan -> execute -> verify`; a changed state cannot reuse
the earlier verification report.

## Live First-Action Comparison

Run only with the synthetic, non-confidential fixtures:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
.venv/bin/python evals/chapter_13c/run_live_action_baseline.py
```

On the recorded 2026-08-09 run, the controller selected an accepted action in
10/10 cases. The same configured model selected 8/10; its two failures were
invalid structured outputs. Mean action-decision latency was approximately
0.22 ms for the controller and 13.4 seconds for the model. The model used 15,580
tokens. This is evidence about the first action only, and parser failures must
not be presented as evidence of end-to-end outcome superiority.

## Verification So Far

- Focused cognitive controller/kernel/procedural-memory tests: 20 passed.
- Raw-input representation-to-kernel composition: success and clarification
  paths passed, including a complete raw equation run.
- Offline cross-domain structural cases: 10/10 passed.
- Recovery cases: 1/1 passed.
- Failed-verification detection and recovery cases: 1/1 passed.
- Repeated failed actions against the same target: 0.
- Verified procedural transfer cases: 1/1 passed.
- Live next-action cases: controller 10/10; direct model 8/10, including two
  invalid structured responses.
- The controller uses no model for action selection in this proof.

## First Persisted Full Outcome

A rebuilt Docker API run solved `23 * 7?` through:

```text
interpret -> discover constraints -> detect gaps -> calculate -> hypothesize
-> plan -> execute -> verify -> reflect -> stop
```

It returned `23 * 7 = 161.`, `verification_status=passed`, and a report with two
provenance-bearing calculator observations, an inverse-identity verification
check, no counter-evidence, no open questions, a bounded next action, full
reflection, and an audit-trace link. The equivalent in-process run completes in
milliseconds and makes no cognitive model calls.

Live model-backed attempts reached progressively farther through the same loop.
The final remaining failure was an OpenRouter HTTP 429 at verification after the
earlier stages and real calculator execution succeeded. This is a
provider-capacity failure, not a reasoning or correctness result. The product
stopped with insufficient evidence and did not repeat the failed action.

## Full Outcome Gate

Run only with the synthetic non-confidential cases:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
.venv/bin/python evals/chapter_13c/run_live_outcome_comparison.py
```

The harness scores conclusion correctness, source provenance, explicit checks,
recovery, terminal status, latency, calls, and tokens. It writes a sanitized
provider-blocked artifact rather than treating provider failure as a result.
The 2026-08-09 attempt completed zero comparable cases because the configured
free model returned HTTP 429. See
`Chapter_13C_Outcome_Benchmark_Operations.md` for the three-repetition fairness
contract, automated win threshold, and blinded-review protocol.

## Honest Boundary

This proves control structure and cross-domain routing, not superior real-world
problem-solving quality. Fixture capabilities cannot establish correctness over
unknown external environments. The persisted runtime now completes a real
deterministic arithmetic outcome and includes controller-governed model
reasoning, governed memory, search, inspection, measurement, simulation,
experiment, and safe code execution. Chapter 13-C remains incomplete until the
implemented fair multi-category live outcome harness records complete
comparable cases.
The configured free model's rate limit is not evidence for or against PolyaBrain.
None of the experimental action fields should be promoted into sacred core
contracts yet.
