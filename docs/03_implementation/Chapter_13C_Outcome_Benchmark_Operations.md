# Chapter 13-C Outcome Benchmark Operations

Status: harness complete and offline-verified; one stable six-pair live
qualification run complete, superiority gate still open.

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

## Historical External Blockers

On 2026-08-10 the configured model completed a corrected one-pair smoke test in
both conditions. A subsequent full-run diagnostic exposed and led to fixes for
an unenforced PolyaBrain model-call ceiling, overlong plans, and insufficient
direct-condition JSON repair; that interrupted run is explicitly invalidated
and is not evidence. After the fixes, two identical named-case attempts against
the configured NVIDIA free endpoint ended with HTTP 502, and an eligible OpenAI
free-model attempt ended with HTTP 429. A subsequent attempt using the
user-selected `poolside/laguna-s-2.1:free` model also ended immediately with
HTTP 429 after all configured retries. No post-fix comparison pair completed.

On 2026-08-22 the configured `openrouter/auto` route completed the math pair
with both conditions passing, then returned no text content on pagination. A
pinned `deepseek/deepseek-v4-flash-0731` diagnostic completed pagination before
the current fusion change: both conditions passed, but Polya used six model
calls, 15,488 tokens, and 224,219 ms while direct used two calls, 2,369 tokens,
and 11,419 ms. That result is a diagnosis of the old staged pipeline, not a win.

The harness now uses the current one-call deliberator plus one-call conclusion
checker, with the same 1,800 output-token ceiling as direct. Retries and repair
share a hard 60-second deadline per fused capability. A post-change pinned run
returned no text content before completing a pair and failed closed within the
two-stage deadline envelope. The relevant artifacts are:

- `evals/chapter_13c/live_outcome_runs/2026-08-22/122334-02dec531/blocked.json`
- `evals/chapter_13c/live_outcome_runs/2026-08-22/122617-3535a3e7/summary.json`
- `evals/chapter_13c/live_outcome_runs/2026-08-22/124324-3535a3e7/blocked.json`

Complete the gate only after a model route demonstrates stable structured
capacity for all 18 comparison pairs. Do not count provider failures or the
pre-fusion diagnostic as PolyaBrain evidence.

## 2026-08-22 Stable-Route Qualification

A strict-routing diagnostic found that OpenRouter endpoint metadata currently
advertises the portable completion limit as `max_tokens`. Sending
`max_completion_tokens` with `require_parameters=true` eliminated all eligible
`google/gemini-3.7-flash` endpoints and returned HTTP 404. The adapter now uses
the metadata-compatible field; strict JSON routing then completed both the
named pagination smoke and all six category pairs.

Artifact:
`evals/chapter_13c/live_outcome_runs/2026-08-22/133131-16a8dce2/summary.json`

| Metric | Polya | Direct |
|---|---:|---:|
| Passed | 6/6 | 6/6 |
| Total tokens | 32,725 | 14,945 |
| Mean latency | 8,933 ms | 5,101 ms |
| Recovery-case model calls | 2 | 3 |
| Unsupported forced conclusions | 0 | 0 |

The run qualifies the route and confirms the fused loop works across all six
categories, but it fails the product-value gate: there is no correctness
advantage, and Polya uses about 2.19 times the tokens and 1.75 times the
latency. Three repetitions would add cost without resolving that structural
finding, so the 18-pair gate should not be run unchanged.

The next evaluation revision must add adversarial evidence conditions with real
headroom: contradictory sources, stale versus current authority, prompt
injection in retrieved content, missing evidence requiring safe refusal,
ambiguous user-owned constraints, multi-source corroboration, and tool failure
recovery. The next runtime revision must also avoid semantic deliberation when
an independently attested deterministic tool result already covers every
success criterion. Do not weaken scoring or add benchmark-only shortcuts.

Chapter 13-I then implemented the first safe evidence-closure mechanism and
reran all 18 balanced pairs. Polya completed 18/18 with zero model calls and
zero tokens; direct completed 17/18 using 47,656 tokens. Mean latency was 3.38
ms versus 5,158 ms. Both conditions received the same attestation fields, and
negative tests reject forged or incomplete bindings. Artifact:
`evals/chapter_13c/live_outcome_runs/2026-08-22/134337-16a8dce2/summary.json`.

The predeclared general gate still fails because the 5.56-point correctness
advantage is below 10 points. Treat this only as a narrow compute win for known
deterministic evidence contracts. Adversarial evidence cases and blinded review
remain required for a broader product-value claim.

Chapter 13-J then added a separate adversarial epistemic-control track with
paired answerable and intentionally unanswerable tasks. Across 24 rotated
same-model/same-observation pairs, both Polya and direct passed 24/24. Polya
used 24 model calls and 70,613 tokens versus 69 calls and 103,583 tokens, with
4,156 ms versus 7,737 ms mean latency and equal 45 external calls. Answer
accuracy and abstention precision/recall were all 100%; unsupported conclusions
and forbidden-output hits were zero. Artifact:
`evals/chapter_13j/live_runs/2026-08-22/141629-16a8dce2/summary.json`.

The Chapter 13-J automated gate passes as a narrow synthetic quality-adjusted
compute result. It does not turn the older Chapter 13-C general superiority gate
green. The condition-blinded packet exists, but independent review and
non-synthetic field cases remain pending; product-value claim readiness is
therefore still false.
