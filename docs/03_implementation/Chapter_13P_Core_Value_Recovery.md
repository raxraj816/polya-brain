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
