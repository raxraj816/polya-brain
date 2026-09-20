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

## Production-path dependency investigation regressions (Chapter 13-P)

Freeze the task and complete artifacts before running the public Investigator CLI
and a direct same-model baseline. Score outcome facts independently of the
runtime's own `passed` flag. Include direct upper bounds, installed parent pins,
multiple fixed release branches, optional/environment-conditional dependencies,
no listed fix, duplicate IDs, and transitive alias groups. Keep ambiguous,
malformed and partial-source controls, and test copied facts with contradictory
prose so necessary coverage is never mislabeled semantic verification.

Retain each failed run; fixes invalidate its use as a held-out case. Fresh
synthetic transfer cases are useful regression evidence but are not independent
blind evaluation, learned procedure transfer, or real-user product preference.

## Core-loop efficiency and recovery regressions (Chapter 13-P)

Compare the unchanged runtime with a direct same-model answer on a frozen
non-dependency incident case. Check observation/inference separation, competing
causes, whether a proposed infrastructure purchase is justified, reversible
experiments, residual uncertainty and unperformed-action boundaries. Record
source-review limitations and actual tokens/latency, including baseline strengths.

Prompt compression must preserve mode overrides, clarification boundaries and
wrong-cause warnings across all ten framing fixtures. These examples appear in
the prompts and therefore measure compatibility, not held-out quality. Keep
failed prompt candidates and distinguish input savings from whole-run savings.
Execution-negative cases must not pass from metadata alone; if recovery clears a
failed verification and then stops, both report paths must retain its explicitly
historical diagnostics without promoting them to a current verdict.

## Knowledge-on-demand public-runtime checks (Chapter 13-P)

Start scientific and technical investigations with no supplied documents. Require
actual public-source acquisition, independently inspect the retrieved excerpts,
and distinguish observation from inference and a proposed experiment from an
executed one. Preserve failed attempts before fixes; subsequent replays are
regressions, not held-out wins. Record model-backed search as both model and external
usage, and report unknown usage rather than inventing zero cost after failures.

Negative controls include missing citation excerpts, invalid search telemetry,
provider timeout, CAPTCHA-only pages, ungrounded extracted claims, unavailable
sources, privacy constraints and exhausted budgets. Multiple pages from one host
must not manufacture independent corroboration. Grouped questions cannot resolve
from evidence for only their first question. Official-source reporting does not
establish broad causal or cross-domain validity. A full product claim still needs
fresh comparisons, learned procedure transfer and repeat use by real users.


Scope-recovery evaluations must distinguish an explanation plus proposed diagnostic
from a request to prove an actual incident cause or perform a fix. Test incomplete,
duplicate and invented question identifiers, missing source support, invalid user
scope references, partial deferral, retained uncertainty in both report paths and
invalidation of prior verification. A model's selection of a real user quote is
provenance, not independent proof that the selected fact is nonblocking.

Page-reading checks must start with a discovered source, select useful material
beyond the initial snippet, stage it without admitting it, and record actual read
usage alongside search/model usage. Exercise private and mixed DNS answers,
connection pinning and TLS host retention, redirects, non-text content, decoded
response limits, total deadlines, repeat URLs, candidate exhaustion, privacy and
offline composition. Different excerpts from one page do not create independent
corroboration. Development regressions retain failed attempts; changing a bound or
routing rule after seeing a failure makes the next run a repair, not a held-out win.

### Verification-driven public research recovery

Start with a failed final check after initial research has been marked complete.
Require an actual failed-check-bound research request, separate source admission,
fresh analysis with distinct task IDs, and a new independent verification before
success. Retain prior failures; do not silently accept the old analysis. Test
invalid check indices, passing verdicts with research requests, repeated rounds,
private/execution requirements, unavailable tools, sensitive-data boundaries and
exhausted call budgets. Re-run the unchanged NASA DART task with all previous
failures retained and report model/search/page usage and actual termination.
Model-suggested public-source classification is not itself a correctness gate;
this recovery does not replace observed execution or establish cost advantage.

Retain the DART false pass that rewrote `−33.24 min ± 1.4 s` as
`−33.24 ± 1.4 minutes`. Evaluate the final answer against raw admitted excerpts,
not only model-extracted claims. The time-uncertainty guard must reject this case,
accept exact equivalent conversions, and document unmatched/unparsed quantities
as outside its narrow coverage. A runtime `completed` status alone does not make
a development result correct.
