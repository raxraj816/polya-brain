# Chapter Backlog

This is the local implementation tracker until a project board exists. The source of truth remains `../../PolyaBrain_Product_Implementation_Master_Plan.md`.

## Chapter 1: Product Lock And Repository Foundation

Status: complete on `feature/chapter-1-foundation`.

Done:

- Product source of truth exists in the master plan.
- Chapter 1 start document exists.
- Cognitive doctrine, architecture decisions, data contracts, benchmark categories, and acceleration playbook exist.
- Pre-platform proof harness runs through the local CLI.
- Stored pre-platform proof runs verify with deterministic checks.
- Repository foundation files exist for README, environment template, editor config, pre-commit config, and planned top-level directories.
- Local chapter backlog exists until a GitHub project board is needed.
- Final verification pass completed with `python3 proofs/pre_platform/verify_pre_platform_proof.py --all`.
- No real secrets are stored in the environment template.

Exit criteria:

- Repo can be cloned by a new developer.
- MVP scope is visible in the README.
- No secret values are committed.
- Local proof command is documented and verified.

## Chapter 2: Architecture Decisions And Risk Register

Status: complete on `develop`.

Done:

- Added `docs/architecture_decisions.md`.
- Added `docs/risk_register.md`.
- Added lightweight ADR template at `docs/adr/0000-template.md`.
- Recorded reasons for PolyaBrain core-first architecture, Python/FastAPI modular monolith first, Postgres plus pgvector first, LangGraph orchestration, Redis runtime support, Next.js workbench UI, use-case pack boundaries, typed contracts and stage gates, reasoning versioning, tool registry safety, mixed benchmark categories, and the pre-platform proof as a regression anchor.
- Documented mitigations, owners, signals, verification paths, and residual risks for hallucination, bad data, LLM cost, PII leakage, tool misuse, infinite loops, poor UX trust, scope creep, benchmark skew, provider dependency failure, and secrets/configuration mistakes.
- Updated docs map with the Chapter 2 artifacts.

Exit criteria:

- Every major architecture choice has a reason.
- Every critical risk has an owner and mitigation.

## Chapter 3: Local Development Environment

Status: complete on `feature/chapter-3-local-dev-env`.

Done:

- Create Python backend package and dependency files.
- Added FastAPI, Pydantic v2, SQLAlchemy, Alembic, pytest, ruff, mypy, LangGraph, Redis client, and Postgres driver.
- Added Docker Compose for Postgres with pgvector, Redis, and backend.
- Added Makefile commands for setup, dev, test, lint, format, typecheck, migrate, Docker up/down, and proof verification.
- Added `/health` endpoint with typed response and tests.
- Added GitHub Actions CI for lint, tests, and proof verification.
- Added Alembic scaffold without Chapter 4 schema migrations.
- Updated backend, infra, README, and implementation notes for Chapter 3.

Verification:

- `make lint`
- `make test`
- `make proof`
- `make dev` plus `curl http://127.0.0.1:8000/health`
- `docker compose config --quiet`
- `make docker-up` plus `curl http://127.0.0.1:8000/health`
- `make migrate`
- `make docker-down`

Exit criteria:

- `make dev` starts the backend locally.
- `make test` passes.
- CI lint and test workflow exists for a clean checkout.

## Chapter 4: Database Baseline

Status: complete on `feature/chapter-4-database-baseline`.

Done:

- Converted shared SQLAlchemy metadata into a SQLAlchemy 2.0 declarative base.
- Added `pgvector` dependency for SQLAlchemy vector support.
- Added Alembic migration `20260620_0001` enabling the Postgres `vector` extension.
- Added durable MVP tables for sessions, structured problems, knowledge gaps,
  evidence items, hypotheses, plan tasks, reasoning events, verification reports,
  artifacts, and semantic knowledge chunks.
- Added nullable `VECTOR(1536)` storage for `knowledge_chunks.embedding`.
- Added explicit embedding provenance columns on semantic knowledge chunks.
- Added local seed and smoke utilities.
- Guarded smoke seeding to local/test environments or explicit override.
- Linked seed evidence, hypothesis, and knowledge-gap records so the fixture
  exercises evidence-backed reasoning relationships.
- Added Makefile targets for `db-seed`, `db-smoke`, and `db-test`.
- Added DB integration test gated by `POLYABRAIN_RUN_DB_TESTS=1`.
- Added GitHub Actions database baseline job using `pgvector/pgvector:pg16`.
- Updated backend, README, and implementation notes for Chapter 4.

Verification:

- `make lint`
- `make test`
- `make proof`
- `docker compose config --quiet`
- `make docker-up`
- `make migrate`
- `make db-smoke`
- `make db-test`

Exit criteria:

- `pgvector` is enabled and verified.
- First durable MVP tables exist through Alembic.
- Seed and smoke checks prove sample session, evidence, trace, artifact, and
  vector-backed knowledge chunk insert/retrieve.
- Seed and smoke checks prove evidence-to-hypothesis linkage and embedding
  provenance storage.

## Chapter 5: Core Pydantic Models

Status: complete on active implementation branch.

Done:

- Define first-class Pydantic v2 models for the core contract surface.
- Added strict Pydantic models for structured problems, knowledge gaps, evidence
  items, hypotheses, plan tasks, verification reports, and reflections.
- Added value validation for product modes, priorities, plan risk levels,
  hypothesis origins, hypothesis statuses, reasoning modes, confidence scores,
  reliability scores, relevance scores, and verification confidence deltas.
- Kept structured problem representation as the current canonical session
  representation; reframe history remains trace metadata until versioned
  representation history proves necessary.
- Added JSON round-trip tests for all Chapter 5 models.
- Added malformed-data tests for extra fields, blank required strings, invalid
  enum values, evidence provenance, score bounds, selected-hypothesis
  requirements, and verification report consistency.
- Added full contract-bundle fixtures for math, technical research, software
  debugging, data analysis, planning, and ambiguous-problem use cases.
- Added implementation notes at `Chapter_5_Core_Pydantic_Models.md`.

Verification:

- `backend/tests/test_core_contracts.py`

Exit criteria:

- All models round-trip through JSON.
- Bad data fails clearly.
- Contract bundles cover the required Chapter 5 benchmark categories.

## Chapter 6: LangGraph State Object

Status: complete on active implementation branch.

Done:

- Added `backend/app/graph/state.py`.
- Defined `PolyaState` as a LangGraph-compatible `TypedDict`.
- Included session id, raw input, structured problem, gaps, evidence,
  hypotheses, plan, execution outputs, verification, reflection, iteration
  count, max iterations, final answer, and events.
- Added `StateEvent` for append-only state event messages.
- Added `ExecutionOutput` for task execution results before persistence exists.
- Added `append_state_events` as the `events` state reducer.
- Added reducer validation for dict-shaped graph event updates.
- Kept state event metadata and execution output payloads JSON-compatible.
- Added `create_initial_state` for raw-input validation and complete initial
  state construction.
- Added focused tests in `backend/tests/test_polya_state.py`.
- Added implementation notes at `Chapter_6_LangGraph_State_Object.md`.

Verification:

- `backend/tests/test_polya_state.py`

Exit criteria:

- A raw input can become a valid initial state.
- LangGraph accepts the `PolyaState` schema.
- A compiled LangGraph smoke graph accumulates event updates through the reducer.

## Chapter 7: Engine Interface Contract

Status: complete on active implementation branch.

Done:

- Added `backend/app/engines/contracts.py`.
- Defined shared `PolyaEngine` protocol with `name`, `reasoning_mode`,
  `version`, and synchronous `run(state)` interface.
- Added `EngineRunOutput` for graph-ready state deltas plus typed engine result.
- Added state-delta key validation against `PolyaState`.
- Added `EngineResult` with status, confidence, missing inputs,
  recommended route, duration, errors, token usage, version metadata, and
  summary.
- Added initial status values: `ok`, `needs_input`, `needs_evidence`,
  `low_confidence`, `blocked`, `failed`, and `insufficient_evidence`.
- Added initial route values: `continue`, `clarify`, `research`, `reframe`,
  `replan`, `retry_execution`, `finalize`, and
  `finalize_insufficient_evidence`.
- Added version metadata for engine, prompt, model, tool, verifier, and graph
  version.
- Added common `run_engine` telemetry wrapper with duration capture,
  structured logging, start/completion/failure events, version propagation, and
  exception-to-failed-result conversion.
- Added fail-closed fallback handling for malformed engine identity or version
  metadata.
- Added validation guards so `ok`, `needs_input`, `needs_evidence`,
  `low_confidence`, `blocked`, `failed`, and `insufficient_evidence` statuses
  cannot recommend unsafe or incoherent routes.
- Added focused tests in `backend/tests/test_engine_contracts.py`.
- Added implementation notes at `Chapter_7_Engine_Interface_Contract.md`.

Verification:

- `make lint`
- `make test`
- `make proof`

Exit criteria:

- All future engines can be implemented consistently.
- Engines cannot silently pass low-confidence or incomplete outputs to the next
  stage.

## Chapter 8: Graph Skeleton

Status: complete on `feature/chapter-8-graph-skeleton`.

Done:

- Add graph nodes for all nine logical engines.
- Wire engine nodes through the Chapter 7 telemetry wrapper.
- Add graph routes for gaps, missing inputs, low confidence, verification
  failure, insufficient evidence, success, and iteration limits.
- Prove blocked or weak stages stop safely instead of continuing.
- Added `backend/app/graph/skeleton.py`.
- Added stable graph node names for all nine logical engines.
- Added `PolyaGraphEngines`, `build_polya_graph`, and `run_polya_graph`.
- Added graph-owned `iteration_guard` and `safe_stop` router nodes.
- Reconstructed routing decisions from Chapter 7 terminal event metadata
  without adding new `PolyaState` fields.
- Added deterministic graph skeleton tests.
- Added Chapter 8 implementation notes and routing Mermaid diagram.

Verification:

- `backend/tests/test_graph_skeleton.py`
- `make lint`
- `make test`
- `make proof`

Exit criteria:

- Graph runs end-to-end with stubs.
- Routing is visible in documentation.
- The graph is recoverable, not a blind linear chain.

## Chapter 9: Event Trace System

Status: complete on `feature/chapter-9-event-trace-system`.

Done:

- Added deterministic per-session ordering through
  `reasoning_events.sequence_number`.
- Added Alembic migration `20260620_0002` to backfill and enforce sequence
  numbers for existing trace rows.
- Added pure trace preparation for sanitized durable writes.
- Added derived `graph_router` `route_decision` events after terminal engine
  events with route metadata.
- Added recursive redaction for secret-like keys and obvious secret-bearing
  strings before logging, persistence, and API response.
- Added `SQLAlchemyTraceRepository` for appending graph state events and reading
  ordered persisted events.
- Kept LangGraph execution storage-agnostic; callers persist events after runs.
- Added `GET /api/v1/sessions/{session_id}/events`.
- Added API response models for ordered trace events.
- Extended database smoke checks to verify trace ordering metadata.
- Added Chapter 9 implementation notes.
- Added unit and API tests for redaction, event ordering, route-decision
  insertion, endpoint output, missing sessions, and wrapper redaction.

Verification:

- `make lint`
- `make test`
- `make proof`

Exit criteria:

- Every persisted run can produce an inspectable ordered trace.
- Users can tell whether the system was exploring, comparing, reframing,
  executing, verifying, or reflecting at each major step.
- Logs and persisted/API trace data redact obvious secrets.

## Chapter 10: API Shell

Status: complete on `feature/chapter-10-api-shell`.

Done:

- Added session API models for create, read, and run responses.
- Added `POST /api/v1/sessions`.
- Added `GET /api/v1/sessions/{session_id}`.
- Kept `GET /api/v1/sessions/{session_id}/events` as the ordered trace read
  endpoint.
- Added `POST /api/v1/sessions/{session_id}/run`.
- Added deterministic application stub engines for all nine logical graph
  stages.
- Wired the run endpoint to execute the stub graph synchronously, persist trace
  events, and update the session outcome.
- Added an atomic `created` to `running` claim before graph execution so
  duplicate or competing run requests return `409`.
- Preserved Chapter 10 honesty by not persisting rich reasoning artifacts from
  stub outputs.
- Added duplicate-run protection for non-created sessions with `409`.
- Added sanitized failed-run handling that marks the session as `failed`.
- Added OpenAPI tags and request examples for the session workflow.
- Added API and graph smoke tests for session creation, readback, run behavior,
  validation, conflicts, missing sessions, and trace readback.
- Added database-backed service tests for run persistence, ordered trace
  persistence, failed-run marking, and competing-run protection.
- Added Chapter 10 implementation notes.
- Completed the Phase 1 debt closure pass after Chapter 10:
  - broadened trace secret redaction coverage,
  - added bounded trace pagination and filtering,
  - added lightweight trace persistence metrics,
  - validated per-session trace append locking under concurrency,
  - added stale-running session expiration,
  - closed all implementation debt introduced by completed Phase 0/1 chapters.

Verification:

- `make lint`
- `make test`
- `make proof`
- `docker compose config --quiet`
- `make docker-up`
- `make migrate`
- `make db-smoke`
- `make db-test`
- `make docker-down`

Exit criteria:

- A client can create and run a session through the stub graph.
- The completed session is readable through the API.
- The ordered trace is readable through the API.
- The stub final answer clearly states that Chapter 10 proves platform wiring,
  not real investigation intelligence.
- No implementation debt remains open for completed Phase 0 or Phase 1 chapters.

## Phase 2 Readiness Note

Before Chapter 13 lands, real engine outputs should follow the Phase 2
persistence policy in
`../01_architecture/Phase_2_Engine_Output_Persistence.md`.

The working rule is: persist canonical rows only after a producing engine
completes successfully and its structured output passes parser and contract
validation. Chapter 13 owns the first canonical `structured_problems` write.
Trace events remain the append-only audit history for accepted, rejected, failed,
or repaired outputs.

## Phase 2 Action Plan

Use `Phase_2_Action_Items.md` as the tactical checklist for the next
implementation branches.

Current intended order:

1. Chapter 12-A: LLM client interface and fake deterministic client.
2. Chapter 11: prompt templates, parser, schemas, and JSON repair.
3. Chapter 12-B: first real provider adapter, starting with OpenAI.
4. Chapter 13: problem representation engine with `structured_problems`
   persistence.
5. Chapter 15: clarifying question flow.
6. Chapter 14: constraint discovery engine.
