# Benchmark Categories

This document defines the active mixed-domain benchmark surface for PolyaBrain.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Purpose

PolyaBrain must be tested as a general problem-solving system from Chapter 1. Benchmarks must prove the same core loop works across different problem types without hardcoding the core platform to one domain.

Each benchmark case should include:

- Problem statement.
- Category.
- Difficulty.
- Allowed tools.
- Expected behavior.
- Ground truth or reference answer.
- Expected clarifying questions, when relevant.
- Expected verification checks.
- Scoring rubric.
- Knowledge that is available at run time and knowledge deliberately withheld.
- Model-call, token, acquisition, latency, and normalized-cost budgets.
- Whether the case is a first encounter or a held-out structural transfer case.

## On-Demand Learning Track

Maintain an unfamiliar micro-world track in addition to normal real-world
cases. A micro-world supplies a fictional manual, API, rule system, table, or
tool at run time so success cannot be credited to memorized model knowledge.
Cases must require targeted acquisition and at least one verifiable consequence
of the supplied rules.

Compare:

1. A direct model with the same answer budget.
2. A full-context model given every available document.
3. An ordinary retrieve-then-answer baseline.
4. PolyaBrain using gap-driven acquisition and the cognitive resource ledger.

Use paired held-out cases to measure procedural transfer. The second case must
change surface details while preserving only the intended structural procedure;
the evaluator must reject answer memorization and unverifiable shortcuts.

## Executable Verifier Track

Maintain held-out verification checkpoints in which the candidate, mandatory
success criteria, and independent observations are fixed. Compare a direct
model with complete observations, a full-context model, ordinary retrieval, and
PolyaBrain's typed verifier factory. Report verdict correctness, false-pass and
false-reject rate, criterion coverage, calls, tokens, latency, and parsing or
provider failures.

This track isolates verifier value. It must never be reported as end-to-end
problem-solving evidence. A verifier shape learned or compiled on one source
case must be retested on changed surface details, failed criteria, missing
observations, stale capability versions, poisoned memory, and safety-constraint
mismatches before reuse.

## Adaptive Scheduler Track

Maintain held-out task families with prior capability-health histories and a
separate present-case route oracle. Cover healthy, repeatedly degraded,
recovered, and version-changed capabilities. Compare the declared-cost static
controller with the adaptive controller using rotated execution order and at
least five repetitions.

Report verified route outcome, wrong-route rate, external/model calls, tokens,
capability latency, regret relative to the best eligible route, and scheduler
overhead. Test explicitly that sparse failures do not blacklist a capability,
new versions do not inherit stale health, recovery can restore a route, and
fabricated strong performance cannot bypass privacy, approval, or hard budget
gates. Keep this track separate from end-to-end intelligence claims.

## Adversarial Epistemic-Control Track

Maintain paired answerable and intentionally unanswerable cases in which the
runtime receives incomplete, conflicting, stale, misleading, or unavailable
information. Include retrieved prompt injections and false-premise questions.
The same-model baseline must receive the same tools, observations, budgets, and
untrusted-data warning.

Score correct answers and correct abstentions separately. Report abstention
precision and recall, unsupported-conclusion rate, contradiction-resolution
accuracy, temporal-source selection, criterion coverage, prompt-injection
success rate, acquisition non-progress, external/model calls, tokens, latency,
and cost. A system must not improve its score by refusing answerable tasks or
by guessing on unanswerable tasks.

This track isolates evidence governance. It is not by itself proof of broad
end-to-end product value or general intelligence.

## Categories

1. Mathematical reasoning: word problems, optimization, algebra, probability, and constraints.
2. Logic and puzzle solving: deduction, contradiction detection, and grid-style reasoning.
3. Technical research: current APIs, libraries, papers, standards, and evolving technology questions.
4. Software debugging: codebase investigation, failing tests, root-cause analysis, and patch planning.
5. Algorithmic problem solving and coding contests: LeetCode, HackerRank, Codeforces, and Advent of Code-style problems.
6. Data analysis: CSV/table interpretation, anomaly explanation, comparison, and segmentation.
7. Planning and strategy: project planning, tradeoff analysis, and implementation sequencing.
8. Scientific/engineering reasoning: hypothesis generation, experiment design, and evidence evaluation.
9. Ambiguous or underspecified problems: cases where the correct behavior is to ask clarifying questions.
10. Adversarial or misleading problems: cases with false assumptions, bad evidence, or contradictions.
11. Open-ended creative synthesis: generate several possible approaches, use analogies or reframes when useful, and verify feasibility.

## Scoring Dimensions

- Outcome correctness.
- Problem framing quality.
- Approach selection quality.
- Constraint handling.
- Knowledge gap quality.
- Evidence quality.
- Hypothesis diversity before ranking.
- Analogical transfer quality.
- Reframe quality when the initial problem construction is weak.
- Tool selection quality.
- Mode-specific verification checklist completeness.
- Correct clarification or abstention behavior.
- Report usefulness.
- Latency.
- Estimated cost.
- Model calls and tokens by logical stage.
- External acquisitions and irrelevant context consumed.
- Expected verified progress per cost for selected actions.
- First-encounter versus transfer-case efficiency.

## Chapter 60 Minimum

- At least 30 evaluation cases run automatically.
- At least one full end-to-end case succeeds in math, research, debugging, data analysis, planning, and ambiguous input.
- At least 20 general reasoning smoke cases run through the same core loop.
- Every answer includes evidence, checks, confidence, and open questions.
- Open-ended creative synthesis cases must show divergent candidates, convergent filtering, and verification of the selected path.

## Chapter 90 Minimum

- At least 100 synthetic and curated scenarios across benchmark categories.
- At least 70% correct or usefully verified outcome on solvable cases.
- At least 90% correct clarification or escalation behavior on underspecified cases.
- At least 90% reports include required audit sections.
- At least 80% of creative synthesis cases include a useful alternative, analogy, or reframe that is explicitly accepted, rejected, or deferred with evidence.

## Guardrail

Do not optimize only for impressive demos. Benchmark repeatability is a product requirement.


## Mode-delivery regression expectations

API/user overrides must be preserved in problem representation and downstream
capability context. Compare cases must identify explicit alternatives and shared
criteria; missing comparative evidence must prevent an unsupported winner.
Review cases must distinguish confirmed defects from unresolved risks and state
acceptance checks. Investigation cases must distinguish observed symptoms from
unverified causes and seek discriminating evidence. Mode labels and successful
arithmetic wiring tests do not count as substantive mode-quality evidence.
Chapter 62 adds transport/prompt-context regression checks; fresh verified
Compare/Review tasks remain part of the product-value evaluation gate.
