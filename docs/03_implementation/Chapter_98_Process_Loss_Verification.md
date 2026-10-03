# Chapter 98: actual process-loss verification

Verified locally on 2026-10-01. This increment adds six subprocess regression
tests and a test-only fault fixture. Application runtime behavior is unchanged.

## Fault boundaries and outcomes

The parent test waits for a child to confirm the exact boundary through a pipe,
then sends SIGKILL and waits for the OS exit status. Python exception handling and
`finally` cleanup cannot supply durability. Test cleanup only terminates its own
subprocess and uses an isolated recovery directory and PostgreSQL database.

| Boundary | Verified outcome |
| --- | --- |
| Durable in-flight marker, before calculator dispatch | No dispatch occurred, but replay is conservatively refused because the checkpoint cannot prove that fact |
| Inside calculator wrapper after a durable dispatch witness | Replay refused; in-flight and unconsumed markers remain after repeated attempts |
| Calculation completed, before its result checkpoint | Durable completion witness exists, but replay remains refused because the result was not committed to the recovery store |
| Calculator result checkpoint committed | Live cross-process lease blocks a competitor; death releases the lease; continuation preserves budget/usage, reaches the same verified arithmetic answer and does not repeat calculation; parent and terminal child cannot be reused |
| API run admitted, before result persistence | Fresh database connection observes the retained active slot and daily charge; replacement work is denied before dispatch; operator-confirmed release marks the interrupted run failed without refund |
| API result persisted, before admission release | Result remains readable and unchanged; active slot remains until operator-confirmed release; daily charge remains; a subsequent run consumes the next allowance |

The public operator CLI is also exercised: release without confirmation is refused.
The fixture supplies confirmation only after the child is confirmed dead. Duplicate
attempts to run the original session do not dispatch again. The saved API result
uses the actual offline arithmetic runtime, not a fabricated passing model response.

## Evidence

`backend/tests/test_process_loss_recovery.py` contains the six checks;
`backend/tests/fixtures/process_loss_worker.py` is the subprocess-only fault fixture.
It uses explicit offline settings and never exposes an application endpoint.

**Six tests passed, zero skips**, with a disposable migrated PostgreSQL database.
Ruff lint and formatting pass for both new files. No application source changed,
so unchanged full backend/frontend suites were not repeated. At that increment, the complete
backend suite remained the previous 1,107-test result; no 1,113-test full suite
was claimed. The subsequent 1,142-test full result is recorded in the readiness ledger.

Evidence is retained under `runs/launch-readiness/2026-10-01-process-loss/`:
`second.xml`/`second.log` contain the passing run; `second-temp/` retains the actual
private checkpoint stores and dispatch/completion witnesses. The initial fixture
configuration exceeded the allowed global-concurrency setting and failed before
any fault boundary; its four failures and two DB skips remain in `initial.xml`
and `initial-temp/`. The fixture was corrected to the existing allowed maximum.
No failed observation was reclassified as an application success.

Reproduction with a migrated scratch database:

```sh
POLYABRAIN_RUN_DB_TESTS=1 .venv/bin/pytest backend/tests/test_process_loss_recovery.py
```

Provide `DATABASE_URL` for that scratch database and clear provider credentials.
The test starts and kills only its own child processes. The disposable database
was stopped after verification; no production worker or admission was touched.

## Limits and next evidence

These tests exercise local POSIX process death, local SQLite checkpoints,
PostgreSQL admissions and the service/operator boundaries. They do not establish
remote provider cancellation, billing reconciliation, host power-loss/fsync
guarantees, database failover, HTTP/browser behavior during backend death, or
hosted worker operations. The action witness is a deterministic local calculation,
not a remote paid call. The loopback-provider follow-up below now covers work that survives worker death;
it must not be equated with provider-account or production reconciliation.


## Chapter 98 follow-up: provider completion after caller death

Verified 2026-10-02, Asia/Kolkata. A separate HTTP provider process accepts an
actual loopback request, durably records acceptance, and waits on a parent-owned
completion gate. The test confirms acceptance before sending SIGKILL to the
caller, confirms its death, then permits the independent provider to complete.
The provider records completion after that death even though the caller never
receives the response. There are no paid calls or external network requests.

Two additional tests pass, zero skips, in separate focused invocations:

| Boundary | Observed result before and after provider completion |
| --- | --- |
| Private recovery checkpoint | Repeated load attempts reject uncertain outcome/cost; in-flight remains set and consumed remains false; exactly one provider request |
| PostgreSQL API run admission | Original session rejects duplicate execution; another session is denied by active-run allowance before dispatch; daily count and active count both remain one; no passing report or conclusion appears |

After completion, the API probe invokes the real operator CLI with confirmed
worker termination. The slot is released, the daily count stays one, and the
interrupted report becomes `operator_stopped`. There is still exactly one provider
request. The provider process remains independent throughout; killing the caller
cannot be interpreted as cancelling its remote work.

Implementation is exclusively in
`backend/tests/fixtures/remote_completion_worker.py` and
`backend/tests/test_remote_completion_recovery.py`. The fixture sends HTTP inside
a disposable capability/service runner; it does not replace a production provider
adapter or implement a new cancellation or reconciliation mechanism. Existing
runtime source and admission behavior are unchanged.

Artifacts: `runs/launch-readiness/2026-10-02-provider-completion/` contains
`local.xml` (1 passed, 1 deselected, 1.46 seconds), `api.xml`/`api.log`
(1 passed, 1 deselected, 1.90 seconds), and the retained `local-temp/` and
`api-temp/` checkpoint/dispatch/completion witnesses. Each invocation emitted one
existing LangChain deprecation warning. Ruff lint and formatting pass. A fresh
PostgreSQL database applied all ten migrations and was stopped afterward.
Unchanged passing full backend and frontend checks were not repeated.

These checks do **not** prove real-provider cancellation, API-key billing limits,
invoice reconciliation, transport retry behavior of a particular provider SDK,
remote idempotency or hosted worker recovery. In particular, retained daily
admission is an invocation allowance, not a dollar charge. Next evidence should
cover actual backend HTTP-process loss and browser reconnection, while maintaining
this distinction between an uncertain remote outcome and a locally verified one.


## Chapter 98 follow-up: actual HTTP backend loss and restart

A third focused test now starts Uvicorn in a disposable child process and uses
real HTTP to create two sessions and start a run. After the independent provider
acknowledges dispatch, the test kills the entire Uvicorn process with SIGKILL; the
HTTP client observes a transport failure. A fresh Uvicorn process connects to the
same PostgreSQL database before the provider is permitted to finish.

Before and after late provider completion, actual HTTP reads return the original
session as `running`, with no final conclusion and no passing verification.
Duplicate execution returns **409**; another session's run returns **429** while
its user's active slot is retained. The usage endpoint reports one daily invocation
and one active run. After explicit operator release, the restarted backend reports
`failed`/`operator_stopped`, zero active runs and the same daily count of one.
The provider's durable witness records exactly one request throughout.

`http.xml`/`http.log` record **1 passed, 2 deselected**, 3.09 seconds, with one
existing dependency warning. `http-temp/` retains provider witnesses and distinct
logs for both backend processes. Together with the earlier two invocations, these
are **three new distinct passing tests, zero skips**, not a repeated full-suite
claim. The scratch database was stopped again after this probe.

The fixture supplies a trusted principal and replaces only the representation
runner with the gated HTTP call. Session routes, persistence, usage/admission and
operator release are real. This does not test OIDC, a real provider adapter,
external billing, browser rendering, or a deployed service restart. Browser
reconnection to these persisted uncertain/failed states is now verified separately
in [the browser follow-up](Chapter_98_Browser_Process_Loss.md).
