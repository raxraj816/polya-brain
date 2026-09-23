# Chapter 13-D: On-Demand Task Learning and Compute Efficiency

Status: implementation proof and narrow exact-lookup outcome gate complete;
general problem-solving outcome gate open.

## Implemented Product Loop

The production cognitive composition now supports:

```text
raw problem
  -> deterministic or model task construction
  -> trace-derived task model and current impasse
  -> deterministic explicit-gap construction
  -> expected verified progress / cost action selection
  -> memory, artifact, web, tool, model, or human capability
  -> evidence admission
  -> deterministic procedure or fused semantic deliberation
  -> independent deterministic or semantic verification
  -> verified reflection and procedural consolidation
  -> report or truthful insufficient-evidence stop
```

The temporary task model is an audit projection of canonical `PolyaState`; it
does not create a competing state store. Every controller cycle records the
goal, current impasse, counts of knowns/unknowns/constraints/gaps/evidence,
pending work, verification state, budget, and accumulated usage.

## Compute Controls

- Explicit unknowns become gaps deterministically.
- Capability metadata declares deterministic, model, external, memory, or
  human execution kind plus worst-case model/external-call reservations.
- The controller rejects actions that cannot fit the remaining hard run budget.
- Every observation records model calls, external calls, tokens, and normalized
  cost. Failed model capabilities consume their conservative reservation.
- Compatible hypothesis generation, planning, and state-only analysis share
  one semantic call. Verification and reflection share a separate call only
  after checks pass.
- Exact explicit-artifact lookup uses a narrow deterministic pack only when one
  admitted local claim matches its excerpt and provenance. Complex debugging,
  analysis, comparison, review, and “why/how” requests cannot use this pack.

## Verification Evidence

On 2026-08-22:

1. The final full offline test suite passed: 284 passed and 23 skipped. Ruff
   lint/format and strict mypy checks also passed.
2. The unfamiliar micro-world structural proof passed six cases across three
   paired families. Every run was verified and used two simulated semantic
   calls; every transfer case avoided one previously failed public-search step
   while inspecting and verifying new case-specific evidence.
3. The existing premium-model Chapter 13-C equation path was correct but
   inefficient: PolyaBrain used five model calls, 10,963 tokens, and about
   218 seconds; the direct condition used two calls, 2,517 tokens, and about
   5.2 seconds. This is negative product evidence for the old stage-per-call
   design.
4. The fused premium-model post-evidence probe passed with two calls, 5,185
   tokens, and about 19.1 seconds, with hypothesis, plan, analytic output,
   verification, reflection, and task-model trace.
5. The first raw production attempt failed safely at generic representation
   after provider retries. The second exposed and led to a fix for synchronized
   gap/unknown resolution. The model-backed deliberation then failed safely on
   provider output.
6. After promoting the exact artifact procedure to deterministic cognition, the
   raw fictional-manual run completed from input to verified report with zero
   model calls, zero tokens, and about 2 milliseconds. It inspected the named
   file, admitted the exact Z7.4 claim, verified claim/excerpt/provenance, and
   returned the value 37.
7. The live four-condition unfamiliar-corpus benchmark completed 18 case-runs
   (six cases, three repetitions, rotated order) with the configured
   `deepseek/deepseek-v4-flash-0731` endpoint. Polya passed 18/18 with explicit
   verification, zero unsupported conclusions, zero model calls, and zero
   tokens. Full-context passed 17/18 using 23,933 aggregate tokens; ordinary
   retrieval passed 16/18 using 15,057 tokens. Closed-book direct appropriately
   abstained on all fictional cases. Median latency was about 3.1 ms for Polya,
   4.6 seconds for full context, and 8.6 seconds for ordinary retrieval. The
   narrow gate passed; `general_intelligence_win_claimed` remained false.

## What This Does Not Prove

The zero-call result is a known-procedure case, not general intelligence. The
passing live gate covers exact fictional fact lookups with one strong local
claim and a known deterministic verification procedure. PolyaBrain has not yet
demonstrated a superior quality-cost frontier on broader held-out investigation,
planning, debugging, scientific reasoning, or open-ended tasks.

## Remaining Scientific Gate

- Expand the repeated live four-condition design beyond exact lookup into
  unfamiliar multi-rule deduction, debugging, planning, and scientific tasks.
- Use the same underlying model and capabilities where the condition permits.
- Report outcome correctness, provenance, unsupported conclusions,
  verification catches, calls, tokens, latency, acquisitions, and cost.
- Blind the condition labels for human usefulness review.
- Require verified transfer to reduce work without lowering held-out quality.
- Make no “winner” claim until those results pass the master-plan thresholds.
