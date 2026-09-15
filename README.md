# PolyaBrain

PolyaBrain is a brain-inspired problem-solving intelligence system. It is a
cognitive workbench that helps a person understand, investigate, solve, verify,
and learn from difficult problems. It makes reasoning visible, evidence
inspectable, uncertainty explicit, resource use auditable, and learning
reusable.

PolyaBrain is a product-first, initially cloud-hosted, model-agnostic Cognitive
Runtime that turns difficult objectives into verified outcomes. It acquires
knowledge on demand, uses deterministic procedures whenever possible, invokes
bounded model reasoning when necessary, and learns reusable procedures from
verified work.

It is not a generic chatbot, a foundation model project, or a biological brain
simulation. PolyaBrain owns the problem-solving control loop; language models,
search, memory, code, calculators, databases, simulators, documents, APIs, and
human input are replaceable capabilities it can select. The product goal is to
help users understand, investigate, solve, verify, and learn from hard problems
through an auditable loop:

```text
problem input -> representation -> constraints -> gaps -> evidence/tools
  -> hypotheses -> plan -> execution -> verification -> reflection -> report
```

The initial user-facing product is **PolyaBrain Investigator**, a verified
technical problem-solving workbench. The enduring core is the **PolyaBrain
Cognitive Runtime**. A managed cloud product and API are the initial delivery;
the runtime remains portable to sovereign cloud, private cloud, and local
execution. **PolyaBrain Intelligence OS** is an eventual platform category to
claim only after applications and developers depend on the runtime and the same
kernel has cross-domain proof. General-purpose intelligence is the architectural
ambition, not a current superiority claim.

The binding product decision and win standard are in
[`PolyaBrain_Product_Implementation_Master_Plan.md`](PolyaBrain_Product_Implementation_Master_Plan.md#1-product-decision).

## Current Status

This branch completes Phase 1 through the Chapter 10 API shell and advances
Phase 2 through the Chapter 12-B production OpenRouter adapter and Chapter 13
Problem Representation Engine on top of the
Chapter 9 event trace system, Chapter 8 LangGraph skeleton, Chapter 7 engine
interface contract, Chapter 6 LangGraph state object, Chapter 5 core Pydantic
contracts, Chapter 4 database baseline, Chapter 3 local development
environment, and the verified pre-platform proof harness. The Phase 1 debt
closure pass leaves no open implementation debt for completed Phase 0 or Phase 1
chapters. Chapter 12-A adds a deterministic fake LLM client, typed request and
response contracts, JSON-mode capability checks, bounded retry/backoff, token
usage, and sanitized errors. Chapter 12-B adds the environment-configured,
privacy-aware OpenRouter adapter with normalized errors and usage metadata.
Chapter 11 adds a versioned problem-understanding prompt, strict JSON schema,
ten validated local examples, deterministic parsing, bounded repair, mode
selection, clarification routing, and mapping to the existing canonical
`StructuredProblem` contract. Chapter 13 turns those boundaries into the first
real engine, including narrow deterministic fallbacks, stage-gated clarification,
auditable framing and mode events, and validated `structured_problems`
persistence.

Chapter 14 adds a real constraint-discovery engine between representation and
later problem solving. It extracts explicit and implicit requirements, asks for
missing decision boundaries, persists accepted constraints in the canonical
problem, prevents capabilities without sensitive-data approval from handling
privacy-constrained work, and refuses a passing verification report that does
not cover every declared success criterion. Chapter 15 makes the earlier
clarification route durable and resumable through the API and event stream.

Chapters 16-20 add governed long-term memory. Semantic knowledge retains source,
domain, reliability, freshness, tags, admission status, and embedding
provenance; episodic cases are admitted only after verification and reflection;
procedural outcomes are learned idempotently from verified runs. The controller
can recall sourced knowledge and verified strategies, but present-case
verification still decides. Read-only memory APIs expose all three stores, and
the curated five-document seed passes 20 cross-domain retrieval queries.

The persisted cognitive runtime also has its first real outcome path. Exact
binary arithmetic runs through gap detection, calculator evidence, hypothesis,
plan, execution, verification, reflection, and a controller-owned stop without
using an LLM for work a deterministic procedure can do. Model-backed capabilities
cover the same structured boundaries for harder problems and fail closed on
invalid output or provider errors. Accepted gaps, evidence, hypotheses, plans,
verification, and reflection are durable, and
`GET /api/v1/sessions/{session_id}/report` exposes the auditable result.

Chapters 22 and 26 add the first controlled external knowledge-acquisition
path. The gap detector sees only configured data sources. When Brave Search is
configured, the controller can run a gap-tied query under durable session
budgets, stage results as untrusted candidates, and invoke a separate evaluator
before any result becomes canonical evidence. Two independent sources are
required to fill a web-derived gap, and factual verification is still required.
The same staged-evidence boundary supports explicitly referenced local text
files contained by configured roots; it never performs an implicit directory
scan or executes file contents as instructions.
Chapter 29 adds claim-level evidence assessment: grounded extraction,
support/contradiction/background classification, relevance, reliability,
freshness, near-duplicate removal, cross-source corroboration, and checks
against evidence already persisted for a resumed session.
The first deterministic measurement tool reads only explicitly referenced
CSV/JSON tables under configured roots and produces exact distributions,
percentiles, missing-value counts, and categorical frequencies with file
provenance.
Chapter 33 adds optional isolated Python execution and structured assertion
tests in a digest-pinned, networkless, read-only, resource-limited container.
The planner sees this tool only when it is enabled.
Deterministic execution also includes grouped/in-memory SQL table analysis,
explicit sensitivity scenarios, and bounded control-versus-treatment effect
evaluation. Missing simulation or experiment observations trigger a user pause
instead of model invention.

Chapter 13-C is in progress as the first general cognitive-control proof. Its
experimental controller selects the next action from explicit `PolyaState`,
executes only through registered capabilities, treats capability results as
observations, changes action after failure, and requires verification plus
reflection before a completed stop. The offline proof exercises the same
controller across ten problem categories without using an LLM as the
controller. The structural and first-action live proofs are complete;
production-loop integration now includes governed memory and the minimum
acquisition/execution tools. The six-category full-outcome harness is
implemented and offline contract-tested with equal state, model, tools,
observations, call budget, output-token limit, and alternating execution order.
After correcting strict provider-parameter compatibility, the configured paid
route completed one post-fusion repetition across all six same-model/same-tool
outcome categories. Both Polya and direct passed 6/6; Polya used 32,725 tokens
and 8.93 seconds mean latency versus direct's 14,945 tokens and 5.10 seconds.
Polya saved one model call in the recovery case, but the overall run is not a
win. Chapters 13-I and 13-J address the two exposed gaps: redundant
post-evidence semantic work and adversarial evidence/uncertainty control.

Chapter 13-I now closes fully attested deterministic tool results before
semantic cognition. In the repeated 18-pair same-information live gate, Polya
completed 18/18 with zero model calls and zero tokens; direct completed 17/18
using 47,656 tokens. The general gate remains false because the correctness
advantage is only 5.56 points, below the predeclared 10-point threshold. This is
a narrow compute win for trusted typed procedures, not general superiority.

Chapter 13-J adds trace-derived residual evidence requirements and adaptive
search revision for corroboration, freshness, authority, conflict, and
discriminating evidence. In a repeated 24-pair synthetic adversarial gate,
Polya and direct both passed 24/24; Polya used 24 versus 69 model calls, 70,613
versus 103,583 tokens, and 4.16 versus 7.74 seconds mean latency. This is a
narrow quality-adjusted compute win over one same-model baseline. Blinded human
review and non-synthetic field cases remain pending, so it is not a broad
product-value or general-intelligence claim.

Chapter 13-D adds the trace-derived task model, hard cognitive resource ledger,
deterministic explicit-gap construction, fused bounded model stages, and the
first zero-model-call exact-artifact proof. Chapter 13-E adds an experimental
verifier factory and procedure compiler: known criteria become independent
executable checks, successful verified traces become integrity-protected
procedure proposals, and replay, applicability, capability-version, safety, and
present-case verification gates prevent automatic trust. These are implemented
mechanisms; broad held-out outcome superiority remains unproven.

Chapter 13-F adds bounded adaptive capability scheduling. Runtime traces now
separate operational success from contribution to a completed verified outcome,
retain duration and resource use, and build version-scoped health profiles. The
controller can prefer a healthier eligible route, but only after availability,
privacy, safety, and hard-budget gates. Across 60 held-out scheduler decisions,
adaptive routing produced 60/60 verified route outcomes versus 45/60 for the
static controller, while reducing external calls from 60 to 45 and modeled
capability latency from 160.5 seconds to 43.2 seconds. This is a
scheduler-specific deterministic win, not an end-to-end intelligence claim.

Chapter 13-G makes time a hard cognitive resource. Model attempts, retry
backoff, and structured-output repair share a total capability deadline;
model-backed capability versions include the configured route fingerprint.
Normal runs and compiled procedures reserve declared timeout before execution,
charge measured duration afterward, and stop with an auditable
`insufficient_evidence` result when the run deadline is exhausted.

Chapter 13-H makes model endpoints replaceable semantic processors behind
controller-registered cognitive capabilities. Polya deterministically orders
one primary and at most one explicit fallback using capability-specific route
health, preserves fallback time inside one hard deadline, opens recoverable
circuits after repeated typed failures, and charges every retry and repair call.
Route attempts are trace-visible without copying prompts or raw provider
responses. This is a resilience and accounting mechanism, not a reasoning-
quality win. Initial representation now uses the same broker and hard deadline,
so failed retries and parser repairs are counted before any later cognitive
action begins.

The repeated Chapter 13-E live verifier gate is complete: across 18 held-out
multi-rule/debugging verification checkpoints, Polya scored 18/18 with zero
false passes and zero model tokens. Direct-model and full-context checkers also
scored 18/18 using 23,944 and 26,978 tokens; fixed ordinary retrieval scored
8/18 using 30,901 tokens. This is a narrow known-verifier quality-cost win.
End-to-end general problem-solving superiority and real procedure-transfer
savings remain open gates.

Verified compiled procedures now have a governed runtime executor. Proposals
can run only in replay mode to generate their own verification evidence; two
distinct passing replays are required for promotion. Production execution
rechecks applicability, safety, capability versions, approval, sensitive-data
permission, budgets, typed observations, and the present-case verifier. A
failed transfer produces no final answer.

Run the actual Cognitive Runtime locally (Python 3.14; `make setup` first):

```bash
./polyabrain investigate "What is 17 * 6?" --offline
./polyabrain investigate "Fix it." --offline
./polyabrain investigate "Your technical problem and available evidence" --max-model-calls 12
```

The CLI writes private Markdown and JSON artifacts under `runs/investigator/`:
actual state, evidence, hypotheses, plan, execution, verification, reflection,
trace, resource usage, code provenance, and SHA-256 manifest. Existing run
directories are never overwritten. `--offline` enforces zero model/search
calls; an unrecognized task stops with insufficient evidence. Semantic work
uses the existing `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` configuration.
Use `--artifact-root /path/to/folder` to permit explicitly referenced files;
code execution remains disabled unless `--allow-code-execution` is supplied.

For an explicit Python source/check investigation, the experimental workflow
proposes one bounded edit and checks failing-original / passing-candidate behavior:

```bash
./polyabrain investigate "Explain the defect and propose a minimal correction" \
  --source /path/to/case/source.py --check /path/to/case/check.py \
  --artifact-root /path/to/case \
  --experimental-source-patch --allow-code-execution --max-model-calls 4
```

The check defines `verify(implementation)`. Original files remain unchanged;
the run exports the candidate edit and both check results. This is supplied-check
coverage, not independent causal or hostile-code verification. See
[Chapter 13-N](docs/03_implementation/Chapter_13N_Source_Visible_Investigation_Delivery.md).

Exit codes: `0` verified completion, `2` clarification or invalid CLI syntax,
`3` no verified outcome, `1` configuration/runtime failure, `130` interruption.
Use `--json` for a machine-readable summary. No database service is required:
local checkpoints use private SQLite storage under `~/.local/state/polyabrain`.
Continue a cycle pause, or answer a missing-input pause with a full revised problem:

```bash
./polyabrain investigate "What is 17 * 6?" --offline --max-cycles 3 --run-id arithmetic-start
./polyabrain resume runs/investigator/arithmetic-start --offline --run-id arithmetic-finish
./polyabrain investigate "Fix it." --offline --run-id clarification-start
./polyabrain resume runs/investigator/clarification-start --offline --answer "What is 17 * 6?"
```

Use the same runtime options, code, and configuration when resuming. Resource
budgets carry forward, earlier reports remain intact, and a checkpoint can be
continued once. Interrupted in-flight calls require investigation before a new
run; they are never automatically replayed. Durable learned memory remains in
the API workflow. See [Chapter 13-M](docs/03_implementation/Chapter_13M_Recoverable_Local_Investigations.md)
for recovery boundaries and private-store retention.

See [Chapter 13-L](docs/03_implementation/Chapter_13L_Investigator_Runtime_Delivery.md)
for examples, verification scope, and remaining delivery work. A local workbench
now supports persisted reports, live recorded activity, evidence, hypotheses,
history, export, clarification, and feedback. See [frontend setup](frontend/README.md)
and the [workbench verification record](docs/03_implementation/Chapter_61_70_Local_Investigator_Workbench.md).
The public cloud product and independent product-value gate remain open.

To use the local UI, run `make migrate && make dev`, then in another terminal
run `make frontend-install && make frontend-dev`. Open `http://127.0.0.1:3010`.
Alternatively, `docker compose up --build --wait` starts the full local stack.
Ports bind to localhost; no authentication or tenant isolation is claimed.
The browser also supports experimental Python source/check investigations with
explicit consent and a local host backend enabled for sandbox execution. See
[Chapter 13-O](docs/03_implementation/Chapter_13O_Browser_Source_Check_Delivery.md)
for setup, exact-snapshot handling, and the supplied-check verification boundary.

Run the legacy curated-template demonstration explicitly:

```bash
./polyabrain proof "Our API p95 latency jumped after deploy. Should we add Redis or inspect the query path first?" --clean
python3 proofs/pre_platform/verify_pre_platform_proof.py --run-dir proofs/pre_platform/runs/our_api_p95_latency_jumped_after_deploy
```

Start the backend locally:

```bash
make dev
curl http://127.0.0.1:8000/health
```

Fetch a persisted session trace:

```bash
curl http://127.0.0.1:8000/api/v1/sessions/{session_id}/events
curl 'http://127.0.0.1:8000/api/v1/sessions/{session_id}/events?limit=50&after_sequence=99'
curl -N http://127.0.0.1:8000/api/v1/sessions/{session_id}/events/stream
```

Create and run a persisted cognitive session:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sessions \
  -H 'content-type: application/json' \
  -d '{"raw_input":"Investigate why p95 latency jumped after deploy.","mode":"investigate","domain":"software_debugging"}'

curl -X POST http://127.0.0.1:8000/api/v1/sessions/{session_id}/run
curl -X POST http://127.0.0.1:8000/api/v1/sessions/{session_id}/respond \
  -H 'content-type: application/json' \
  -d '{"answer":"Reduce checkout p95 below 300 ms without increasing errors."}'
curl http://127.0.0.1:8000/api/v1/sessions/{session_id}
curl http://127.0.0.1:8000/api/v1/sessions/{session_id}/report
curl http://127.0.0.1:8000/api/v1/sessions/{session_id}/events
```

Run the local checks:

```bash
make lint
make test
make proof
make chapter11-proof
make cognitive-proof
```

Run the Chapter 13 live technical-investigation comparison with a configured
OpenRouter key and model:

```bash
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
.venv/bin/python evals/chapter_13/run_live_investigations.py
```

Those overrides are required by the configured free evaluation endpoint and
must be used only with non-confidential fixtures. Production defaults remain
fail-closed.

Run the non-confidential Chapter 13-C live next-action comparison:

```bash
POLYABRAIN_ALLOW_NONCONFIDENTIAL_LIVE_EVAL=1 \
OPENROUTER_DATA_COLLECTION=allow \
OPENROUTER_REQUIRE_PARAMETERS_FOR_JSON=false \
.venv/bin/python evals/chapter_13c/run_live_action_baseline.py
```

This comparison evaluates only state-dependent next-action selection. It is not
an end-to-end outcome benchmark.

Run the offline Chapter 13-F adaptive scheduler comparison:

```bash
PYTHONPATH=backend .venv/bin/python \
  evals/chapter_13f/run_adaptive_scheduler_benchmark.py \
  --repetitions 5 --write-artifact
```

Start the containerized local stack:

```bash
make docker-up
make migrate
make db-smoke
make db-test
make docker-down
```

`make db-smoke` verifies the Chapter 4 schema and inserts local seed data only in
local/test environments or with `POLYABRAIN_ALLOW_DB_SEED=1`. Chapters 5, 6, 7,
and 8 add contracts, graph primitives, engine primitives, and graph skeleton
orchestration and do not require a database smoke check.

Verify all stored proof runs:

```bash
python3 proofs/pre_platform/verify_pre_platform_proof.py --all
```

The proof harness writes local artifacts for trace, evidence, hypotheses, verification, report, and direct baseline comparison. It exists to prove product value before building the full FastAPI/Postgres/Redis/Next.js platform.

## MVP Scope

The first product wedge is a technical investigation workbench for founders, engineers, researchers, and technical product builders.

The MVP must expose:

- final conclusion
- confidence level
- evidence used
- evidence against
- checks performed
- open questions
- recommended next action
- audit trace

The system must preserve uncertainty and say when evidence is insufficient.

## Repository Layout

```text
backend/      Python/FastAPI backend, health route, Alembic, DB models, seed/smoke checks.
frontend/     Local Next.js Investigator workbench and browser checks.
infra/        Infrastructure notes; Docker Compose lives at repo root.
scripts/      Local developer scripts and notes.
evals/        Benchmark and evaluation runners plus reproducible run artifacts.
docs/         Vision, architecture, implementation, examples, and research notes.
proofs/       Executable pre-platform proof harness and generated proof artifacts.
polyabrain    Local CLI entrypoint for proof workflows.
```

## Source Of Truth

Read these first before major implementation work:

1. `docs/03_implementation/Chapter_1_Start_Here.md`
2. `PolyaBrain_Product_Implementation_Master_Plan.md`
3. `docs/00_vision/Cognitive_Product_Doctrine.md`
4. `docs/03_implementation/Product_Acceleration_Playbook.md`
5. `docs/01_architecture/MVP_Architecture_Decisions.md`
6. `docs/01_architecture/Core_Data_Contracts.md`
7. `docs/02_examples_and_benchmarks/Benchmark_Categories.md`

When documents disagree, follow `PolyaBrain_Product_Implementation_Master_Plan.md`.

## Local Setup

The proof harness runs without platform services. The backend runs locally with
Python, and the full local service stack runs with Docker Compose.

Requirements:

- Python 3.14. The repository defaults to Python 3.14 through
  `.python-version`, matching the current local development interpreter.
- Bash-compatible shell
- Docker, for Postgres, Redis, and backend composition

Optional:

- `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` for the production adapter and
  live Chapter 13 comparison
- `OPENROUTER_FALLBACK_MODELS` for an optional single explicit semantic
  fallback used only after typed retryable or schema failures
- `OPENAI_API_KEY` for the earlier OpenAI direct-model proof baseline

Run the local proof:

```bash
./polyabrain proof "Investigate why a background job started timing out after a dependency upgrade." --clean
python3 proofs/pre_platform/verify_pre_platform_proof.py --all
```

## Environment

Copy `.env.example` to a local `.env` when platform or live baseline work needs credentials. Never commit real secrets.

## Chapter Plan

Implementation is chapter-based, not date-based.

Chapters 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12-A, 12-B, 13, 13-D, 13-E, 13-F,
13-G, 13-H, 13-I, 13-J, 14, 15, 16, 17, 18, 19, 20, 22, 26, 29, 30, 33, and 34 are complete
in the current working tree. Chapters 13-C, 31, and 35 are in progress. The
Phase 1 debt closure pass is complete.

The next implementation sequence is:

1. Chapter 28: fetched web-document extraction and richer uploaded-document
   parsing; bounded local text-artifact inspection is already available.
2. Close the remaining Chapter 31 tool-schema metadata and Chapter 35 symbolic,
   unit, statistical, and logic helpers.
3. Complete Chapter 13-C with a fair end-to-end tool-enabled outcome comparison.

Chapter 13 follows the Phase 2 persistence policy in
`docs/01_architecture/Phase_2_Engine_Output_Persistence.md`: accepted validated
output is canonicalized, while clarification and rejected paths remain in the
trace without creating a canonical row.

See `docs/03_implementation/Phase_2_Action_Items.md` and
`docs/03_implementation/Chapter_Backlog.md` for the active local backlog.
