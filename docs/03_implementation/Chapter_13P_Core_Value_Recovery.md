# Chapter 13-P: Core investigation value recovery

Status: **product-value gate open**. Further AWS deployment and account-flow work
is paused while the production Investigator path is repaired and evaluated.

## What must win

The Cognitive Runtime must turn a difficult technical objective into an actionable,
evidence-grounded outcome with explicit checks and less total user effort. The
initial product is Investigator. Architecture, test counts, authentication, and
completed feature chapters do not establish demand or an advantage over a direct
model answer. Verified reusable procedures must later improve new investigations;
repeat use by real users remains a required product signal.

## Real production-path failure

The dogfood task uses this repository's actual dependency scan, declared package
constraints, and installed transitive requirements. It requests affected packages,
advisory deduplication, blocking upper bounds, proposed compatible changes, and
remaining verification. It explicitly forbids claiming that remediation was run.

Inputs and hashes are frozen locally under
`runs/core-value/dependency-remediation/`. Each attempted run has its own output
directory. The inputs are not added to source control, and this task is not an
independent blind benchmark. Do not report its repaired result as a held-out win.

The original public CLI run returned `needs_input` in approximately 0.02 seconds,
with zero model calls, evidence items, or checks. It asked for information already
supplied as files. Subsequent attempts exposed additional failures rather than
proving completion:

- Multi-file synthesis had been misclassified as deterministic single-file lookup.
- Substring routing treated `compatible` as `table`, JSON as a numerical question,
  and user-directory path text as a reason to request human input.
- Framing responses exhausted a short output allowance and failed schema parsing.
- Artifact inspection stopped at 40 lines and silently cut long excerpts.
- Model abbreviation of source filenames lost the source hints used for routing.
- The fused semantic deliberation still failed its schema or model deadline after
  evidence acquisition. A safe stop is preferable to a fabricated result, but it
  does not fulfill the user's investigation.

## Repairs under test

Single-file lookup now excludes paths from intent detection. Multiple quoted
artifacts retain semantic framing. User-provided artifact references survive model
paraphrasing. Existing typed gaps take precedence in action selection; filenames
and directories cannot supply incidental calculator/measurement/user intent.

Artifact inspection shares a 64,000-character content allowance across explicit
files. Smaller supplied manifests retain a fair allocation; unused space goes to
larger files. Complete files are read when they fit, and omitted content or a cut
line is labeled in the excerpt. URI line ranges describe only displayed lines.
The existing allowed-root, suffix, size and secret-file checks still apply.

Framing is concise with a 3,000-token response allowance. Deliberation requests two
meaningful alternatives and at most two grouped analytic tasks, avoiding repeated
quotations. A semantic attempt can use the existing capability deadline. Shared
run budgets and strict output validation remain in force.

## Provider deadline repair

An isolated deliberation diagnostic with a larger experimental output allowance
returned no model content and was observed running past its declared 90-second
deadline. Increasing output space did not establish a successful repair. That
first experiment alone did not justify a production allowance change. After the
parameter fix below, a new isolated run returned valid analytic findings in one
call: 3,894 output tokens in about 36 seconds. The deliberator response allowance
is therefore 6,000 tokens; the earlier 3,600 ceiling was too small for that result.

The synchronous OpenRouter adapter now runs cancellable asynchronous I/O in an
owned worker and applies one total timeout across connection, response headers,
and body consumption. This prevents a periodically trickling response from
resetting a socket read timeout indefinitely. Tests cover stalled headers and
trickling bodies, response cleanup, no retry after deadline exhaustion, and calls
from both synchronous code and an existing event loop. Local cancellation cannot
prove that remote generation or billing stopped. Usage for the failed diagnostic
is unknown; no completed response was recorded.

## Structured-model compatibility and scope

Pinning the baseline's observed model initially returned a parameter-routing
error. The provider model catalog listed JSON response support but no temperature
support, while every structured runtime request forced temperature. The existing
temperature option is now optional and omitted by default, including repairs.
Explicit numeric requests are still forwarded. Strict JSON and data-policy
requirements remain enabled. See the [provider routing documentation](https://openrouter.ai/docs/guides/routing/provider-selection).

With that fix, the same pinned-model task reached analysis and conclusion checking
in three model calls. The checker then demanded executed remediation even though
the task requested only a proposal and future checks. Framing and checker prompts
now preserve that scope while still rejecting missing facts and unsupported
feasibility claims. Analytic outputs must contain findings rather than only
statements that no external execution occurred.

## Baseline and limits

A direct model received the same task and all three complete files. The first
3,000-output-token answer was truncated. A separately recorded 6,000-token-allowance
answer completed in about 35 seconds, using 10,628 input and 3,061 output tokens,
with provider-reported cost about USD 0.00633. Its observed model was
`openai/gpt-5.6-luna` through the configured OpenRouter route.

That answer is useful but not wholly correct: it calls the scan's 9 underlying
alias groups "9 unique advisory IDs"; the actual scan contains 14 records and 10
unique scanner IDs. It correctly identifies six affected packages and the two
declared upper bounds blocking listed fixes. Neither condition upgraded packages
or ran remediation checks. These are single-run diagnostic observations, not
statistically reliable superiority evidence or a comparison with an actual human
workflow.

## Verification recorded

508 backend tests passed with the isolated Postgres integration database. Ruff,
format checking, and strict mypy passed. Regressions cover public CLI JSON lookup
under a user directory, multi-file lookup rejection, source preservation through
model paraphrasing, path-independent routing, complete late-file coverage, fair
allocation, and truthful truncation provenance. Provider deadline and optional-temperature regressions are included. The subsequent
analysis allowance change passed its relevant capability/adapter tests. The production-path result below is separately reviewed; this test count is not
the product-value gate.

## Latest production-path result: completed, quality gate failed

Using the pinned observed model and the normal 12-call/300-second ceilings, the
public runtime completed in 57.93 seconds with three model calls and 42,444 tokens.
Earlier diagnostic attempts used tighter 6-call/180-second ceilings. The runtime
reported passing verification, but review against the frozen files found:

- It omitted `langgraph<1` as a direct blocking upper bound (`pyproject.toml:18`).
- It said the parent of `httpcore2==2.4.0` was unknown, although
  `installed-constraints.json:2-6` identifies `httpx2` as that parent.
- The model conclusion checker missed these defects and accepted all criteria.

This is a verification false positive, not a product-value win. The result also
used about 3.1 times the direct baseline's tokens and took about 1.66 times as long.
The baseline has its own advisory-ID counting defect. Local `quality-review.json`
and `quality-review.md` preserve both findings; the original run artifacts remain
unchanged.

A separate negative control requested proof that upgrades were installed and tests
passed, while supplying only dependency metadata. It correctly returned
`needs_input` and requested actual installation/test evidence. Scope correction
therefore did not turn that case into an unsupported execution success.

## Remaining runtime limits

The run ledger records observed resources and checks declared capability reserves
before dispatch. Token admission is not yet a strict aggregate retry/fallback
ceiling: the declared output reserve is per response, and input tokens are measured
after provider completion. Failed responses may leave remote token/cost usage
unknown. Do not describe this as a guaranteed token or currency spending cap.
A separate per-attempt aggregate admission repair is required before that claim.

## Required next gates

1. Complete this production-path investigation with a correct, cited result and
   appropriate verification; record actual failures and resource usage.
2. Run fresh technical cases through the unchanged public runtime, including
   inadequate evidence and misleading-input cases. Compare against a direct model
   using equivalent evidence access and record remaining human work.
3. Demonstrate that a verified reusable procedure helps a new case without
   transferring unsupported conclusions.
4. Observe real users bringing a second problem. Deployment is valuable only when
   it enables this proof; further launch polish is not the current priority.

## Source-fact repair and fresh-case findings

The first experimental source-fact check (`dependency_source_facts@0.1.0`) repaired
the omitted direct bound and the falsely unknown exact-pin parent. The preserved
`polya-dependency-remediation-source-facts` run still miscounted scanner identities
while declaring success. Agent source review therefore failed it: 3 calls,
45,689 tokens, 62.10 seconds. The failed output was not replaced.

The next procedure version, `dependency_source_facts@0.2.0`, separately computes
record count, distinct scanner IDs and connected supplied ID/alias groups. In
`polya-dependency-remediation-counted-facts`, the public runtime reports the correct
6 packages, 14 records, 10 scanner IDs and 9 groups, includes both direct bounds,
and names the installed parent of the exact pin. Its proposal remains conditional
on resolution and actual tests. Agent source review found the targeted defects
repaired; this is a development-case result, not independent evaluation. It used
3 calls, 43,628 tokens and 52.39 seconds, still substantially more resources than
the direct baseline.

The procedure reads only complete admitted snapshots. It uses package requirement
and version parsers, preserves markers and optional groups, distinguishes alternative
fixed branches, and exposes source references. A model-proposed pass missing any
required verbatim fact is replaced with failure before its answer or reflection
can enter state. This catches omissions, not every semantic contradiction. Correct
paraphrases without the required block can be rejected. A copied block contradicted
elsewhere in prose still needs independent semantic review; a regression explicitly
records that limit. This hand-built reusable procedure is not learned intelligence.

A new fictional transfer case was frozen before either the direct answer or the
runtime run. It has three packages, four records/three IDs, an old-branch fix that
fits the existing upper bound, an exact installed-parent pin, and an optional
Python-conditional dependency. The unchanged runtime stopped at `needs_input`
after one call (4,746 tokens, 11.15 seconds), while the direct model produced a
useful conditional plan in one call (2,854 tokens, 18.55 seconds).

The trace exposed a separate false conflict: the evaluator compared a bare
`"version": "2.8.1"` line with a different package's `quarrycore==1.9.2` requirement.
Shared digits counted as subject overlap. `source_quality_evaluator@0.3.0` now
requires an anchored matching nonnumeric subject and one comparable numeric value
for numeric conflicts/corroboration. Different entities, unanchored JSON fields,
and multi-value/version-qualified records do not earn those heuristic judgments.
Existing same-subject conflict, cross-batch corroboration, and injection-boundary
checks remain in the regression suite. Missing a heuristic conflict does not prove
that all sources agree. The original transfer failure remains recorded, and that
case is now a regression case rather than held-out evidence.

A subsequent transfer run with the subject fix stopped during framing and requested
Python/extras despite the explicit request for a conditional plan. Framing 1.4.0
now carries those acknowledged conditions in existing given/constraints and future
checks, while retaining actual blocking acquisition in unknowns. The next public
run, `polya-dependency-transfer-conditional-scope`, completed with the correct
alternative-branch comparison, exact-pin parent, counts, and conditional optional
requirement. It used 3 calls, 20,460 tokens and 50.16 seconds. Source review found
the targeted facts correct, but its cost/latency exceeds the direct answer (about
7.2 times the tokens and 2.7 times the time). This is no demonstrated product win.

The same framing was tested again on the execution-negative case: it correctly
returned `needs_input` for actual installation and test evidence, using one call
and 4,445 tokens. None of these tests executed dependency upgrades. The final
coverage/subject regressions also reject ambiguous dual audit collections and
dynamic optional requirements. The check remains narrow and experimental.

Final local validation for this repair: 542 backend tests passed with the isolated
Postgres integration database; Ruff, formatting, strict mypy and diff whitespace
checks passed. No frontend or cloud changes were made in this repair. Fresh
unchanged-runtime comparisons, aggregate resource-budget repair, independently
reviewed outcomes and repeat-use evidence remain open.

## Persisted workbench proof and residual uncertainty

Commit `15c1192` passed both CI workflows (35309479011 and 35309481774). The
conditional transfer task also completed through the frontend proxy and persisted
session service; its report reloaded from Postgres with three evidence records,
eight checks, and the actual runtime trace. Browser inspection confirmed the
visible completed report. The local development frontend had stalled while
compiling and recovered after restarting its existing process; this was not a
backend investigation failure.

That inspection exposed a reporting inconsistency: uncertainty remained in the
conclusion but the dedicated Open questions section contained no entries. The
conclusion capability now supplies bounded optional reporting metadata, recorded
as an answer-bound trace event and consumed by both CLI and persisted reports.
Canonical gaps, confidence and completion rules are unchanged. Legacy runs are
not retroactively rewritten.

A new live persisted run (`1fb08847-91f8-4814-8386-22597eeb7176`) completed with nine
checks and eight recorded residual questions, including target Python/extras,
candidate parent metadata, resolver compatibility and unperformed tests. Browser
inspection confirmed these questions appear in the completed report. This closes
the reporting inconsistency on that integration case; it is not a new independent
quality or efficiency comparison. All 552 backend tests passed with Postgres,
including local/persisted report consistency, invalid and stale metadata, and
suppression of metadata from rejected conclusions. Ruff, formatting and strict
mypy passed.

## Non-dependency case and measured overhead

A fresh fictional gateway incident was frozen before results at `3fc690f`.
Two supplied files describe a worker pool reduced from 64 to 8, stable traffic,
fast database queries, and slow local pool acquisition. The public runtime
challenged the proposed database-capacity purchase, kept the pool-size diagnosis
conditional, compared connection retention/leaks, and proposed a reversible
canary without claiming execution. Agent review found all eight predeclared
expectations covered. This is a synthetic developer-authored case, not independent
or blind evaluation.

The same-model direct answer was also useful and explicitly asked for worker count
and aggregate connection headroom before the experiment. The runtime used three
calls, 17,038 tokens and 58.79 seconds; direct used one call, 2,758 tokens and
37.35 seconds. The runtime therefore did not demonstrate a quality or efficiency
advantage. The original artifacts remain under `runs/core-value/incident-transfer`
and `runs/core-value/polya-incident-transfer`.

A prompt experiment reduced framing from ten examples to three. Across ten paired
live fixture calls, input tokens fell from 36,835 to 19,375, but four mode choices
changed and three cases added clarification stops. Its incident run also took
62.40 seconds despite fewer tokens. That candidate was rejected and preserved.

The adopted narrower serialization keeps all ten examples and all framing rules,
omitting only reconstructible example defaults and JSON whitespace. The semantic
gateway likewise preserves every decoded schema/state value. All ten framing
fixtures retained expected mode, override, clarification and warning behavior;
input tokens were 32,594 (11.5% below the previous prompt), with 2,483 output tokens
versus 2,543 before. The fixtures are in the prompt corpus, so this checks
compatibility, not generalization. Latency did not improve in that fixture sample.

Production-path replays retained the targeted investigation behavior:

| Case | Earlier total tokens / seconds | Compact serialization tokens / seconds |
| --- | --- | --- |
| Gateway incident | 17,038 / 58.79 | 15,453 / 42.55 |
| Conditional dependency transfer | 20,460 / 50.16 | 20,512 / 62.45 |

These are single runs; output length, provider latency, and recovery choices vary.
Do not claim a universal end-to-end saving. Neither result establishes a win over
the direct answer. Smaller prompts do not replace better deterministic checks,
verified procedural transfer, or real-user validation.

## Failure diagnostics across recovery

The execution-negative replay still refused success, but took four calls,
17,758 tokens and 31.98 seconds instead of the earlier one-call clarification.
It inspected the supplied metadata, failed verification for missing installation
and test records, replanned, and stopped after an unsuitable measurement action.
This is a recovery-efficiency defect, not a successful optimization.

It also exposed an audit defect: material replanning correctly cleared stale
verification but erased the failed checks from the final report. The kernel now
records a versioned `verification_invalidated` event before clearing that report.
When no current verification exists, CLI and persisted reports can display the
latest failed report with an explicit "Earlier attempt, before recovery" label.
The historical result cannot establish current success, confidence, reflection,
or learning. A new current verification takes precedence; an invalidated pass or
malformed event cannot supply fallback checks. Older failed runs without such an
event cannot be reconstructed retroactively.

All 561 backend tests passed with Postgres, including kernel re-verification and
historical-diagnostic readback on both report paths. Ruff, formatting and strict
mypy passed. A further live execution-negative run stopped earlier at `needs_input`
and explicitly requested installation output and the full test-suite report.
That live run verifies the refusal boundary, but does not exercise the historical
fallback; deterministic recovery and persistence regressions verify that path.
The extra recovery calls and inappropriate measurement choice remain unresolved.

The subsequent planner repair adds a truthful exit for missing evidence. Its
experimental response chooses either executable tasks or at most three focused
questions. Questions become an existing `human_input_required` blocked observation,
so the kernel pauses without erasing failed verification or claiming progress.
Supplied files and permitted conditions of a proposal must not become redundant
clarification requests.

A live isolated planner test started from a synthetic failed-execution fixture
with executor, measurement and Python execution listed as available. It requested
the actual full-suite command, exit status, result summary and revision, retaining
the failed checks. It used one call, 1,383 tokens and 3.64 seconds. This exercises
the previously unavailable planner exit; it is not a fresh public end-to-end
comparison or proof that every recovery route now makes the right choice. Invalid
mixed/empty branches, maximum questions, kernel resource accounting and the durable
session adapter are covered by regression tests.

Validation after planner recovery: all 569 backend tests passed with Postgres;
Ruff, formatting and strict mypy passed. The local workbench backend was restarted
with this code after confirming no investigation was running.
