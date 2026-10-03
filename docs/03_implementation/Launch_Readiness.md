# PolyaBrain pre-deployment readiness ledger

Updated: 2026-10-03, Asia/Kolkata. Preparation deadline: **2026-10-07 00:15
Asia/Kolkata**. Work remains chapter-based. Deployment is deferred.

## Current verdict

**Public launch: NO-GO. Local preparation: in progress.** A substantial local
runtime and workbench pass regression checks. Representative reliability,
competitive quality/cost, independent review, real-user repeat use and production
operations are not established. There is no evidence for global superiority.

The original audit is preserved at
`runs/launch-readiness/2026-09-30/READINESS.md`. Its pending-disposition section
is historical: the user's subsequent “please continue” resumed implementation
with the evaluation results preserved in place. The current branch is
`feature/launch-readiness`, based on `ba51625096b522165fd7f8d7170eaa01a7e02a2e`.
Do not ask that resolved question again. All changes remain uncommitted; no push
or deployment is authorized. Preserve pre-existing untracked evaluation results
from Chapters 13C, 13D, 13E, 13F, 13J and 13K.

## Verified increments

| Scope | Evidence | Limit |
| --- | --- | --- |
| Initial backend audit | 970 passed, zero skips with disposable PostgreSQL and pinned Docker sandbox; nine migrations applied | Regression and empty-database migration checks |
| Initial frontend audit | Six unit tests, TypeScript and production build pass; six ordinary browser cases plus invite-only and self-service OIDC fixture flows pass | Paid-provider browser case skipped; loopback identity fixture, not hosted provider |
| Initial visual review | Desktop home and mobile report inspected | Not a complete accessibility audit |
| Chapter 13-P citation provenance | Saved wrong-section and invented-source outputs now rejected by current capability; corrected section accepted; both verifier paths and persisted API/learning regression covered | Fake model outputs; provenance does not establish semantic truth |
| Backend after citation change | 1,016 passed, zero skips, 76.62 seconds; JUnit retained | Developer tests; 841 dependency deprecation warnings remain |
| Final focused/static verification | 48 citation tests passed, zero skips; Ruff lint/format and strict mypy pass | Adds two non-HTTP compatibility cases after the full suite; not a full 1,018-test run |
| Chapter 98 transport recovery | 30 frontend tests pass, including native socket aborts; TypeScript/production build pass | Helper/socket and fake-time route checks; no backend cancellation guarantee |
| Browser after proxy change | Seven local cases and both OIDC fixture flows pass; lost-response case recovers persisted result with one run request | One live-provider case skipped; lost response deliberately injected |
| Production standalone deadline | Stalled headers and stalled bodies return 504 at 30.022/30.028 seconds; each upstream socket closes after one dispatch | Loopback HTTP fixtures, no model/backend execution |
| Chapter 77 storage-write limits | 24 database/API checks pass, including four-connection user/global races, rollback, shared upload quotas and ownership negatives | Daily retained-write bounds, not complete rate/storage protection |
| Browser write-limit recovery | Two OIDC fixture flows pass, including retained drafts/corrections after real 429 responses and saved-report access | One-session/one-feedback test configuration; no live provider |
| Full backend after write limits | **1,042 passed, zero skips**, 79.54 seconds, real PostgreSQL and pinned Docker sandbox; ten migrations applied | Developer regressions; 841 existing dependency warnings remain |
| Chapter 77 request-body admission | 53 focused checks and ten raw socket checks passed; actual 10-second deadline verified with h11/httptools | Per-request body bounds; not header/concurrency/rate protection |
| Full backend after body gate | **1,089 passed, zero skips**, 101.15 seconds, with real PostgreSQL and pinned Docker sandbox | 843 dependency deprecation warnings, including two exposed by socket tests |
| Browser after body gate | Seven local cases plus invite-only and self-service OIDC flows pass | Three skips: live-provider case, and one-quota fixture case in each auth mode; quota fixture passed in prior increment |
| Chapter 66 verification presentation | Before-fix failure preserved; three persisted citation scenarios pass through browser/report/trace/export/reload/mobile; seven ordinary browser cases pass | Scripted model outputs; one live-provider case skipped; no semantic truth or recovery claim |
| Frontend after report presentation | 30 unit/socket tests, TypeScript and production build pass | Backend runtime unchanged; no repeat of unchanged full backend suite |
| Saved DART termination audit | Trace exhausted 3/3 external calls before asking for public information; minimal current-policy probe reproduces ask-human at exhaustion and search with one call available | Not a full-run replay; no fresh scientific or source-selection success established |
| Chapter 13-P public-research budget stop | Current controller now stops at acquisition reservation denial instead of asking for user-owned information; kernel, CLI, persisted report and browser verified | Typed public gap and generated reservation denial only; the full DART task is not repaired |
| Backend after research-stop repair | **1,107 passed, zero skips**, 100.44 seconds, real PostgreSQL and pinned Docker sandbox; Ruff lint/format and strict mypy pass | Developer regressions; 843 existing dependency warnings remain |
| Research-stop browser delivery | One production-browser case passes, including export, reload, retained evidence, no clarification and no mutation; TypeScript passes | Seeded deterministic stop with zero live providers; unchanged frontend unit/build checks not repeated |
| Chapters 13-M/77/98 actual process loss | **Six new subprocess tests passed, zero skips**: SIGKILL at four local capability/checkpoint boundaries and two API persistence/admission boundaries; operator release preserves daily charges and saved success | Offline arithmetic and scratch PostgreSQL; not remote cancellation/billing or hosted-worker evidence; no runtime source change |
| Chapter 171 matched coding comparison | Original frozen developer batch: Polya 5/12, lean 12/12; 3.19× cost, 5.77× tokens, 2.46× time; all 24 artifact sets audited | Known tasks, not held out; explanation quality and human value unmeasured |
| Chapter 13-P generated-check recovery | Six saved rejections reproduce with precise locations; origin acceptance rule retained; sandbox parameter bounds now enter existing bounded repair | Prompt/diagnostic repair and model-boundary validation; post-change live comparison separate |
| Saved candidate admission ablation | Six rejected candidate implementations pass independent checks; five generated suites pass, one exceeds the size bound | Selected failed development responses; no successful final answer reconstructed; no live model calls |
| Post-prompt matched follow-up | Polya 11/12, lean 12/12; 2.91× cost, 5.03× tokens; targeted post-bounds task 2/2 for both with 4.77× cost | Separate development batches; no full six-case live run after final bounds change; original failures retained |
| Chapter 98 provider completion after caller death | Two new subprocess/loopback HTTP tests pass, zero skips: uncertain checkpoint remains blocked; PostgreSQL admission persists before/after independent provider completion; operator release retains daily count | Local fixture, not a paid provider, SDK retry test, invoice or hosted-worker proof; runtime unchanged |
| Chapter 98 HTTP backend loss and restart | One further test passes: client transport failure on SIGKILL; fresh Uvicorn reads retained state/allowances before and after late provider completion; duplicate 409 and replacement 429; operator release does not refund | Real HTTP/routes/database with trusted fixture principal and gated runner; not OIDC, browser or hosted evidence |
| Chapters 66/98 browser process loss | New actual-loss browser case passes; 7 ordinary browser regressions pass with 1 live-provider skip; 17 backend checks, 30 frontend tests, TypeScript/build and service mypy pass | Saved running state now reads outcome pending; one dispatch across outage/restart; fixture identity and loopback provider, not OIDC or billing proof; initial ordinary-run setup failures preserved |
| Backend after proposal-repair changes | **1,142 passed, zero skips**, 105.66 seconds, real PostgreSQL and pinned Docker; Ruff and strict mypy pass | 843 dependency warnings; one additional malformed-cost audit case subsequently passes in focused 11-case audit suite |
| Chapter 13-P unavailable public research | Five before-change failures preserved; missing, failed/inconclusive/blocked search and privacy refusal now stop without fabricated user-input needs; 108 focused checks and 2 browser cases pass | Typed public gaps only; genuine private clarification and alternative inspection preserved; deterministic fixtures, not source-selection or provider proof |
| Backend after unavailable-research repair | **1,157 passed, zero skips**, 114.47 seconds, scratch PostgreSQL and pinned Docker; Ruff, four-module strict mypy and frontend TypeScript pass | 843 dependency warnings; no new frontend runtime changes or paid calls |
| Chapter 13-P distinct-page recovery | Original 3 failures preserved; 118 focused checks pass, including 14 new recovery cases and actual adapter-to-export flow with fixture providers; fresh evaluated discovery can enable a different document after a bound failed attempt | Two-read ceiling, no-repeat URL, privacy and shared budget retained; recovered passages do not establish a verified outcome; legacy/unbound failures remain blocked |
| Backend after distinct-page recovery | **1,171 passed, zero skips**, 111.97 seconds, scratch PostgreSQL and pinned Docker; Ruff and two-module strict mypy pass | 843 dependency warnings; no paid calls, frontend changes or deployment |
| Chapter 13-P preferred research routes | Five before-fix failures retained; 89 focused checks pass. Scope reviewer and page reader now use actual invocation reservations and normal admission, and pending evaluation cannot buy new search | Developer fixtures, not live source-selection or full DART recovery; [chapter](Chapter_13P_Preferred_Research_Routes.md) |
| Chapter 171 source-packet comparison, original | Four paired synthetic cases complete: Polya delivers 1/4, lean 4/4; all 15 calls reconcile to $0.07404150 | Delivery only, no independent semantic ratings; [chapter](Chapter_171_Source_Packet_Comparison.md) |
| Bounded supplied-evidence framing repair | Existing snapshots now enter initial framing as limited, untrusted user data; focused prompt, routing and harness checks pass | Snapshot content is not admitted as truth; synthetic follow-up is separate development evidence |
| Chapter 171 source-packet follow-up | Two paired cases delivered by both arms; a later provider call returned no response or cost, so the guard retained $0.04337250 and stopped remaining cases | Incomplete batch; ten known calls report $0.05577900; no further paid calls pending cost reconciliation |
| Backend after research-route and framing changes | **1,226 passed, zero skips**, 124.66 seconds, scratch PostgreSQL and pinned Docker; Ruff lint/format, strict mypy for three runtime modules, and `git diff --check` pass | 843 dependency warnings; no frontend change or new browser claim |
| Chapter 172 adversarial differential verification | 32 new developer controls expose and repair false agreement for nested types, mutation after exceptions, truncated iterators, skipped required checks and failed sandbox results; both report pipelines retain unverified status; 70 focused checks pass | Actual local Docker with scripted proposals; no live solver-quality or real-change catch-rate claim; [chapter](Chapter_172_Adversarial_Verification.md) |
| Backend after differential hardening | **1,258 passed, zero skips**, 132.93 seconds, scratch PostgreSQL and pinned Docker; Ruff lint/format and strict mypy on both changed runtime modules pass | 843 dependency warnings; zero paid calls; unchanged frontend checks not repeated |
| Chapter 172 incomplete comparison coverage | Seven before-fix failures retained; failed generation, reference timeouts and unusable scale checks block clean certification; bounded retries, retained counterexamples/counts and post-repair gating verified | Ten coverage controls plus four replay-binding checks; scripted model outputs and actual local Docker; [chapter](Chapter_172_Comparison_Coverage.md) |
| Offline QuixBugs historical-response replay | 80 expected arm records: 38 bug regressions; 34 unchanged controls; zero control regression reports; three controls unverified; five historical responses/attempts unavailable | 75 replayable attempts, zero new provider calls; public algorithm fixtures, not fresh live trials or real-user changes; replay manifest pins its runtime |
| Backend after coverage work | **1,325 passed, zero skips**, 154.86 seconds, scratch PostgreSQL and pinned Docker; Ruff lint/format, three-module strict mypy and `git diff --check` pass | Includes other working-tree work as well as this chapter's 14 tests; 843 dependency warnings; no new browser claim |
| Chapter 171 aggregate accounting | 512 returned guarded calls, nine trace-only calls and ten unresolved reservations inventoried; $4.96704900 recorded reported-plus-reserved; 17 offline tests pass | Only $0.03295100 nominal difference from $5; not spending clearance; one additional unitemized trace and invoice reconciliation remain unresolved; [details](Chapter_171_Campaign_Accounting.md) |

See [citation implementation and limitations](Chapter_13P_Citation_Provenance.md).
No live provider requests were made in the initial audit and engineering-fix runs.
The subsequently authorized matched evaluation campaign below uses live OpenRouter. Historical failures
and initial before-fix observations remain separate from after-fix results.
Unchanged passing frontend checks were not rerun for the backend-only citation
change. They were rerun for the subsequent proxy change. The unchanged backend
suite was not rerun for that frontend-only increment.

## Priority queue and exit evidence

1. **Chapters 13-M, 77, 98: interruption and bounded recovery.** Proxy transfer
   deadlines and lost-response recovery are now verified locally; see
   [Chapter 98 evidence and limits](Chapter_98_Workbench_Transport_Recovery.md).
   [Actual process-loss checks](Chapter_98_Process_Loss_Verification.md) now cover
   safe checkpoint continuation, uncertain-call refusal and retained API admissions.
   Two additional loopback-provider probes now verify completion after caller
   SIGKILL: no checkpoint replay, duplicate dispatch, automatic admission release
   or passing report; operator release retains the daily allowance. A third test
   now kills and restarts the actual Uvicorn backend: real HTTP returns retained
   running/unverified state, 409 duplicate and 429 replacement-run refusal, then
   failed/operator_stopped after explicit release. The new production-browser
   probe also passes outage/reconnection, late completion, operator release,
   export and mobile reload with one dispatch. Misleading progress wording is
   corrected to outcome pending; see [browser evidence](Chapter_98_Browser_Process_Loss.md).
   Next local priority is the source-fidelity/acquisition-routing audit below;
   hosted recovery and actual provider reconciliation remain separate gates.
   Local socket cancellation does not prove that backend/provider work stopped.
2. **Chapters 13-P, 29, 107, 136: source fidelity and false success.** Citation
   acceptance is now screened. Persisted failures and safe next actions now pass
   [browser delivery checks](Chapter_66_Verification_Status_Presentation.md).
   Typed public-research reservation denial now stops truthfully with retained
   evidence and costs; see [implementation and limits](Chapter_13P_Public_Research_Budget_Stop.md).
   Missing, failed and privacy-blocked research now stop honestly; genuine
   user-owned clarification remains available. See
   [the unavailable-research chapter](Chapter_13P_Public_Research_Unavailable.md).
   Distinct-document continuation after a known failed read now passes the bounded
   recovery gate; see [page-read evidence and limits](Chapter_13P_Page_Read_Recovery.md).
   Scope-review and pending-evaluation exits, including invocation-specific
   reservation handling, now pass [focused checks](Chapter_13P_Preferred_Research_Routes.md).
   Source-selection and semantic-support adversarial checks remain necessary;
   the synthetic source-packet lane does not exercise acquisition.
   Update the master plan before further intelligence changes.
   The saved DART run stopped at its external-call ceiling;
   it was not a browser hang. Representative source selection, semantic support
   and full failure recovery remain unproven. Preserve the recorded DART stop and
   original HTTP failure. See the [offline termination audit](Chapter_13P_Core_Value_Recovery.md#offline-launch-preparation-audit-of-the-persisted-dart-stop).
3. **Chapters 73, 77, 155: abuse and privacy.** Authenticated session creation and
   feedback now have durable volume quotas; see [policy and limits](Chapter_77_Storage_Write_Limits.md).
   Direct API body bounds before JSON parsing are now implemented and verified
   against oversized/chunked and slow uploads; see [request-body admission](Chapter_77_Request_Body_Admission.md).
   Header parsing before ASGI, aggregate concurrency, retention, export/deletion,
   edge throttling, authentication traffic and total storage remain separate gaps.
   Run/write allowances are not currency reconciliation or complete abuse protection.
4. **Chapters 171, 13-K, 161–170: supported claim and measured value.** Freeze an
   independent corpus before further broad claims. The newer frozen six-case
   developer comparison has **5/12 Polya passes versus 12/12 lean passes**, 3.19×
   provider-reported cost, 5.77× tokens and 2.46× time. Six failures identified a
   generated-check repair ambiguity; prompt and location feedback are now repaired
   without relaxing admission. The separate full follow-up reaches **11/12 versus
   12/12**, still 2.91× cost and 5.03× tokens. The subsequent size-boundary repair
   passes its targeted 2/2 follow-up, with 4.77× cost; it is not a full-corpus result.
   A new [source-packet comparison](Chapter_171_Source_Packet_Comparison.md) tests
   post-acquisition reasoning over four developer-authored synthetic cases. Its
   original Polya delivery failure led to bounded evidence context in framing.
   The separate follow-up has only two completed pairs and an unresolved provider
   call; neither batch establishes independent semantic correctness or product
   advantage. The pilot protocol is prepared but no people have participated.
   The shared coding/change verifier now passes the 32 adversarial controls and
   the additional coverage tests: generator errors/reference timeouts can no
   longer silently yield a clean certificate. Saved QuixBugs generators have been
   replayed locally with omissions and abstentions retained. These are mechanism
   tests and historical-response replay, not new independent model outcomes.
   Next evidence should use the founder's next real problems under the current
   founding-thesis reliability gate and independent real-change inputs; retain
   model-oracle and same-process isolation limitations. The additional campaign records are now inventoried below; ten unresolved
   charges and an unitemized trace still block paid work.
   See [the evidence/reviewer/pilot package](Chapter_171_Readiness_Evidence_Package.md).
   Historical smaller coding pilots had equal success but worse Polya costs.
   See [matched outcomes](Chapter_13P_Compact_Model_Interface.md). Preserve failed
   attempts; lower cost must not weaken verification. Next evaluation work should
   test the actual investigation wedge with equally capable tools and fresh
   independently supplied tasks, rather than tune repeatedly against these six
   coding tasks. Until those tasks exist, source-support adversarial checks and
   backend-process-loss/browser-reconnection verification can proceed locally.
5. **Chapters 61–70, 101–108, 120, 176: usability and real users.** Exercise long
   reports, citations, code, keyboard/mobile, refresh/resume and clear failures.
   Master-plan pilot/reviewer and voluntary second-use evidence remain absent.
   Prepare review materials locally; contacting reviewers needs authorization.
6. **Chapters 171, 175, 178: final handoff.** Record exact revision plus uncommitted
   patch identity, test results/skips, limitations, supported claim and stop-launch
   criteria. In the last scheduled run within four hours of the deadline, finish
   bounded verification, hand off and pause the heartbeat. After the deadline,
   handoff only; do not implement or deploy.

## Remaining external and deployment gates

The user delegated evaluation provider/account and budget choice. The existing
OpenRouter account and aggregate **US$5** campaign ceiling were selected. The
three earlier completed batches (52 attempts, 124 provider calls) reported
**$1.42342275**. The source-packet original reported **$0.07404150** across 15
calls. The follow-up has ten returned calls reporting **$0.05577900**, plus one
unreturned call with **$0.04337250** retained as a local reservation. Total
reported cost is **$1.55324325**; reported plus unresolved reservation is
**$1.59661575**, leaving a nominal **$3.40338425** in that historical subset.
The [2026-10-03 aggregate inventory](Chapter_171_Campaign_Accounting.md) now
joins those batches with `runs/verified-coding/` and `runs/verified-change/`:
**$4.38000975 reported through saved responses or traces plus $0.58703925 across
ten unresolved reservations = $4.96704900**. Only **$0.03295100** nominally remains
below $5. Neither this amount nor the older subset remainder is spending clearance.
The inventory covers 512 returned guarded calls and nine additional trace-only calls.
A Chapter 174 failed-development trace has no itemized calls; its actual charge is
not established by the saved artifacts and is excluded from these quantified totals.
The earlier verified-coding ledger omitted the source-packet batches, whose
$0.17319300 exactly explains the difference from its $4.79385600 total.
Historical ledgers are retained unchanged.

**Paid calls remain paused.** Ten unknown reservations and the unitemized gap need
reconciliation or explicit disposition before any new bounded paid work. A local
reservation is not an invoice upper bound; no provider-account balance or cap was
verified. Source hashes and per-call inventory are in
`runs/launch-readiness/2026-10-03-campaign-inventory.json`; 17 new offline tests pass.
No paid calls, account changes or credential creation were performed in this audit.
Independent judgments and real-user behavior cannot be
manufactured by the assistant. Public exposure additionally requires actual
identity-provider/HTTPS verification, private service boundaries, edge controls,
spend configuration, monitoring, backup/restore, load and rollback rehearsal,
worker operations and a security review. No cloud provisioning, publishing or
production changes are in scope for this preparation window.

The active heartbeat continues local work in this chat. The computer and Codex
app must remain running for local scheduled execution. A deadline does not waive
any readiness gate.
