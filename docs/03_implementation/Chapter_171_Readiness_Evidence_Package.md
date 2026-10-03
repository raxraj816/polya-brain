# Chapter 171 — launch-preparation evidence package

## Decision and scope

**Public launch remains NO-GO.** This package measures developer cases and prepares
independent review. It does not establish a world-leading product, unseen-task
performance or customer demand. No deployment or external reviewer contact occurred.

The user delegated provider and budget selection. The selected existing OpenRouter
account is used only for this evaluation campaign with an aggregate **US$5** ceiling.
Both arms pin `google/gemini-3.7-flash`, with fallback disabled. No credits were
purchased and no account/key limits changed. Conservative local reservations stop
new calls on unknown cost, route mismatch, exceeded reservation or insufficient
remaining allowance. They are estimates, not an invoice or provider-enforced cap.
Do not reset this campaign's allowance on a heartbeat or new output directory.

## Frozen comparison

Six known coding problems, two repetitions each, two arms: production cognitive
runtime and a lean model → sandbox → bounded repair loop. Both use the same prompt,
observed model and outer ceilings: six model calls, 20,000 output tokens, 6,000 per
request, four sandbox executions and 240 seconds. The runtime retains its internal
scheduling and verification rules. Input tokens are measured; there is no shared
hard token-count limit before requests, although both use the same request-byte
ceiling. All attempts are preserved, including no-answer and admission failures.
Order alternates by repetition. Independent developer checks run after each attempt
and are never sent to either solver. Elapsed solving time excludes those checks.

Cases are frozen in `evals/launch_readiness/coding-regression-cases.json`. They were
already used during development: **not held out**, even though independent checks
are hidden from the model. Repetitions are not independent samples of task diversity.
The comparator is a practical tool loop, not a deliberately weak text-only answer.

Original artifacts: `runs/launch-readiness/2026-10-01-matched-v1/`.
Audit and blinded packet: `runs/launch-readiness/2026-10-01-matched-v1-review/`.

| Original frozen batch | Lean loop | PolyaBrain |
| --- | ---: | ---: |
| Passing delivered implementations | 12/12 | 5/12 |
| Tokens | 48,202 | 278,083 |
| Provider-reported USD | 0.15580950 | 0.49704225 |
| Summed solving seconds | 281.687 | 693.414 |

PolyaBrain costs 3.19×, consumes 5.77× tokens and takes 2.46× time in this batch.
Total reported spend is **$0.65285175**. All 24 artifact sets pass the offline
consistency audit. This does not authenticate provider invoices or independently
prove explanation quality. Seven failures remain failures: six at generated-test
admission after bounded repair, one at structured JSON parsing. None is silently
removed from the denominator or converted to success by scoring proposed code.

## Repair and verification

Six saved initial deliberations reproduce rejection at exact test locations.
The model had retained literal comparisons derived from prose examples while its
repair concentrated on invented boundary tests. The exact-token admission rule
cannot establish origin for prose or changed receiver names. The revised prompt
states that distinction, and diagnostics identify all offending locations up to
ten without echoing user values or code. The validator's acceptance rule remains
unchanged, as do retries, model budgets and previously admitted-check protection.
Prompt version is `cognitive_capability@0.10.1`; origin screen is
`generated_check_sources@0.1.1`.

Saved replay: `runs/launch-readiness/2026-10-02-check-repair-replay.json`.
Focused regressions: 103 passed and four Docker cases initially skipped; those
four were then run successfully after restoring the pinned image reference.
Seventeen evaluation-control tests pass, including missing/corrupt records,
route/cost mismatches, unknown spend and preserved failed attempts. Ruff and
strict mypy pass for the changed runtime modules. These are developer checks.

A separately labeled post-change batch uses the same six cases and repeats under
a **$1 sub-budget**, inside the remaining original $5 campaign allowance.
Its artifacts are `runs/launch-readiness/2026-10-02-matched-v2/`. It completed
24 attempts: **Polya 11/12, lean 12/12**. Polya uses $0.49763025, 294,139 tokens
and 730.582 summed seconds; lean uses $0.17126850, 58,430 tokens and 313.014
seconds. Ratios are **2.91× cost, 5.03× tokens and 2.33× time**. All 24 artifact
sets pass the audit. The remaining failure is the oversized test discussed below.
This batch ran prompt version 0.10.1; the final 0.10.2 size repair has only the
separate targeted live comparison, not a repeated full six-case result. Do not
substitute either follow-up for the original failures.

## Independent review packet: ready, judgments pending

Share `review-packet.md` and its `review-packet.json` rating form with these
instructions to each reviewer separately, once contact is authorized.
Keep `private-condition-key.json`, `audit.json`, model identity, costs and prior
results hidden until judgments are locked. Responses have randomized opaque IDs
and order; answer wording is unchanged, so style may still reveal a condition.
Every pair is included, including absent answers. No reviewer judgments are filled.

Select two technically competent reviewers who did not build these changes: one
algorithms/correctness reviewer and one senior engineer who regularly investigates
technical problems. Ask them to disclose relevant conflicts and familiarity with
these tasks. Each reviews the same packet independently before discussion.

For each pair, record correctness/counterexamples, explanation and complexity,
unsupported claims, useful next actions and required repair effort. Choose either
response, tie or neither, with a concrete reason. Do not reward length or a claim
of verification without evidence. Empty output counts as no delivered solution.
Record review time. Keep initial disagreements; adjudication is a separate record.
After ratings are locked, reveal the condition key and resource costs, and ask
whether any usefulness advantage justifies the overhead. Two reviewers improve
scrutiny; they are not a representative user sample or a statistical guarantee.

## Fresh-task evaluation: protocol ready, evidence pending

Before another model run, have the independent reviewers privately supply tasks
and acceptance criteria not used in implementation. Include coding/debugging,
source-grounded technical investigation, and deliberately insufficient evidence.
Keep reference answers/checks inaccessible to the solver. Freeze task/check hashes,
model, tool availability, budget, scoring rubric and stopping rule before execution.
Allow external research equally in both arms for source tasks; this coding batch
had none. Preserve exclusions with reasons decided before results are viewed.

Compare verified useful completion, unsupported claims, source support, dollar and
token cost, latency and required human repair. Report each task and category;
do not pool different budgets or task types into an unexplained win rate. Report
failures and missing telemetry. Any changes based on these tasks make them future
development cases: collect new independent tasks before claiming generalization.

## Real-user pilot: materials ready, participation pending

Select three voluntary target users with actual technical work: a founder or
technical product builder, a working software engineer, and a researcher. Do not
invent identities or infer willingness from public profiles. No recruitment
messages are authorized or sent by this package.

Use a local or otherwise explicitly authorized private environment. At intake,
record a pseudonymous participant ID, role, problem, usual workflow, success
criterion, permitted data/tools and time allowance. Exclude confidential inputs
unless the owner has authorized their use. The facilitator explains evidence,
checks and uncertainty, then observes without solving the task for the participant.

Record time to first useful result, successful outcome, evidence inspection,
confusing controls, failures, facilitator help, corrections and total effort versus
the participant's usual workflow. Ask what they would use next time and why. Offer
continued optional access without prompting a second task; record voluntary return
on a genuinely different task, with consent and the observation window. Requested
or coached reuse is not voluntary retention. Keep dropouts and negative feedback.

Pilot form fields: participant_id, consent_recorded, role, task_description,
acceptance_criteria, usual_workflow, start_time, end_time, outcome,
verification_checked, unsupported_claims, required_repairs, assistance,
preferred_workflow_and_reason, followup_window, voluntary_second_task,
second_task_outcome. Unobserved fields remain null. Three participants are formative
usability evidence, not market validation.

## Mechanism attribution and remaining gates

Citation rejection, budget stops and actual process-loss tests demonstrate local
mechanisms under controlled failures. They do not measure a live quality/cost gain
from those mechanisms. A saved-response ablation may isolate an admission decision;
it cannot reconstruct an unobserved final answer or customer preference. Live
ablations require frozen fresh tasks, equal budgets and preserved outcomes before
causal product-value claims. Do not disable safety checks in the product to win an
experiment.

Engineering, independent task performance, human review and voluntary second use
are separate gates. Hosted authentication, edge/resource controls, retention,
monitoring, backup/restore and rollback still need their own verification when
deployment is authorized. This package is an evidence handoff, not a release waiver.

### Saved-candidate admission ablation

`runs/launch-readiness/2026-10-02-admission-ablation.json` records all six selected
failed initial proposals. With origin screening, all six are rejected. In isolated
Docker execution of the saved candidate, all six pass independent developer code
checks; five pass their generated checks, while one generated suite exceeds the
existing per-test size bound and is rejected before execution. The initial probe
aborted on that bound; its error artifact is preserved and the probe was corrected
to retain the rejection as data. There were no model calls for this experiment.

This isolates an admission obstacle on already-known candidates. It does not show
six successful delivered reports without the screen, validate all explanations,
or justify removing provenance checks. The original six no-answer outcomes stand.

### Sandbox bounds repair

The first post-prompt integer-coverage run produced a 2,105-character test, exceeding
the 2,000-character execution limit. The model output parser previously accepted
it, so the failure bypassed its bounded repair. Shared proposal validation now runs
inside the model boundary and again before dispatch. The existing sandbox retains
its own admission. Prompt identity advances to `cognitive_capability@0.10.2`.
Nine new cases cover malformed/oversized parameters, successful repair, and a
failed repair with exactly two accounted model attempts. The initial negative test
expected the unwrapped exception; it was corrected to check the existing audited
error and its cause. All original test-run artifacts remain preserved.

Local wall times are descriptive: validation work shares this host during the
post-change batch. Do not treat them as isolated performance measurements.


### Broad regression verification

The full backend suite after both recovery changes passes **1,142 tests, zero
skips**, in 105.66 seconds using a fresh ten-migration PostgreSQL database and the
pinned Docker image. The scratch database container was stopped afterward. There
are 843 existing dependency warnings. The additional non-finite-cost artifact case
was added after that suite was collected; all 11 audit cases then passed separately.
Ruff lint/format and strict mypy (145 source files) pass. The malformed-cost test
first exposed a missing finite-number check in the audit utility; the failing
JUnit and repaired result are both retained. These checks are not independent
product evidence. Unchanged passing browser checks were not rerun.

### Targeted follow-up after sandbox-boundary repair

`2026-10-02-bounds-v3` completed four attempts: PolyaBrain **2/2** and lean **2/2**
on the already-known integer-coverage task. All four artifact sets pass the audit.
Polya uses $0.08404425 and 50,387 tokens; lean uses $0.01762800 and 5,184 tokens.
Total additional reported spend is **$0.10167225**. The cost ratio is 4.77× and
token ratio 9.72×, so this is recovery evidence, not an economics win. Both live
Polya runs used origin repair; neither happened to trigger an oversized-test repair.
The size-boundary repair itself is verified by saved-response rejection at the
model boundary and deterministic model-repair tests, not by a live size violation.
Do not pool this selected one-task follow-up with the six-case batch.


## Reconciled campaign and next work

All three batches completed: **52 attempts and 124 provider calls**. Raw per-arm
responses match the shared spending ledgers by response ID and content. No unknown
or outstanding reservations remain. Provider-reported total: **$1.42342275**;
remaining original campaign allowance: **$3.57657725**. See
`runs/launch-readiness/2026-10-02-campaign-reconciliation.json`. This is telemetry
reconciliation, not invoice verification. No further paid evaluation is currently
running. Do not reset the allowance on the next heartbeat.

The strongest supported conclusion is improved recovery on known coding tasks,
with a persistent substantial cost gap against the lean baseline. The prompt
changes were motivated by these failures, so improvements are development evidence,
not held-out proof. The blinded packets are ready; no independent ratings or real
pilot sessions have occurred. Next useful local work is adversarial source-support
verification and independent provider completion after worker death. A broader
competitive claim needs fresh investigation tasks and real human judgment, not
another favorable rerun of this coding corpus.
