# Chapter 98 follow-up: bounded workbench transfers

Implemented locally on 2026-09-30 in the uncommitted `feature/launch-readiness`
branch. This closes a proxy transport gap; it does not complete the broader
background-worker, process-loss or provider-reconciliation gates.

## Behavior

The proxy previously awaited upstream headers and forwarded bodies without an
explicit application deadline. Its framework `maxDuration` setting alone did
not establish bounded behavior for the local standalone server.

The proxy now owns a cancellable transfer with these limits:

| Boundary | Limit |
| --- | --- |
| Ordinary API routes | 30 seconds total |
| Run, clarification response and event-stream routes | 330 seconds total |
| Public authentication preflight | 10 seconds within the total |
| Request upload | 10 seconds within the total; 120,000 bytes |
| Buffered ordinary response | 16 MiB |
| Authentication preflight response | 120,000 bytes |

The total includes authentication, upload, response headers and response body.
Receiving headers or another chunk does not renew it. Ordinary responses are
fully read before forwarding, allowing stalled or broken bodies to fail rather
than delivering partial successful JSON. Event streams remain incremental.
Expiry also unblocks a pending stream write when a consumer stops reading.
Normal completion, errors, disconnects and consumer cancellation dispose timers
and listeners and release the local upstream request.

A deadline produces HTTP 504 before response headers are sent; an unavailable,
broken or oversized upstream response produces 502. An observed incoming abort
uses 499 if a response is still possible. After stream headers were sent, failure
errors the stream; it cannot replace the already-sent HTTP status. Public auth
configuration, route/origin checks, cookie filtering, redirects, Retry-After and
no-store forwarding remain intact. No action is retried automatically.

The browser API client also translates network failures and unreadable JSON into
an uncertain-outcome message. Users are told that work may still be running or
saved and to refresh the session or history before retrying. Existing polling
can recover the persisted result while the page remains open. A lost creation
response may lack a session ID, so history inspection is necessary. This does
not provide idempotency for manually repeated create/feedback actions.

## Execution remains separate from transport

Closing the browser connection or timing out a local fetch does **not** establish
that backend work stopped, that an action was never dispatched, or that a provider
incurred no charge. This change does not cancel backend runners, release durable
run admissions, alter usage or reset budgets. Backend runs configured above the
proxy's wait limit may continue, with reports available through later reads.
Interrupted workers still require the Chapter 77 reconciliation procedure.

Buffer limits can reject a legitimate very large report; operators must inspect
the backend rather than repeatedly retrying the same response. Limits apply per
request, not to total concurrent traffic. Event streams are bounded to 330 seconds
even though the current backend normally ends them after 30 seconds. A slow
runtime event loop can delay timer delivery; these are application deadlines,
not real-time scheduling guarantees. Hosted edge and worker behavior remain
deployment verification work.

Implementation follows standard abort/stream cancellation behavior; see the
[ReadableStream cancellation API](https://developer.mozilla.org/en-US/docs/Web/API/ReadableStream/cancel).
Cancellation of local stream consumption does not certify remote execution state.

## Verification and retained failures

Artifacts are separate from earlier readiness runs under
`runs/launch-readiness/2026-09-30-proxy/` (ignored local files).

- `before.json`: the original proxy failed the stalled-read deadline regression.
- `stream-backpressure-failure.json`: an intermediate implementation failed to
  cancel a stream when the consumer never read. This failure was preserved and
  fixed by explicitly erroring the blocked output on deadline.
- `after.json`: **30 frontend tests passed**, including 22 proxy/client regressions,
  two native-fetch socket tests and the six existing frontend tests. Native tests
  inject 100 ms helper deadlines; route boundary tests use fake time with actual
  configured limits. They are distinct from production-server wall-clock checks.
- TypeScript and the production Next.js build passed. Formatting checks passed
  for changed files.
- Browser verification against a migrated disposable PostgreSQL database:
  **seven local cases passed**, including a real deterministic run whose response
  is replaced with an injected 504. Its saved answer appears and survives reload,
  with exactly one run request. Invite-only and self-service OIDC fixture flows
  each passed. The live-provider browser case was skipped.
- `standalone-stall-results.json`: the actual production Next standalone proxy
  returned 504 for loopback stalled headers and stalled bodies at 30.022 and
  30.028 seconds. Both upstream sockets closed, each after exactly one request.
  `standalone-stall.mjs` preserves the reproduction; it uses the existing local
  build and port 3016, with no backend or provider execution.

The first migration command raced disposable database startup; after readiness
was confirmed, all nine migrations applied. This was a harness startup failure,
not a failed application migration. No model/search provider was invoked, no
deployment was performed, and the unchanged backend suite was not rerun.

The disposable database and local server processes were stopped after verification.
The readiness ledger records the next bounded task. These checks are development evidence, not external security review
or proof of general real-world reliability.
