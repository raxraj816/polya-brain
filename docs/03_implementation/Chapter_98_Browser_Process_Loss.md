# Chapters 66/98 — browser reconnection after backend process loss

Verified locally on 2026-10-02, Asia/Kolkata. Production Next.js build, actual
Uvicorn child processes, disposable PostgreSQL and an independent loopback HTTP
provider. No paid calls, deployment or hosted identity-provider claims.

## Finding and correction

The initial browser probe passed its transport/reconnection assertions, but visual
inspection exposed misleading presentation: after confirmed backend death and
restart, the saved `running` status displayed “Investigation in progress”. The
backend correctly retained an uncertain outcome; its status did not prove that
work remained alive. The original screenshot is preserved.

The workbench now labels that stored status **outcome pending** in history, detail
and the status filter. Its banner says **Awaiting a recorded outcome**, explains
that work may still be running, and says saved status does not confirm live
progress. The persisted API status remains `running`; no liveness field or new
recovery decision was introduced.

Running reports recommend checking trace and refreshing before retrying, with
operator inspection if progress stops. Operator-stopped reports recommend checking
trace and provider activity before a new investigation and explain that releasing
a local slot does not establish external completion or cost. These instructions
also appear in the Markdown export. Existing verification outcomes and allowances
are unchanged; no duplicate execution or automatic release is added.

## Actual browser verification

`frontend/tests/process-loss.spec.ts` starts its own provider and backend through
`backend/tests/fixtures/remote_completion_worker.py`. The fixture supplies a trusted
identity and gates the representation runner on an actual HTTP request; it does
not test OIDC or a commercial provider adapter. The application routes, database,
proxy, report, usage and operator CLI are real.

The browser creates a session and dispatches its run. After the provider records
acceptance, the test kills the backend with SIGKILL. The proxy exposes an uncertain
response; reloading during the outage displays an unavailable-workbench screen.
A fresh backend starts on the same port against the same database. “Retry
connection” restores the saved session without rerunning it. The provider then
finishes independently, but the screen and another reload retain an unverified
pending outcome.

Explicit operator release changes the screen to failed/operator stopped, without
a verified badge. The export retains that status and the external-completion
caveat. A 390-pixel mobile reload preserves it without horizontal overflow.
Exactly **one browser run POST and one provider dispatch** are recorded. Desktop
pending and mobile stopped screenshots were visually inspected.

## Evidence and limits

- New browser case: **1 passed**, 4.5 seconds, after the presentation correction.
- Ordinary workbench regressions: **7 passed, 1 live-provider case skipped**,
  5.7 seconds.
- Backend session service and applicable process-loss checks: **17 passed,
  zero skips, one unrelated checkpoint case deselected**, 4.86 seconds; one
  existing dependency warning.
- **30 frontend unit/socket tests**, TypeScript and production build pass.
- Ruff lint/format and strict mypy for the changed report service pass.
- No unchanged full backend-suite or OIDC-fixture rerun is claimed.

Versioned artifacts are under `runs/launch-readiness/`:
`2026-10-02-browser-loss-initial/` preserves the original misleading screenshot;
`2026-10-02-browser-loss-final/` contains corrected outage, pending and mobile
stopped views plus subprocess witnesses. Matching `.log` files retain results.
`2026-10-02-browser-loss-backend.xml` retains database verification.

The first ordinary-suite attempt mistakenly retained public-origin frontend
configuration while using an authentication-disabled local backend. The proxy
correctly refused it with 503. Four failures, one interrupted case and three
unrun cases remain in `2026-10-02-browser-loss-ordinary/` and its log. Correcting
only the local test configuration produced the seven-pass result in
`2026-10-02-browser-loss-ordinary-final/`. This is a fixture setup failure, not
reclassified passing evidence. No authentication guard was weakened.

The disposable database and both application servers were stopped after testing.
Provider and backend child processes are cleaned up by the browser test. The
campaign spending ledger is unchanged. These are controlled developer checks;
they do not establish real-user usability, external billing reconciliation,
provider idempotency, real identity-provider recovery or hosted restart reliability.
