# Public self-service release readiness

The user selected public self-service release within one week. Hosting, domain
and identity-provider choices are explicitly deferred. This document tracks
the existing Investigator product; it does not narrow the runtime's long-term
ambition or claim launch readiness from a test count.

## Current evidence

| Requirement | Current evidence | Release state |
| --- | --- | --- |
| Self-service identity admission | Explicit mode, validated OIDC identities, issuer-bound opaque cookies, subject revocation; private mode stays default | Implemented locally |
| Private account workspaces | Fresh-Postgres integration and real-browser account switching deny another account's report | Locally verified |
| Complete browser workflow | Production Next.js build; earlier authenticated arithmetic/account-isolation flow, plus a live graph investigation with persisted reload, exact code copy/export and inspectable repair trace | Locally verified; graph run used loopback test mode |
| Spending admission | Existing per-user/global daily and concurrency enforcement; included in database suite | Local mechanism verified; hosted price reconciliation remains open |
| Backend regression | 970 passing tests with all DB tests enabled, including Docker recovery, generated-check admission, bounded response edits, exact code attachment, source-check API persistence/reuse and transfer-oracle tests; Ruff and mypy pass | Passed |
| Frontend build | Typecheck, six unit tests, formatting and production build passed | Passed |
| Technical coding reliability | Latest signed-array and directed-walk reruns: each has Polya 2/2 and lean 2/2; independent checks and runtime acceptance pass within unchanged budgets. A separate browser graph run passes 600 random and eight boundary/scale checks | Four latest matched attempts and separate browser run pass; broader reliability and efficiency advantage unproven |
| Source-edit recovery | Failed first model edits now receive one governed replacement attempt; two live injected-failure runs pass the unchanged check and 3,000 independent comparisons each | Controlled recovery verified; broader diagnosis/repair reliability unproven |
| Hosted signup and HTTPS | Provider/domain/host not selected | Unverified; deferred by user |
| Operations | Hosted backup restoration, retention/deletion, monitoring, abuse handling and rollback rehearsal | Not established by local checks |
| Product value | No demonstrated advantage on these matched coding cases; independent technical-user and repeat-use evidence still missing | Unproven |

## Active delivery order

Latest user priority: product advantage takes precedence over demo polish.
The latest signed-array regression completes 2/2 versus lean's 2/2 after compact
requests, stricter proposal-status admission and bounded response edits. Earlier
0/2 and 1/2 runs remain preserved. The latest completions pass unchanged independent
checks and runtime acceptance, using three calls and 16,832 / 17,309 total tokens
versus lean's one/two calls and 2,575 / 6,570 tokens. Neither Polya attempt needs
repair, so these savings cannot be attributed to edit application. See
`Chapter_13P_Compact_Model_Interface.md` and the preceding delivery chapter.
Do not count undelivered candidate correctness as a completed outcome or override
frozen failed scores.

The graph rerun also completes 2/2 for both arms. Its checks cover 600 random
multigraphs and eight boundary/scale cases. Both Polya runs actually repair test
fields without regenerating the implementation. Polya uses four calls and
30,863 / 30,723 tokens versus lean's one call and 4,581 / 4,554. Relative to the
preceding build, average tokens fall about 37% on signed arrays and 9% on graphs;
two repetitions per task do not establish a stable or causal improvement. Lean
remains cheaper in tokens and faster on these tasks. Reducing this overhead and
measuring useful transfer to fresh investigations remain the product priorities.

The separate production-browser graph session persists a complete readable report,
exact copyable code, full original problem, repair metadata and Markdown export.
Its independent replay passes and confirms delivered/executed code identity.
Artifacts: `runs/coding-readiness/browser-edit-repair-graph-v1`. This is an
additional developer run, not another matched baseline or external user sample.

1. Address measured completion failures and excess orchestration cost across fresh tasks.
   Preserve failed runs and their costs. A wrong or unverified answer must remain
   clearly incomplete in the UI and report.
2. Verify the full intended public workflow with authenticated users, quotas,
   data handling and recovery. Include failure paths, not just a successful demo.
3. Prepare provider-independent deployment and operational checks while hosting
   decisions are deferred. Provision and verify actual HTTPS/OIDC when selected.
4. Rehearse the release against production-like staging: account creation,
   ownership isolation, representative investigations, interrupted work, resource
   exhaustion, backup restoration and rollback.
5. Obtain independent technical-user feedback and measure successful repeat use.
   Neither architectural ambition nor selected passing examples prove a win.

## Preserved coding evidence

- `runs/coding-readiness/matched-common-slot-v1`: invalid comparison because a
  harness adapter failed before Polya called a model. Both lean runs and their
  costs are retained; this is not a Polya loss or lean win.
- `runs/coding-readiness/matched-common-slot-v2`: valid initial pilot. Polya asked
  for its own output as missing input in one repetition and truncated its proposal
  in the other. Lean delivered code passed both independent checks in both repeats.
- `runs/coding-readiness/matched-common-slot-v3`: framing context/empty-list rules
  and proposal allowance repaired. One run reached execution and caught a real
  misspelled variable; its recovery plan truncated. Another proposal/repair still
  failed before execution. Lean again passed both repetitions.
- `runs/coding-readiness/matched-common-slot-v4`: both Polya repetitions reached
  and passed their sandbox tests, after three provider calls. Neither delivered
  an answer: the conclusion capability reserves four calls and the common six-call
  allowance had three remaining. Lean passed both independent outcomes in one call
  each. Polya used 22,700 / 16,449 tokens and 68.2 / 34.3 seconds versus lean's
  4,427 / 6,289 tokens and 30.7 / 37.5 seconds. These are two repetitions of one
  development problem, not estimates of general performance.
- `runs/coding-readiness/matched-common-slot-v5`: bounded review permits completion
  in both repetitions. Delivered code passes all 1,200 seeded random cases and
  boundary/scale checks, plus the current execution/identity acceptance gate.
  Polya uses four calls each, 28,728 / 29,464 total tokens and 72.7 / 76.3 seconds.
  Lean passes both with one/two calls, 6,119 / 10,554 tokens and 35.7 / 49.2 seconds.
  Completion improved; there is still no measured advantage on this problem.
- `runs/coding-readiness/matched-common-slot-v6`: the proposal prompt explicitly
  retains candidate status before execution and disallows predicted results as
  observed evidence. Both Polya repetitions again pass independent checks and
  runtime acceptance, using four/three calls, 28,787 / 17,698 tokens and
  78.7 / 52.2 seconds. Lean passes both with one call each, 5,301 / 5,857 tokens
  and 34.5 / 38.9 seconds. One unsupported selection still requires model repair.
  The small sample does not establish a causal efficiency improvement.

The bounded-verification follow-up retains independent review while sharing a
hard provider-call allowance across retries, repairs and fallback routes. V5
and v6 confirm completed outcomes under the unchanged comparison ceiling. Next
measure fresh technical investigations and failure recovery against the practical
baseline, including human effort and reuse; this already-developed case cannot
establish generalization or user preference. Avoid further tuning solely to this
one regression. Public release remains gated on representative reliability and
the unverified operational requirements above.

## First-model source-repair recovery

The existing recovery path previously admitted only recalled edits. A frozen
retry-deadline task now tests a deliberately incomplete initial proposal through
the public runtime. The preserved failed live run spends two real calls and
10,030 tokens without a verified repair. After the routing fix, both repetitions
recover with one real call, using 3,290 / 3,334 tokens and 11.43 / 11.71 seconds.
Both preserve the failed verdict and original files, pass the unchanged admitted
check and 3,000 withheld comparisons, and admit only the verified replacement to
memory. Injected proposal counts are separated from real provider usage.

The PostgreSQL API regression also verifies that the current replacement is
exported, historical failure is visible, lessons stay owner-scoped and a related
case reuses the correct edit with fresh execution and zero additional model calls.
That API test uses scripted proposals; the two recovery runs use a live model.
These are controlled developer tests, not evidence of competitive superiority or
real-user preference. Reproduction: `evals/chapter_13p/source_recovery/README.md`.
