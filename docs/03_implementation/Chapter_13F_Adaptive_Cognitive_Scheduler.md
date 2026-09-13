# Chapter 13-F: Adaptive Cognitive Scheduler and Capability Health

Status: complete in the current working tree.

## Problem

The Chapter 13-D controller ranks actions using declared cost, expected
usefulness, risk, budget, and current-run failure history. Those inputs are
necessary but incomplete. The Chapter 13-E premium-model evaluation observed
HTTP 404 strict-routing failures, provider unavailability, empty final content,
multi-second median latency, and long-tail responses above 30 seconds. Static
metadata cannot represent that changing operational reality.

PolyaBrain should learn capability health without confusing speed with
intelligence. A fast wrong answer loses. A slow or temporarily unavailable model
may remain the only eligible semantic capability. Performance evidence may
adjust ranking only after permission, privacy, hard budget, applicability,
provenance, and present-case verification boundaries remain intact.

## Experimental Mechanism

The implemented scheduler layer:

1. Measure duration at the capability registry boundary.
2. Derive bounded samples from decisions, observations, resource events, and
   final verified status.
3. Maintain version-scoped profiles for operational reliability, verified
   yield, latency, calls, tokens, and normalized cost.
4. Blend empirical estimates with conservative priors according to sample
   confidence.
5. Adjust expected verified progress and effective marginal cost within strict
   bounds.
6. Expose every adjustment in the decision trace.

The first ledger is in-process and bounded. Durable tenant-aware performance
memory remains a promotion gate, not an excuse to add a premature database
contract.

## Safety Invariants

- Performance cannot make an unavailable or unsupported capability eligible.
- Performance cannot override approval, risk, sensitive-data, or budget gates.
- Operational success is separate from verified-outcome contribution.
- A model or tool version starts a new profile.
- One sample has low influence and cannot permanently blacklist a capability.
- The present task is still verified independently after any adaptive route.

## Evaluation Gate

Use repeated held-out cases with rotated capability conditions: healthy,
degraded, recovered, and version-changed. Compare the current static controller
with the adaptive policy on verified outcome, wrong-route rate, calls, tokens,
latency, recovery, regret, and scheduler overhead. Do not claim a scheduler win
from a handcrafted single selection.

## Implemented Boundary

- `CapabilityPerformanceLedger` derives bounded samples from kernel traces and
  keys profiles by task family, action type, capability name, and capability
  version.
- Beta-smoothed operational reliability and verified yield are blended by
  sample confidence. Progress multipliers cannot fall below `0.35`, and added
  empirical cost cannot exceed `2.0`.
- Declared call reservations are not charged twice; only calls above the
  declaration add an empirical call penalty.
- The controller applies the adaptive estimate only after availability,
  repeated-current-run-failure, hard-budget, and sensitive-data checks.
- Selected and lower-ranked candidates expose sample count, confidence,
  progress multiplier, cost adjustment, and policy version in the decision
  rationale.
- Kernel and governed-procedure capability observations now include measured
  duration. The production FastAPI process shares one bounded in-process
  ledger across session runners.
- Model-backed capability versions include a non-secret fingerprint of the
  configured model route, so changing from an auto route to a pinned model does
  not inherit stale health evidence.

The contracts remain experimental and outside canonical `PolyaState`. The
ledger is not yet durable or tenant-aware, and its coarse outcome attribution
credits successful actions on a completed verified run rather than claiming
causal credit for each action.

## Evidence

The deterministic held-out scheduler benchmark contains 12 distinct task
families, covers healthy, degraded, recovered, and version-changed regimes,
rotates static/adaptive execution order, and repeats each case five times.

Artifact:
`evals/chapter_13f/results/2026-08-22/121908/summary.json`

| Metric | Static | Adaptive |
|---|---:|---:|
| Held-out decisions | 60 | 60 |
| Verified route outcomes | 45/60 | 60/60 |
| Wrong routes | 15 | 0 |
| External calls | 60 | 45 |
| Tokens | 121,500 | 112,500 |
| Modeled capability latency | 160,500 ms | 43,200 ms |
| Route regret | 267,300 ms | 0 ms |
| Mean scheduler overhead | 0.035 ms | 0.077 ms |

The gate passes for this scheduler-specific deterministic benchmark. It does
not establish end-to-end problem-solving or general-intelligence superiority.
