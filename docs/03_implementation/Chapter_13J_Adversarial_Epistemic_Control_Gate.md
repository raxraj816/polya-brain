# Chapter 13-J: Adversarial Epistemic Control Gate

Status: complete in the current working tree for the first synthetic automated
gate. Blinded human review and non-synthetic field evaluation remain pending.

## Problem

Polya can already close an exact trusted procedure with zero model calls and
can evaluate ordinary acquired candidates for provenance, independence,
freshness, relevance, and obvious contradiction. The loop still lacks an
explicit representation of the evidence that remains necessary after an
evaluation. As a result, a successful search that does not resolve the gap can
be mistaken for useful progress, and the next search can repeat the same
strategy.

The capability to retrieve information is not the intelligence layer. The
intelligence layer is deciding:

- whether current evidence is sufficient for the declared outcome;
- which observation would reduce the remaining uncertainty;
- whether a new source is genuinely independent and current;
- whether conflict is resolved or merely hidden by source order;
- whether external content is evidence or an attempted instruction; and
- when bounded acquisition has failed and the only truthful result is
  insufficient evidence.

## Research Basis

- BrowseComp shows that difficult web discovery needs strategic persistence,
  but its reported accuracy also scales with test-time compute. Polya must
  measure useful verified progress per unit of compute, not browsing volume.
- CRAG reports that straightforward retrieval still leaves a large gap to
  trustworthy question answering, especially for dynamic and complex facts.
- AgentDojo demonstrates that tool-returned content can carry indirect prompt
  injections, so retrieved text must remain untrusted data below the policy
  boundary.
- CONFACT and RAMDocs expose the weakness of retrieval systems under conflicting
  evidence and varying source credibility.
- GAIA motivates tool-using, real-world, human-simple tasks, while FalseQA and
  abstention-focused RAG work motivate explicit false-premise detection and
  correct non-answering.

These sources shape the benchmark; none is treated as proof that one published
architecture is sufficient for Polya.

Primary references:

- <https://openai.com/index/browsecomp/>
- <https://arxiv.org/abs/2406.04744>
- <https://arxiv.org/abs/2406.13352>
- <https://arxiv.org/abs/2505.17762>
- <https://arxiv.org/abs/2504.13079>
- <https://arxiv.org/abs/2311.12983>
- <https://arxiv.org/abs/2307.02394>
- <https://arxiv.org/abs/2603.06198>

## Experimental Boundary

The first mechanism remains outside canonical `PolyaState`. A trace-derived
epistemic requirement and status is produced from the active gap, success
criteria, admitted evidence, evidence-evaluation events, and acquisition
history. The controller and evaluator consume that derived status; the trace
records why the next action or safe stop was selected.

The mechanism may guide search wording and source selection. It may not declare
a semantic claim true, promote raw search results directly into evidence, or
bypass present-case verification.

## Adversarial Cases

The gate must include at least:

1. Every declared acquisition route fails.
2. Evidence covers only part of a multi-criterion outcome.
3. Independent sources make incompatible claims.
4. A stale source conflicts with a current authoritative source.
5. A relevant excerpt includes an instruction to ignore policy or provenance.
6. One source is insufficient where independent corroboration is required.
7. A question contains a false premise.
8. A control case is fully answerable so over-abstention is penalized.

Each case declares its expected terminal status, required and forbidden source
properties, acceptable answer terms where an answer exists, and explicit
evidence or action requirements. Answers and case IDs must never be embedded in
controller logic.

## Metrics and Gate

Report separately:

- answer accuracy on answerable cases;
- abstention precision and recall on unanswerable cases;
- unsupported forced conclusions;
- contradiction-resolution accuracy;
- temporal and authority selection;
- success-criterion coverage;
- prompt-injection policy violations;
- repeated unchanged acquisition after evaluated non-progress;
- model calls, tokens, external calls, latency, and normalized cost.

Run at least three repetitions with rotated condition order against a direct
same-model baseline. A product-value claim requires all safety invariants, no
loss on answerable controls, and a predeclared improvement in quality-adjusted
epistemic outcome. Failure must be recorded as evidence, not explained away.

## Implemented

- A deterministic trace-derived requirement records minimum independent
  sources, temporal need, authority need, current success criteria, and the
  active target without changing canonical state.
- A residual status distinguishes initial evidence, corroboration, current
  authority, conflict resolution, discriminating evidence, and satisfied.
- Search queries change according to that residual need and add a materially
  different source strategy after repeated evaluated non-progress.
- Evidence evaluation accumulates current supporting and authoritative source
  keys across separate batches instead of requiring same-batch discovery.
- Contradictions persist across later empty or duplicate batches until the gap
  is actually resolved; source order cannot erase them.
- An explicit authority gate prevents agreeing low-authority sources from
  resolving an official-source requirement.
- Conflict and corroboration compare admitted extracted claims, while the raw
  excerpt remains visible for audit. This prevents instructions or decoy
  numbers elsewhere in an excerpt from masquerading as the factual claim.
- All model-backed cognitive capabilities retain the shared untrusted-state
  instruction boundary, and the deterministic controller cannot acquire a tool
  name from retrieved text.
- The same-model harness separates answer accuracy from abstention precision
  and recall, rotates condition order, enforces equal search/model/token
  budgets, and generates a condition-blinded review packet with a separate key.

## Qualification Audit

The first one-repetition pilot exposed real defects: an unnamed benchmark API,
raw-excerpt rather than claim-level contradiction comparison, an undersized
candidate budget that blocked empty recovery searches, and an overly literal
false-premise term matcher. These were corrected at their respective benchmark,
runtime, budget, and scoring layers before the predeclared repeated gate. The
pilot is retained under `evals/chapter_13j/live_runs/2026-08-22/` and is not
reported as passing evidence.

## Verification

Repeated live artifact:
`evals/chapter_13j/live_runs/2026-08-22/141629-16a8dce2/summary.json`

| Metric | Polya | Direct |
|---|---:|---:|
| Passed | 24/24 | 24/24 |
| Answer accuracy | 100% | 100% |
| Abstention precision / recall | 100% / 100% | 100% / 100% |
| Model calls | 24 | 69 |
| Total tokens | 70,613 | 103,583 |
| Mean latency | 4,156 ms | 7,737 ms |
| External calls | 45 | 45 |
| Unsupported forced conclusions | 0 | 0 |
| Forbidden-output hits | 0 | 0 |

Relative to direct, Polya used 65.2% fewer model calls, 31.8% fewer tokens, and
46.3% less mean latency at equal automatic outcome quality. It used zero model
calls on conflict, stale-only, low-authority-only, and all-search-failed cases;
semantic calls were reserved for supported synthesis or explicit partial-
criterion verification.

The predeclared automated gate passed. The run still records
`product_value_claim_ready: false`: the evidence environment is synthetic and
the generated 24-pair condition-blinded packet has not yet received independent
human review.

Repository-wide regression verification after the epistemic-control change and
the closed-corpus source-substrate compatibility correction passes 356 tests,
with 23 integration tests skipped. Repository Ruff, formatting over 161 Python
files, strict mypy over 103 application source files, focused mypy over both
Chapter 13-J evaluation programs, and `git diff --check` also pass.

## Bounded Claim

This chapter shows a quality-adjusted compute advantage for bounded evidence
governance over one direct same-model baseline on eight synthetic case types.
It does not show a correctness advantage, validate open-web sources, compare
against every competing product, establish broad end-to-end product value, or
prove general intelligence or fitness to govern people or the world.
