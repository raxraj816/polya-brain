# Chapter 77 follow-up: durable storage-write limits

Implemented locally on 2026-09-30 in the uncommitted `feature/launch-readiness`
branch. Run admission previously left unexecuted session creation and feedback
growth unbounded by a write quota. The initial two API regressions reproduced
both gaps before the change.

## Policy

Authenticated API writes now have separate UTC daily limits:

| Setting | Default | Counted writes |
| --- | --- | --- |
| `POLYABRAIN_DAILY_USER_SESSION_LIMIT` | 50 | Sessions for one owner |
| `POLYABRAIN_DAILY_GLOBAL_SESSION_LIMIT` | 500 | Sessions across authenticated owners |
| `POLYABRAIN_DAILY_USER_FEEDBACK_LIMIT` | 100 | Feedback across one owner's sessions |
| `POLYABRAIN_DAILY_GLOBAL_FEEDBACK_LIMIT` | 1000 | Feedback across authenticated owners |

Ordinary sessions and source/check uploads share the session allowance. A zero
limit closes that write path; it does not block existing reports, history, or
other write kinds. Authenticated feedback also has a fixed lifetime limit of
100 records per session, matching the existing review list. Explicit operator-local
bypass is outside these shared-service limits. Run allowances remain independent.

Daily rejection returns 429 with seconds until the next UTC reset in Retry-After.
A permanent session feedback cap returns 409 without a misleading timed retry.
The existing workbench displays the reason and retains the typed problem or
correction on rejection. The allowance display continues to describe runs only;
write quotas are not presented as provider spend or run credits.

## Transaction and ownership boundary

`WriteAdmissionPolicy` takes a PostgreSQL advisory transaction lock for the write
kind, reads the database clock after lock acquisition, normalizes it to UTC, and
counts current-day records. The caller inserts with the returned timestamp and
commits the row and any source artifact in that same transaction. Four independent
database connections cannot all take the last slot. This uses the repository's
default PostgreSQL READ COMMITTED isolation; all serving workers must use the
same policy and settings. No provider/network work runs inside admission.

Existing durable rows are the successful-write accounting; no duplicate counter,
new cognitive contract or per-rejection database record is introduced. A rollback
consumes no allowance. A committed write remains counted after an application
restart or lost response. Existing same-day data counts immediately when this
policy is enabled. Historical operator-local rows without an owner are excluded
from shared-service totals. Ownership and valid session disposition are checked
before admitting feedback; another account receives 404 even if the quota is full.

Migration `20260930_0010` adds `(user_id, created_at)` on sessions and `created_at`
on feedback, complementing the existing date and session/date indexes. It adds
no fields and rewrites no application records. Index creation must be planned
against real database size/traffic before a future production migration.

## Explicit remaining limits

These are daily retained-write bounds, not lifetime storage or request-rate
limits. They do not bound rejected request traffic, authentication/session-cookie
creation, source availability probes, log volume or provider spending. Direct API
body-size handling is covered by the subsequent
[request-body admission increment](Chapter_77_Request_Body_Admission.md); aggregate
traffic and concurrency still require separate controls.

There is no user deletion endpoint or automatic retention in this increment.
Manual deletion of current-day counted rows would reopen capacity. Future
deletion/retention must preserve current-window accounting, or introduce durable
counters first. Data export/deletion, backup/restore, edge controls and independent
security review remain release gates. This change does not classify human
feedback as verified knowledge or provide idempotency for manual retries.

## Verification

Artifacts are preserved in `runs/launch-readiness/2026-09-30-writes/` (ignored local
files). `before.xml` retains the two original failing API checks. `focused.xml`
records **24 passing database/API checks**: same-user/global last-slot races for
both write kinds, rollback, new connection state, daily rollover, UTC normalization,
zero limits, lifetime feedback capacity, local bypass, shared ordinary/source
allowance, invalid inputs, ownership/anonymous negatives, and source artifact
transaction rollback. Source admission tests stub availability only; they do not
invoke a provider or claim sandbox execution.

Two real OIDC browser fixture flows passed with a one-session/one-feedback daily
limit. They cover login/account isolation and rejection through the production
browser proxy, Retry-After forwarding, retained unsaved input, unchanged history
and continued access to the saved result. No model/search provider was called.
The earlier production frontend build was reused because UI runtime code did not
change. TypeScript, Ruff lint/format and strict mypy passed. The readiness ledger
records the complete backend regression result and final continuation state.

The complete backend suite passed **1,042 tests with zero skips** in 79.54 seconds
against real disposable PostgreSQL and the pinned sandbox image. All ten migrations
applied, including the new indexes on an already populated scratch database.
JUnit is retained in `backend-results.xml`; 841 existing dependency deprecation
warnings remain. Compose configuration validation confirmed that explicitly
setting any of the four write limits to zero is forwarded without replacing it
with a default. No Compose service was started for that check. Local browser/API
processes and the disposable database were stopped after verification.

These are developer tests, not a representative load test or external security
assessment. No commit, push, provisioning or deployment was performed.
