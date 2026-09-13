# Chapter 13-C General Cognitive Control Proof

This proof exercises the same deterministic cognitive controller across ten
materially different problem categories. The first action must follow from the
explicit obstacle in `PolyaState`; an LLM does not control the loop.

Run:

```bash
.venv/bin/python evals/chapter_13c/run_cognitive_control_proof.py
```

Each case must:

1. Select the expected first cognitive action.
2. Execute only through a registered capability.
3. Treat the result as an observation and update the gap.
4. Generate a testable candidate.
5. Plan and execute an independent check.
6. Verify before setting the final answer.
7. Reflect only after verification.
8. Stop through the controller.

The mathematics case also injects a failed first verification. It must replan,
execute a revised check, and verify again; any material state revision
invalidates the prior verification report.

The current-API case deliberately fails its primary search capability. The same
controller must use failure history to select inspection next instead of
repeating the failed action.

After that run completes with verification and reflection, the proof learns the
successful inspection recovery as an experimental procedural strategy. On a
related new problem, the controller must change its first choice from search to
inspection. Unverified runs are forbidden from teaching procedural memory. The
structural fixture uses an in-process store; the persisted product runtime uses
the verified Postgres procedural-memory implementation.

The generated run directory contains a sanitized trace and result for each
case, plus an aggregate summary.

With an explicitly configured non-confidential evaluation provider, compare the
controller's first action with the same model given the identical state and
declared capability set:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
.venv/bin/python evals/chapter_13c/run_live_action_baseline.py
```

This live comparison is limited to next-action selection. It records parser
failures, unsupported model choices, latency, tokens, and exact expected-action
accuracy. It does not substitute for a later end-to-end outcome comparison in
real environments.

The complete outcome gate uses six synthetic categories, identical
pre-structured problems, the same configured model, the same typed tools and
observations, an equal six-call model budget, an equal per-call output limit,
and alternating execution order. Polya uses its current fused deliberator and
fused conclusion checker rather than the superseded five-stage model path:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
.venv/bin/python evals/chapter_13c/run_live_outcome_comparison.py
```

It scores conclusion terms, source provenance, explicit verification, recovery,
latency, calls, and tokens across three repetitions by default. Provider
failures create a sanitized `blocked.json` instead of being counted as a win or
loss. The model capability deadline includes retries and structured-output
repair rather than resetting for every attempt.

After a complete run, build the separately keyed, condition-blinded review
packet:

```bash
.venv/bin/python evals/chapter_13c/build_blind_review_packet.py \
  evals/chapter_13c/live_outcome_runs/<date>/<run-id>/summary.json
```

The operational fairness contract and product-value thresholds are documented
in `../../docs/03_implementation/Chapter_13C_Outcome_Benchmark_Operations.md`.

This is deliberately labeled a structural proof. Fixture capabilities establish
that the controller, capability boundary, state updates, verification gate, and
cross-domain routing work. These checks do not establish superior real-world
problem solving. A 2026-08-22 paid-route qualification completed all six pairs
with both conditions passing 6/6, while Polya used about 2.19 times the tokens.
Chapter 13-C remains open: revise the runtime and add adversarial evidence cases
before running the unchanged three-repetition gate.

Chapter 13-I subsequently reran all 18 pairs after adding exact trusted evidence
closure. Polya passed 18/18 with zero model tokens; direct passed 17/18 using
47,656 tokens. The general automated gate remains false because the correctness
advantage is below its predeclared threshold. The result is evidence only for a
narrow known-procedure compute win.
