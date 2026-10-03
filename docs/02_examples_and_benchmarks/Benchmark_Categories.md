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

### Residual research and source selection

Exercise supported + still-needed groups with no deferral: retire the original
group, retain source provenance for supported facts and keep all remaining
questions in one unfilled group. Invalid quotations remain blocking. Preserve
criteria and constraints; an all-needed review must not claim progress. Verify
that only query/read guidance crosses parent lineage, with newer child guidance
taking precedence. Discovery hints must avoid page reads, admitted nominations
must select only eligible untried pages, and invented/rejected nominations must
fall back to search. Test passage targeting and model/external-call accounting.
Re-run unchanged DART and HTTP tasks with all attempts and costs retained. These
are development regressions, not fresh comparisons or general cost evidence.

Retain both HTTP failures where targeted-query publisher identifiers displaced
GET/PUT passages. Explicit numbered sections must outrank publisher/front matter
without increasing the six-passage/9,000-character limit. Preserve the original
user's requested-topic coverage; test a synthetic non-HTTP section inventory.
Retain the persisted DART failure from a generated U+0000 claim. Trace JSONB and
accepted-claim persistence must retain a visible escape and unchanged source text,
without inventing a sign or treating malformed text as new measurement evidence.

Test that unnumbered front matter does not consume a numbered-heading bonus.
Retain the HTTP finalization failure that demanded a pre-existing final answer.
Replay its admitted evidence and analysis without supplying an answer: the final
checker must compose a supported explanation while a matched actual-execution
negative probe still fails. These frozen live-model probes supplement deterministic
regressions; they do not prove arbitrary prompt compliance or held-out success.

Latest development outcome: DART completed in the CLI but still stalled in the
persisted workbench. HTTP completed after the composition repair; manual review
found a section-9.3.1 citation whose supporting selected passage was section 6.4.1.
Preserve this citation-fidelity defect instead of equating runtime status with
independent correctness. Full-run costs and failed attempts remain in the ledger.

The saved source-final workbench DART run exhausted three external calls before
asking for public information. Preserve that historical failure. For the bounded
termination repair, test exhausted and zero acquisition budgets, available search,
affordable alternative memory/inspection, private and mixed gaps, and unavailable
providers. A stop must retain evidence, costs and failed checks, avoid a fabricated
clarification or reusable success, and explain the acquisition limit in CLI and
persisted reports. Reject stale/malformed stop guidance. These deterministic
controls establish truthful termination only; the full DART outcome and fresh
source-selection quality remain unproven.

### Candidate repair transfer (Chapter 13-P)

Freeze the two supplied fictional protocol families in
`evals/chapter_13p/repair_transfer/cases.json` before live execution. Run first
encounter, related changed-code cold, related changed-code warm and incompatible
warm conditions. Cold uses the same production one-call proposal path and
sandbox/check access. Warm receives only the serialized lesson learned from the
first completed run. It must propose no new model call when exact reuse applies,
but must rerun the present baseline and candidate checks. Record initial learning
cost, transfer cost, tokens, time, lesson bytes, unchanged host source and every
failure. A wrong transfer must have an explicit deterministic failed verdict.

These are author-created development cases, not independent held-out evidence.
Changed function names, inputs and surrounding guards leave the intended exact
edit fragment intact; parameter renaming and general program transformation are
outside the experiment. Real PostgreSQL API tests additionally verify owner
isolation, persistence and reuse across separate source/check sessions.

Recovery follow-up: replay the same incompatible ORBIT-R18 and MERIDIAN-D cases
with their previously serialized lessons. Require a failed recalled edit followed
by a distinct successful candidate using the unchanged source/check snapshots.
Count both sandbox attempts and the one proposal-model request; keep the original
failed verdict and plan in the trace. Validate current-candidate reporting, diff
export and learning through the real persisted API. Negative tests cover no model,
exhausted budgets, vacuous checks, repeated or equivalent edits, a second failing
candidate, stale task IDs, changed bindings, forged history and injected verdicts.
The successful known-case replays are recorded separately in
`evals/chapter_13p/repair_transfer/recovery-results.json`; they do not relabel old
failures or establish held-out reliability.

Structural follow-up: `repair_transfer/structural-cases.json` freezes billing,
inclusive-threshold and two-required-flag tasks before implementation. Compare
first learning, cold transfer, prior exact-memory transfer, and expression-adapted
transfer after changing names and statement context. Preserve the same independent
checks and run incompatible-rule variants. Count initial learning separately from
reuse and retain all runs in `structural-results.json`. Reject unsupported calls,
attributes, indexing, introduced names/bindings, inconsistent name substitutions,
literal type/value changes, duplicate text, ambiguous sites and resource overflow.
Check precedence and Unicode spans plus persisted API reuse. These are new
author-created development families, not independently held-out comparisons.

### Coding execution acceptance regressions (Chapter 13-P)

Generated-check regressions must reject unsourced literal outputs, preserve
explicit user values and exact prior checks, and screen repaired proposals again.
Test numeric-prefix and string-content mismatches so similar-looking examples
cannot supply false provenance. A dynamic reference passing this static screen is
not certified: execute checks against wrong implementations and wrong oracles,
and retain independent semantic review. False single-expression tests must fail.
Recovery planning must work with a last affordable provider attempt without
bypassing output budgets, retries, privacy or checkpoint limits.

The frozen `fresh-graph-cases.json` task tests finite/infinite walk counting with
irrelevant cycles, parallel edges, self-loops and an empty walk. Its independent
oracle uses transitive closure and bounded-length walk counting on 600 seeded
multigraphs, plus boundary/scale checks. Validate that oracle against a separate
linear implementation and targeted mutants before the first model run. Report
these as developer checks, not an independent benchmark or external judge.

Code-reference delivery must preserve independent review, reject stale/altered
execution bindings, retain all active implementations and expand only complete
unique references. Test both full-code and reference responses through actual
Docker recovery. Preserve raw provider responses separately from assembled final
artifacts. Report output-copy reduction separately from total token/latency changes.
The signed-array `transfer-cases.json` task adds an untouched problem family with
3,000 brute-force oracle comparisons plus boundary and large-input checks. It is
developer-authored, frozen before live attempts, and not an independent holdout.

Run `backend/tests/test_coding_execution.py` for the public runtime coding path.
Negative controls include missing/failed/empty/truncated execution, duplicate
outputs, incorrect complexity claims, changed delivered code, dropped assertions,
invalid replacement references and unrelated failed tasks. Passing local tests
must still invoke independent semantic review; a failed attempt must not spend
that model call. The real-Docker recovery cases use scripted model responses,
retain the original failed observation and assertions, and deliver the exact
corrected code after a fresh run. They test orchestration, not model reasoning.

Historical selected coding runs and one-call direct answers remain development
evidence. They are not a matched, repeated, held-out superiority experiment.
In particular, the old interval case changed its test oracle and predates the
current recovery contract; do not treat its status as current-contract acceptance.

Evaluator audit: `coding_execution/historical-audit.json` replays the historical
delivered implementations in Docker and applies current recovery requirements.
All three code implementations pass the developer checks, but the interval run
fails current execution acceptance. Historical direct answers are not replayable
because their source artifacts were omitted. A missing artifact is unverified,
not demonstrated incorrect. The median problem prompts also differ. New direct
runs preserve full artifacts and checkpoint attempted/finished cases without
overwriting earlier runs. `test_coding_eval_evidence.py` includes false-completion,
ambiguous-code, duplicate-case, artifact-binding and interruption controls.

Matched-access follow-up: `coding_execution/matched-cases.json` freezes one new
calendar-intersection case with half-open endpoints, touching/overlapping windows,
negative times, immutability and sparse large coordinates. `matched.py` compares
the public runtime with a lean model/sandbox feedback loop under common outer
call, output-token, time and execution ceilings. Both see exactly the same task;
neither sees the independent checks until solving ends. Alternate arm order and
retain every attempt, including harness failures. The common outcome is delivered
code passing the developer checks; additional runtime acceptance is separate.
This is a repeated development pilot, not independent held-out or market proof.

The v4 scheduling failure becomes a regression in `test_bounded_verification.py`:
three of six calls already spent must still permit independent review. Also test
one remaining call, malformed output, transient retries, fallback routes, an
exhausted output allowance, checkpoint admission and sensitive data rejection.
Successful review remains necessary; an unreviewed candidate cannot count as a
completed outcome. Keep the frozen pilot's common limits unchanged for live reruns.

Source-edit recovery uses `evals/chapter_13p/source_recovery/case.json`: a new
retry-deadline fixture with an explicitly injected incomplete first proposal.
The public runtime must observe its failure, propose a different source-only edit,
rerun the original immutable check, preserve the failed verdict and pass 3,000
independent randomized deadline comparisons withheld from the model. Report the
injected response separately from real provider calls/tokens. Original code and
the injected partial fix are mandatory negative controls. This is a controlled
recovery experiment, not autonomous initial diagnosis or a competitive benchmark.

### Compact-interface cost check

Replay saved gateway responses without provider calls to compare message bytes
at the same state and response. Include initial plus repair requests, preserve
all validation constraints except display titles, and distinguish this mechanical
byte saving from live tokens or outcome improvements. Tests cover null/empty
elision, preserved scalar defaults, exact arbitrary JSON, code/tests, provenance,
failed checks, unchanged caller-supplied projections, and no-evidence status
restrictions in initial and repair responses. Live paired pilots retain the same
model, cases, tools and budgets; every intermediate outcome remains reportable.

Bounded response-edit repair must preserve unmentioned content and revalidate
the complete reconstructed response. Negative controls cover invalid paths,
overlapping edits, index coercion, limits, unsupported hypothesis statuses,
unsourced checks, and exhausted budgets. Test malformed-original full repair and
full-response compatibility. Record repaired paths and hashes without values in
the durable trace. Separate runs that actually apply edits from those that need
no repair; do not attribute the latter's savings to edit application.

The latest signed-array and graph repetitions each complete 2/2 in both arms,
with Polya runtime acceptance and independent checks passing. The separate saved
browser graph run also passes the same 600 random and eight boundary/scale checks.
Measured usage, prior attempts, small-sample limits and browser delivery checks
are recorded in `Chapter_13P_Compact_Model_Interface.md`. All remain developer
evidence; lean still uses fewer tokens and less time on these cases.

### Citation provenance acceptance regressions

Preserve the historical HTTP answer whose RFC section locator was absent from
admitted excerpts. Replay its reconstructed terminal response at the current
conclusion capability with a fake provider: the original wrong section and an
unadmitted-domain control must fail, while a manually corrected locator can
pass the provenance screen. This is acceptance-boundary evidence, not a fresh
model answer, whole-run replay or evidence of semantic entailment.

Test both model verifier adapters, wrong paths/queries, cross-reference-only
sections, missing raw excerpts, encoded fragments, malformed URLs, Markdown
reference/autolinks/tables, code examples, explicit future-link disclaimers and
bounded input failure. Check CLI/API reports, persistence across reload and
suppression of failed-outcome learning. Keep non-HTTP synthetic evidence usable
under the existing semantic review. Record all failures and distinguish these
developer regressions from held-out or real-user evaluations. See
[results and limitations](../03_implementation/Chapter_13P_Citation_Provenance.md).


## Chapter 171 launch-preparation developer comparison

### Public-research recovery classification

Developer regressions must distinguish public-source acquisition failure from
missing user-owned information. Missing registration, failed/inconclusive/blocked
search and privacy refusal must not create a clarification or verified outcome.
Retain evidence, unresolved gaps, usage and failure observations; preserve safe
inspection and genuine private clarification in mixed requests. Untyped wording
does not establish public ownership. Verify terminal guidance through CLI reports,
fresh database reads, browser reload and export. These tests do not establish
semantic support, source-selection quality, held-out success or human usefulness.

### Bounded page-read recovery

Page-recovery developer checks must include a failed document followed by fresh,
evaluated discovery of a distinct source; a serialized-state round trip; stale,
unevaluated, unrelated and page-produced batches; missing/mismatched/legacy attempt
bindings; same-URL and third-read refusal; and shared budget/privacy negatives.
An integration fixture exercises actual search/evaluation/page adapters with fake
providers and exports the unverified report. Count retained failures and all calls.
Acquisition progress does not count as verified resolution or live model quality.

### Matched coding evidence

The frozen six-case matched coding campaign and original failures are documented in
[the readiness evidence package](../03_implementation/Chapter_171_Readiness_Evidence_Package.md).
All cases are known development tasks. Hidden check execution is not equivalent to
held-out tasks or independent human review. The original 5/12 versus 12/12 result
remains part of the record after generated-check repair; post-change results must
be reported separately with aggregate campaign spend. No superiority claim follows.

## Chapter 172: familiar problems with an explicit twist

Real specifications often differ from the textbook version of a problem a model has
memorised: lower median instead of the averaged median, unrestricted rather than
restricted Damerau-Levenshtein, an LRU whose updates do not refresh recency,
closed meeting intervals with cleanup gaps, SemVer identifiers containing hyphens,
observed weekend holidays, toroidal 8-connectivity, ASCII-only digits, hard word
wrapping. A lean loop's own tests tend to share its pattern-matched reading, so
these cases measure whether independent verification catches confident errors.

`evals/verified_coding/heldout-cases.json` holds ten such tasks frozen and hashed
before any solver run (`FREEZE.json`). Withheld checks in `checks.py` are validated
by `validate_checks.py`: an agent-written correct solution must pass and every
realistic mutant must fail. Dev cases live separately in `dev-cases.json`. The
paired runner (`run.py`) scores lean, lean plus self-review, lean plus differential
verification (all from the same first answer) and the kernel. Report corrected
failures, harmed successes, false certifications and cost per arm. Tasks are
agent-authored; independent human tasks remain a separate gate.

### Adversarial verifier controls

The 32 cases in `backend/tests/test_differential_adversarial.py` challenge false
agreement rather than measuring solver capability: boolean/numeric values in
containers and object fields, exception-side input mutation, unordered matching,
truncated iterators, malformed required checks and incomplete sandbox results.
Include valid-equivalence controls to detect false alarms. Both certificate/report
pipelines must expose incomplete evidence as unverified. Preserve before-fix
failures and separate these deterministic developer controls from frozen solver
trials, independent review and real-user value. See
[Chapter 172 hardening](../03_implementation/Chapter_172_Adversarial_Verification.md).

Coverage controls additionally challenge generators that work only on one size,
reference timeouts, unavailable scale inputs and coverage loss after a repair.
Offline QuixBugs replay reuses hash-bound historical generator responses; it is
not a new independent trial. Its 80 expected arm records include five unavailable
historical attempts/responses and three unverified controls. Keep those in every
summary denominator; see [replay evidence](../03_implementation/Chapter_172_Comparison_Coverage.md).
