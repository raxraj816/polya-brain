# Chapter 77: Durable run allowances

Authenticated API users now have a UTC daily invocation allowance and a concurrent
run limit. Defaults are 20 starts/resumes per user per day and one active run per
user; the whole service permits 100 starts/resumes per day and four active runs.
Each start or clarification resume also uses the existing Cognitive Runtime's
per-invocation model-call, external-call, token, duration, and normalized-resource
ceilings. Operator-local bypass keeps the existing per-invocation limits and does
not apply these shared-service allowances.

The four settings are `POLYABRAIN_DAILY_USER_RUN_LIMIT`,
`POLYABRAIN_DAILY_GLOBAL_RUN_LIMIT`, `POLYABRAIN_CONCURRENT_USER_RUN_LIMIT`, and
`POLYABRAIN_CONCURRENT_GLOBAL_RUN_LIMIT`. A daily limit of zero closes new work
while keeping reports readable. Limits apply to runs through both the ordinary
Investigator and consented source-check paths. Read/report/export/feedback routes
do not consume a run allowance. Authentication is still required independently.

## Admission before dispatch

Migration `20260917_0009` adds durable `run_admissions` records. A short Postgres
transaction acquires a shared advisory lock, checks user/global daily and active
counts, records the configured resource ceiling snapshot, and claims the problem
session. The slot and session transition commit together before any runner or
provider is called. Concurrent workers therefore cannot both use the last slot.
The trace records `run_admitted`, its admission ID, and the resource ceilings.

A rejected start returns HTTP 429 plus Retry-After and leaves its session created.
A rejected clarification resume leaves the question pending and the submitted
answer unconsumed. The browser retains the question/answer for retry and displays
the reason. Existing terminal-session conflicts never charge another allowance.
Successful, failed, and paused work release their active slot after their outcome
is persisted, but their daily allowance remains charged. This deliberately avoids
claiming a refund for provider work that may already have been billed.

The user's allowance, reset time, active count, and per-invocation ceilings are
visible via authenticated `GET /api/v1/usage` and the workbench. Query state stays
inside the account's isolated cache. Global congestion can still reject a run even
when that user has allowance remaining; the API explains which boundary rejected
it without exposing another user's investigation.

## Interrupted workers

An unfinished admission never expires automatically, including across a UTC day
boundary. The system cannot infer that a remote call or sandbox stopped merely
because a lease elapsed. This can reduce capacity after a crash; it cannot quietly
admit replacement work on top of an uncertain active worker.

Operators can inspect active admissions with:

```sh
.venv/bin/python scripts/manage_run_admissions.py
```

After inspecting and stopping the specific worker/container, release only its
admission:

```sh
.venv/bin/python scripts/manage_run_admissions.py --release <admission-uuid> --confirm-worker-stopped
```

This is an operator database action, not a user endpoint. It records the release
in the admission and session trace, safely marks a still-running session failed,
and keeps its daily charge. The command refuses release without the explicit
worker-stopped assertion. Database credentials are the operator trust boundary.

## What this gate establishes

This is a conservative invocation allowance, not currency billing or a promise
about an external provider's invoice. Even an inexpensive deterministic invocation
uses one allowance. Existing traces report actual recorded model/tool usage;
provider prices and ambiguous remote completions require separate reconciliation.
Per-invocation limits and the admitted invocation count bound dispatch opportunity;
they do not replace a provider-account spending limit.

Tests cover same-user concurrent acquisition across database connections,
user/global daily caps, an active slot surviving midnight, denied clarification
recovery, failure/conflict charging, interrupted worker retention, operator release,
and HTTP 429 without input loss. The OIDC browser suite also checks allowance
visibility in the real authenticated workbench.

Remaining Chapter 77 work includes price reconciliation, warning thresholds tied
to measured cost, and evaluated semantic caching. Public launch additionally needs
rate/creation-volume limits at the edge, actual provider/cloud provisioning,
retention/backup operations, monitoring, independent security review, and fresh
technical/user validation. Do not treat this increment as completion of those gates.

Validation: 495 backend tests passed with migrated Postgres; strict Python checks,
frontend type checks/build, and the authenticated browser login/usage/investigation
flow passed. The ordinary local workbench retains its Chapter 73 browser gate.

## Follow-up: session and feedback storage writes

The separate [storage-write admission increment](Chapter_77_Storage_Write_Limits.md)
now bounds authenticated session creation (including source/check uploads) and
feedback writes. These do not consume run allowances. Daily/per-session limits
are distinct from edge request throttling, lifetime storage and retention; those
remaining gates are not completed by this increment.

The [2026-10-01 process-loss increment](Chapter_98_Process_Loss_Verification.md)
also kills actual admitted subprocesses before result persistence and after a
terminal result commits but before admission release. Both retain their active
slot and daily charge until operator-confirmed release; an already saved report
survives unchanged. This is scratch-database/service evidence, not a hosted worker
or remote-provider reconciliation test.
