# Chapter 77 follow-up: request bodies before parsing

Implemented locally in the uncommitted `feature/launch-readiness` branch. The
initial direct API regressions accepted oversized valid JSON with both declared
length and chunked input. Extra JSON whitespace was enough to bypass semantic
field-length checks. Those two failing observations remain in `before.xml` under
`runs/launch-readiness/2026-09-30-body/`.

## Implemented boundary

`RequestBodyLimitMiddleware` is the outermost application middleware, ahead of
authentication, routing, dependencies and JSON parsing. It applies to all HTTP
paths and methods, including unknown routes, public auth routes and local mode.
It admits at most **120,000 decoded body bytes** under a **10-second total upload
deadline**. These defaults match the workbench proxy's request limits.

The gate rejects excessive Content-Length before requesting any body bytes. It
also counts actual chunks, so an omitted or misleading length does not bypass
the cap. It rejects invalid/duplicate lengths, length/transfer-encoding ambiguity
and unsupported transfer encodings when those forms reach ASGI. Compressed
request content is rejected rather than decompressed. The HTTP server remains
responsible for parsing wire framing and removing chunked transfer encoding.

| Result | API response |
| --- | --- |
| Body or declared size over limit | 413; retain input and reduce its size |
| Total upload time exceeded | 408; request was not dispatched |
| Invalid framing or inconsistent length | 400 |
| Unsupported Content-Encoding | 415 |
| Peer disconnect before complete upload | No dispatch or attempted response |

HTTP/1 rejection responses request connection closure, carry no-store/privacy
headers, and do not drain the rejected body. No cookies, quota reservations,
records, provider work or internal rejection records are created by the gate.
HTTP/2/3 responses omit connection-specific headers; actual HTTP/2/3 transport
behavior is not verified by this increment.

An admitted body is delivered unchanged exactly once. Later receive calls retain
the real disconnect signal. The deadline ends before calling the application:
it does not cancel an investigation or truncate a long response/event stream.
Caller task cancellation remains cancellation; it is not swallowed or reported
as a normal timeout. Complete input still passes through normal authentication,
schema validation, ownership and write/run admission.

## Scope and remaining limits

This caps retained body bytes per request, not total process memory or concurrency.
ASGI/server buffers and Python/framework copies have additional overhead. An
already-delivered oversized chunk is rejected without being retained, but its
transport allocation occurred before the gate. Headers, request lines and slow
header transmission precede ASGI and require server/edge controls. Reverse proxies
can normalize framing before the application sees it; this is not a general
request-smuggling certification. A blocked event loop can delay timer delivery;
the monotonic check rejects a late final chunk, but cannot supply real-time
scheduling guarantees or bound downstream JSON parse/handler CPU.

Compression support, aggregate upload concurrency, network request throttling,
login traffic limits, retention and independent load/security review remain open.
No deployment settings were provisioned or changed. This check does not replace
the proxy, execution deadlines, durable quotas or backend recovery controls.

The implementation follows the [ASGI HTTP request/receive contract](https://asgi.readthedocs.io/en/latest/specs/www.html#request-receive-event).
The installed Starlette and Uvicorn receive implementations were also inspected.

## Verification

Local artifacts are isolated in `runs/launch-readiness/2026-09-30-body/` (ignored
files); earlier audits and evaluation failures remain untouched.

- `before.xml`: two failing oversized-input API regressions before implementation.
- `focused.xml`: 53 passing upload and neighboring session API checks. Coverage
  includes byte boundaries with Unicode, framing, no read on declared oversize,
  all methods, chunked counts, no draining, silence/trickle/empty-frame deadlines,
  disconnect, task cancellation, response cookies/streaming and auth/dependency
  exclusion on rejected requests. Short deadlines exercise timers in process.
- `http.xml`: ten real Uvicorn socket checks passed across **h11 and httptools**
  in 22.56 seconds. Both enforce the actual 10-second upload deadline, reject
  oversize before 100 Continue, reject oversized unterminated chunked input,
  accept the exact byte limit, and remain usable after a disconnected upload.
  The route uses an in-memory session fixture; these are transport tests, not
  durable database or model-outcome evaluations.
- `backend-results.xml`: **1,089 backend tests passed, zero skips**, in 101.15
  seconds with real PostgreSQL, all ten migrations and the pinned Docker sandbox.
  There were 843 dependency deprecation warnings, including two surfaced by the
  new native Uvicorn tests. These are not evidence of future dependency compatibility.
- Seven ordinary browser cases plus invite-only and self-service OIDC flows
  passed. Three browser cases were skipped: live-provider execution and the
  one-quota fixture in each auth mode (the latter already passed in the prior
  write-limit increment). No frontend runtime code changed; the existing
  production build was reused, and unchanged frontend unit checks were not rerun.
- Ruff lint/format (229 files) and strict mypy (143 source files) passed.
  Local server processes and the disposable database were stopped afterward.

No paid provider, reviewer, commit, push or deployment is involved. These tests
do not establish public launch readiness or general resistance to denial of service.
