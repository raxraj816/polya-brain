# Chapter 73: Authentication and private workspaces

## Public self-service admission

The release scope now includes public self-service. Set
`OIDC_REGISTRATION_MODE=self_service` with authentication enabled to admit any
identity validated by the configured OIDC provider. The default remains
`invite_only`, which requires `OIDC_ALLOWED_SUBJECTS`. Self-service does not accept
unsigned identities, another issuer's tokens, request-supplied ownership or a
local bypass. The provider must separately support and enable account signup;
PolyaBrain uses its hosted sign-in/signup flow and stores no passwords.

`OIDC_BLOCKED_SUBJECTS` denies exact provider subject IDs in either mode, including
previously issued sessions on their next request. Opaque handles are bound to the
issuer digest and retain 256 bits of random secret. Changing issuer or upgrading
from older unbound cookies requires sign-in again. Only the handle hash is stored.
Workspace and memory ownership, CSRF checks, expiry, daily per-account/global
allowances and concurrency limits continue to apply. Public signup does not
bypass the run-admission service.

The browser shows "Sign in or create account" in self-service mode. Both modes
are exercised with the production frontend and a real signed-token loopback
identity fixture. Run either mode against a migrated scratch database:

```bash
OIDC_REGISTRATION_MODE=self_service scripts/verify_auth_browser.sh
OIDC_REGISTRATION_MODE=invite_only scripts/verify_auth_browser.sh
```

The real hosting domain and identity provider remain undecided by the user.
These local checks establish the application flow, not hosted signup readiness.

PolyaBrain now supports provider-agnostic OpenID Connect sign-in for an explicitly
admitted private beta. Local development can still use the unauthenticated
operator workspace. These are separate namespaces: enabling authentication does
not claim, publish, or share historical local sessions or memory.

## Identity and access boundary

Authlib performs authorization-code exchange, PKCE S256, state, signature,
audience, expiry, and nonce validation. PolyaBrain also pins issuer, validates
identity endpoint transport, restricts signing algorithms to RS256/ES256, requires
a matching nonce, and checks an explicit provider subject allowlist. Only the
`openid` scope is requested. The library integration follows the
[Authlib Starlette guide](https://docs.authlib.org/en/latest/oauth2/client/web/starlette.html).

A successful login rotates a random 256-bit opaque browser credential. Postgres
stores its SHA-256 digest, an issuer/subject-derived identifier, creation time,
and absolute expiry. Provider tokens, names, and email addresses are not stored.
HTTPS uses `__Host-` cookies with Secure, HttpOnly, SameSite=Lax, Path=/ and no
Domain. Loopback HTTP test environments use unprefixed cookies. A separate signed
10-minute cookie carries OAuth transaction state; it is cleared at callback.
Logout revokes the server record. Removing a subject from the configured allowlist
also denies existing sessions on the next request. The default session lifetime
is one hour, configurable from one minute to eight hours.

Every private API route authenticates independently of the UI. Session paths
require owner equality before reading or mutating artifacts, source checks,
feedback, reports, trace/SSE, run, or clarification. History is owner-filtered.
New sessions derive `user_id` from the authenticated principal. Tool and reasoning
records inherit ownership through their durable session foreign key. Authenticated
normal investigations cannot use operator-configured host filesystem roots;
consented source uploads retain their isolated temporary snapshot workflow.

Semantic, episodic, and procedural memory have an `owner_id` persistence field.
Ingestion, source-session validation, deduplication, retrieval, learned preference
updates, and compiled-procedure lookup all use the repository's trusted namespace.
There is no cross-user memory or default sharing of operator seed material.
Migration `20260917_0008` assigns historical memory to `__local__` and extends the
procedure signature uniqueness constraint by owner. A downgrade refuses to merge
private namespaces; use a reviewed backup recovery instead.

The frontend accepts only its configured Host, forwards only authentication
cookies, and rejects cross-origin state changes. The backend independently
requires the exact public Origin and JSON for authenticated actions. Public proxy
configuration refuses to serve an unauthenticated backend. Private API responses
are no-store. Login redirects and multiple Set-Cookie headers are preserved.
Browser query caches are recreated when identity changes and cleared on sign-out
or authentication failure. No credential is stored in JavaScript storage.
These controls follow the [OWASP REST guidance](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html).

## Configure a real identity provider

Set these on the backend (secrets belong in the deployment secret manager):

```text
POLYABRAIN_ENV=production
POLYABRAIN_AUTH_REQUIRED=true
POLYABRAIN_PUBLIC_ORIGIN=https://your-workbench.example
POLYABRAIN_SECRET_KEY=<at least 32 random characters>
OIDC_ISSUER=https://your-provider.example/issuer
OIDC_CLIENT_ID=<registered confidential web client>
OIDC_CLIENT_SECRET=<client secret>
OIDC_ALLOWED_SUBJECTS=<provider subject ID>,<another admitted subject ID>
POLYABRAIN_AUTH_SESSION_SECONDS=3600
```

Register exactly this callback with the provider:
`https://your-workbench.example/api/backend/api/v1/auth/callback`.
The provider must support discovery, authorization code, PKCE S256, and RS256 or
ES256 ID tokens. Client authentication currently uses the Authlib default
`client_secret_basic`; providers requiring a different method need an explicit
reviewed configuration change. The allowlist uses stable subject identifiers,
not email addresses. No wildcard invites or automatic signup are enabled.

Set the same `POLYABRAIN_PUBLIC_ORIGIN` on the frontend and set
`POLYABRAIN_API_URL` to the internal backend URL. Keep the API, Postgres, and Redis
on private networking; terminate HTTPS at the trusted edge. Preserve Host and
Origin; do not expose a bypass backend through a different public route. Suppress
query strings on OAuth callback access logs at the edge. The provided API startup
commands disable raw request access logging for this reason. Do not put OIDC
secrets in `NEXT_PUBLIC_*` variables.

Missing auth configuration fails startup outside `local`/`test`. Local bypass is
for a trusted operator on loopback only (`make dev` and Compose publish to
127.0.0.1). It is not a tenant security mode. Existing local database data stays
accessible only in this operator mode; there is no automatic adoption/migration UI.

## Verification and limits

Backend integration tests use real signed ID tokens through Authlib with a mock
HTTP transport, not a replacement identity validator. They cover invalid state,
nonce, issuer, audience, expiry, signature, uninvited subjects, session rotation,
logout/expiry, allowlist removal, CSRF, source ownership, and cross-user API/memory
isolation. Existing memory and investigation tests continue to pass.

`scripts/verify_auth_browser.sh` runs a loopback-only identity fixture, the real
API, and the production Next.js build against a migrated scratch database. It
checks the complete redirect/PKCE/cookie flow, an arithmetic investigation,
persisted reload, logout, another account's empty history, and denial of the first
account's report. CI runs this separately from the ordinary local-workbench suite.
The fixture's account buttons are test-only; it is not a deployable identity
provider. It never uses the configured live model credentials.

This is application-level ownership enforcement, not Postgres row-level security.
The database credential remains an operator trust boundary. Session expiry or
revocation blocks new requests; it does not cancel an already admitted synchronous
run or its bounded SSE stream (30 seconds). Logout is local to PolyaBrain and does
not log the browser out of its identity provider. Authentication state is checked
again on each private API request and browser focus/polling.

Still required before public beta: provision and verify the actual provider and
HTTPS deployment, daily spending/concurrency controls, operational retention and
backup recovery, monitoring, an independent security review, and fresh technical
and repeat-use evaluations. This local gate does not establish public readiness.

Verified locally: 487 backend tests with migrated Postgres, strict lint/format/type
checks, frontend type checks and unit tests, production build, six ordinary browser
tests, and the separate full OIDC browser test. No live model calls were made for
this chapter. Linux CI runs these gates after push; the actual hosted provider
and public HTTPS deployment remain unverified.
