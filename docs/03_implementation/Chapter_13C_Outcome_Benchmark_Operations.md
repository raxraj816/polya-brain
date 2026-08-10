# Chapter 13-C Outcome Benchmark Operations

Status: harness complete and offline-verified; live comparison capacity-blocked.

## Purpose

This gate determines whether the cognitive controller adds measurable value
over the same base model operating directly. It is not a marketing demo and it
must not count provider failure as a win for either condition.

## Fairness Contract

Every comparison pair receives:

- the same synthetic, non-confidential pre-structured problem;
- the same model slug and provider account;
- the same executable domain tools and exact observations;
- the same maximum of six model calls;
- the same 1,800 output-token limit per call;
- the same success criteria and automated scorer.

Condition order alternates across cases and repetitions. A pair is recorded
only after both conditions finish. The default run executes three repetitions
of six categories, producing 18 comparison pairs with nine PolyaBrain-first and
nine direct-model-first trials.

PolyaBrain may use fewer model calls when a deterministic procedure is
available. That is intended product behavior; actual calls, tokens, latency,
and capability costs remain visible as outcomes.

## Automated Gate

The harness scores each response on:

- expected conclusion content;
- evidence-source provenance;
- at least one explicit verification check;
- required recovery after a failed tool;
- truthful terminal status;
- compliance with the shared call ceiling.

Minimum evidence before claiming a benchmark win:

1. All 18 pairs complete without provider-capacity errors.
2. PolyaBrain passes at least 15/18 trials and at least 2/3 in every category.
3. The recovery case passes 3/3 without repeating the failed action.
4. PolyaBrain produces zero unsupported forced conclusions.
5. PolyaBrain's pass rate exceeds the direct condition by at least 10 percentage
   points.
6. Tokens and latency are reported even when correctness improves; overhead is
   never hidden.

These thresholds are enforced by the harness and written under
`automated_gate` in `summary.json`. A completed run also records
`human_review_status: pending` and `product_value_claim_ready: false`; automated
success alone is not a product-value claim. The command exits nonzero when the
automated gate does not pass.

Failing this gate means improve the controller, memory, verification, or tools
and rerun. It does not justify changing the general-purpose vision or gaming the
cases.

## Blinded Human Review

Automated keyword scoring is necessary but insufficient. After a completed
run, generate a condition-blinded packet:

```bash
.venv/bin/python evals/chapter_13c/build_blind_review_packet.py \
  evals/chapter_13c/live_outcome_runs/<date>/<run-id>/summary.json
```

Keep `blind_review_condition_key.json` separate until reviewers finish. Use at
least two independent reviewers. Before a product-value claim, PolyaBrain should
be preferred in at least 60% of non-tied judgments and should not score lower on
unsupported claims or verification quality.

## Running the Live Gate

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
.venv/bin/python evals/chapter_13c/run_live_outcome_comparison.py
```

Use `--repetitions 1 --limit 1` only as a capacity smoke test, never as evidence
of product superiority. Use `--case-id <id> --repetitions 1` to diagnose one
named case without rerunning unrelated cases; this is also not win evidence.

## Current External Blocker

On 2026-08-10 the configured model completed a corrected one-pair smoke test in
both conditions. A subsequent full-run diagnostic exposed and led to fixes for
an unenforced PolyaBrain model-call ceiling, overlong plans, and insufficient
direct-condition JSON repair; that interrupted run is explicitly invalidated
and is not evidence. After the fixes, two identical named-case attempts against
the configured NVIDIA free endpoint ended with HTTP 502, and an eligible OpenAI
free-model attempt ended with HTTP 429. A subsequent attempt using the
user-selected `poolside/laguna-s-2.1:free` model also ended immediately with
HTTP 429 after all configured retries. No post-fix comparison pair completed.

The configured OpenRouter account is free-tier and has not demonstrated enough
stable capacity for 18 pairs. Complete the gate only after reliable paid
OpenRouter capacity, BYOK, or another provider-neutral adapter is available.
