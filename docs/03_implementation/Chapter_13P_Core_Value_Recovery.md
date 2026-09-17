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

503 backend tests passed with the isolated Postgres integration database. Ruff,
format checking, and strict mypy passed. Regressions cover public CLI JSON lookup
under a user directory, multi-file lookup rejection, source preservation through
model paraphrasing, path-independent routing, complete late-file coverage, fair
allocation, and truthful truncation provenance. The small subsequent URL-source
exclusion was checked with the 48 relevant framing/routing tests. Live end-to-end
completion remains unproven; this test count is not the product-value gate.

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
