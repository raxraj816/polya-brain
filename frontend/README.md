# PolyaBrain Investigator workbench

A local Next.js workbench backed by actual Cognitive Runtime sessions in Postgres.
It submits investigations, displays recorded activity and resource use, exposes
source evidence and ranked hypotheses, exports reports, restores session history,
and records human feedback for manual review.

## Run locally

Requires Node.js 24 and the Python 3.14 backend with migrated Postgres. From the
repository root:

```sh
make migrate
make dev
```

In another terminal:

```sh
make frontend-install
make frontend-dev
```

Open http://127.0.0.1:3010. The server-side proxy defaults to
`http://127.0.0.1:8000`; set `POLYABRAIN_API_URL` to use another local backend.
Provider credentials belong only in the backend environment, never in a
`NEXT_PUBLIC_` variable. A deterministic smoke input is `What is 17 * 6?`.
Model-backed investigations require the backend's existing OpenRouter settings.

Alternatively, `docker compose up --build --wait` runs the UI, backend, migrations,
Postgres, and Redis. Ports bind to localhost. Use `POLYABRAIN_DB_PORT`,
`POLYABRAIN_REDIS_PORT`, `POLYABRAIN_API_PORT`, and `POLYABRAIN_UI_PORT` to avoid
conflicts with existing local services. Container builds exclude private inputs,
provider credentials, and local investigation artifacts.

## Verification

```sh
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend exec -- playwright install chromium
# With backend and frontend running against a disposable migrated database:
npm --prefix frontend run test:e2e
```

Browser tests create real sessions and feedback. Use a disposable database rather
than a production or shared database. `PLAYWRIGHT_BASE_URL` can override the UI
address. CI runs the tests against a production frontend build and a real backend.

## Current boundaries

- Local, single-workspace preview; no authentication or tenant isolation. The UI
  and proxy accept localhost access only. Do not expose the backend publicly.
- Investigate, Compare, and Review are wired into framing and downstream prompt
  guidance. Optional time, metric, and entity context is preserved as user input.
  Mode selection cannot bypass evidence or verification requirements. Substantive
  mode-specific quality still requires fresh evaluations.
- Trace uses one-second polling while a run is active. Events persist at runtime
  checkpoints; evidence and hypotheses persist when the run pauses or finishes.
  Stage markers indicate recorded activity, not success. Trace metadata contains
  measured resource use; billing is not inferred from these numbers.
- A failed or interrupted request is never automatically replayed. Refresh the
  saved session to inspect the outcome. Only created sessions expose Start.
- Clarification posts additional context to the existing API resume workflow;
  canonical questions survive reload. This is not the CLI's private SQLite
  recovery mechanism or provider-call reconciliation.
- Source/check investigations are available in the UI with explicit consent and
  an enabled local host backend (`CODE_EXECUTION_ENABLED=true`) that can access
  Docker and the pinned sandbox image. The general Compose backend does not
  receive a Docker socket. See [Chapter 13-O](../docs/03_implementation/Chapter_13O_Browser_Source_Check_Delivery.md).
  Inputs are retained as exact snapshots in the local database, and candidate
  diffs are checked against recorded execution hashes. No original file is edited.
- Feedback is append-only and scoped to a session. History feedback filters form
  a manual review list. Corrections never silently overwrite evidence, conclusions,
  or learned verified procedures. Review disposition and identity are pending.
- Hypotheses show stored confidence, not an invented confidence-change chart.
  Source handles are clickable only for HTTP(S); local handles remain text.

The UI is a way to collect real usage evidence, not proof that PolyaBrain has
passed the broader alpha or product-value gates.


The optional live source browser test uses the configured provider and Docker:

```sh
POLYABRAIN_TEST_LIVE_SOURCE=1 npm --prefix frontend run test:e2e -- --grep "source upload" --timeout 210000
```

Run it only against a disposable local workspace with a configured provider. It
verifies a known synthetic defect and is not an independent quality benchmark.
