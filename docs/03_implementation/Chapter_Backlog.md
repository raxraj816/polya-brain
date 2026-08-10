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

Chapter 13 engine outputs follow the Phase 2 persistence policy in
`../01_architecture/Phase_2_Engine_Output_Persistence.md`.

The working rule is: persist canonical rows only after a producing engine
completes successfully and its structured output passes parser and contract
validation. Chapter 13 owns the first canonical `structured_problems` write.
Trace events remain the append-only audit history for accepted, rejected, failed,
or repaired outputs.

## Phase 2 Action Plan

Use `Phase_2_Action_Items.md` as the tactical checklist for the next
implementation branches.

Current intended order after the completed Chapter 12-B, Chapter 13, and Chapter
14-15 work:

1. Minimum production capability set for the persisted cognitive runtime.

## Chapter 12-A: LLM Client Boundary

Status: complete on `feature/chapter-12-llm-client`.

Done:

- Added strict provider-neutral message, request, option, capability, response,
  and usage contracts.
- Added the synchronous `LLMClient` protocol for the current graph architecture.
- Added deterministic `FakeLLMClient` scripting and request capture.
- Added JSON-mode capability checks that fail before unsupported calls.
- Added typed, sanitized client errors.
- Added bounded retry and deterministic exponential-backoff policy.
- Added request-level timeout, model, temperature, output-token, and retry
  controls.
- Added focused tests for validation, fake responses, capability failures,
  timeout propagation, retry behavior, error sanitization, and prompt-free logs.
- Added OpenRouter support and an offline HTTP contract test for the separate
  direct-model proof baseline runner.
- Ran a five-case live OpenRouter baseline audit and recorded the result under
  `proofs/pre_platform/live_baseline_runs/2026-08-09/`.

Exit criteria:

- Future engines can use the fake client in deterministic tests.
- A production adapter can implement the protocol without changing engine
  contracts.
- Unsupported features and weak provider failures stop safely.

## Chapter 12-B: Production OpenRouter Adapter

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Done:

- Added a production OpenRouter adapter behind the Chapter 12-A protocol.
- Added environment-driven model, endpoint, attribution, privacy, ZDR, and JSON
  routing configuration with secret-safe API-key handling.
- Added typed mapping for transport, HTTP, embedded, choice-level, and malformed
  provider failures without exposing provider bodies.
- Added normalized token, cached-token, reasoning-token, and available cost
  metadata.
- Added `Retry-After` support within the existing bounded retry policy.
- Added offline adapter contract and error-mapping tests.
- Exercised the adapter through a genuine live smoke call and all three Chapter
  13 technical investigations.
- Confirmed that the configured free endpoint cannot meet deny-data-collection
  plus strict-JSON production routing; kept defaults fail-closed and limited the
  compatibility override to non-confidential evaluation fixtures.

Exit criteria:

- Real local calls use the provider-neutral engine boundary without contract
  changes.
- Provider failures remain typed, sanitized, and safely retry-bounded.
- Production privacy defaults fail closed when no compatible endpoint exists.

## Chapter 13: Problem Representation Engine

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Done:

- Added the first real engine using the Chapter 11 prompt/parser and Chapter 12
  client boundary.
- Added narrow deterministic fallbacks for exact golden examples, simple
  arithmetic, and explicit underspecified requests.
- Added stage-gated clarification that emits audit trace but does not promote a
  canonical structured problem.
- Added framing, alternate-framing, approach-mode, parser-repair, and fallback
  trace events without expanding the core data contract.
- Added validated, successful-only canonical persistence to
  `structured_problems` plus trace persistence for all accepted engine paths.
- Added fake-client, fallback, repair, clarification, state-update, and
  database-backed persistence tests.
- Ran three reproducible live technical investigations against the configured
  direct model using real code, logs, measurements, and provider-policy
  documents.
- Recorded equal correctness, much stronger Polya evidence quality, and
  substantial Polya latency/token overhead in
  `../../evals/chapter_13/runs/2026-08-09/summary.json`.

Exit criteria:

- The engine produces a contract-valid state update or stops safely for
  clarification.
- Only successful validated output becomes canonical database state.
- Selected and rejected framing decisions remain inspectable in the trace.
- Focused, full-suite, proof, lint, Compose, and real Postgres checks pass.

## Chapter 13-C: General Cognitive Control Proof

Status: in progress on `feature/chapter-12b-13-openrouter-representation`.

Done:

- Established the non-negotiable capability hierarchy: PolyaBrain owns goal,
  state, action selection, observation interpretation, verification, recovery,
  stopping, and reflection; models and tools are subordinate capabilities.
- Added an experimental universal action taxonomy, action candidates, decisions,
  observations, typed state updates, capability registry, deterministic
  controller, and bounded cognitive kernel outside the sacred core contracts.
- Proved cross-domain routing across ten categories with one shared controller.
- Proved search-to-inspection recovery without repeating a failed action.
- Proved failed-verification invalidation and
  `verify -> replan -> execute -> verify` recovery.
- Proved that only a verified completed run can teach in-process procedural
  memory and change a related future decision.
- Added raw-input runtime composition and a typed adapter for the real Chapter
  13 Problem Representation Engine, including successful and clarification
  paths.
- Recorded a live same-model first-action comparison: controller 10/10 versus
  direct model 8/10, with two invalid structured responses; this is not an
  end-to-end outcome claim.
- Added durable verified semantic, episodic, and procedural memory plus
  production acquisition, inspection, measurement, safe-code, simulation, and
  experiment capabilities.
- Added an offline-contract-tested six-category fair full-outcome harness. The
  2026-08-09 live run completed zero comparable cases because the configured
  free model returned HTTP 429.

Remaining exit criteria:

- Execute the implemented fair end-to-end harness when provider capacity is
  available and record complete comparable cases scored on final correctness,
  evidence, recovery, verification, latency, and cost.
- Keep experimental action contracts unpromoted until this evidence identifies
  stable producers, consumers, failure modes, and user value.

## Chapter 15: Clarifying Question Flow

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Done:

- Replaced the persisted API's silent Chapter 10 success stub with the
  representation-capable cognitive runtime.
- Added durable `awaiting_user_input` sessions and expiring
  `clarification_requests` through migration `20260809_0004`.
- Persisted questions in the audit trace and exposed a bounded SSE trace stream.
- Added `POST /api/v1/sessions/{session_id}/respond` with locked state
  transition, durable answer, trace continuity, and representation rerun.
- Canonicalized only validated clarified representations.
- Added repeat-clarification behavior for insufficient answers and safe
  duplicate, wrong-state, missing-session, expired, and resume-failure paths.
- Verified the full pause/respond/resume path through unit, API, real Postgres,
  database smoke, and Docker API checks.

Exit criteria:

- Ambiguous input produces useful questions without canonicalizing weak output.
- A paused session resumes with the same id and ordered trace.
- User answers change the next representation result.
- Missing downstream capabilities stop with an explicit unverified conclusion.

## Chapter 11: Prompt And Parser Design

Status: complete on `feature/chapter-11-prompt-parser`.

Done:

- Added versioned problem-understanding and repair prompts.
- Added a strict Pydantic JSON output schema with literal, deeper, and
  wrong-problem framing.
- Added the exact Polya fields for given information, unknowns, constraints,
  goal, and success criteria.
- Added existing-mode inference, mode rationale and confidence, low-confidence
  clarification routing, and user override preservation.
- Added safe deterministic local JSON repair and bounded LLM repair.
- Mapped validated prompt output into the existing Chapter 5
  `StructuredProblem` contract without expanding the core data model.
- Added exactly ten validated examples covering every category required by the
  master plan.
- Added focused contract, prompt, parser, and service tests.
- Added an executable `make chapter11-proof` verification gate and CI step.
- Added prompt version history and Chapter 11 implementation notes.

Exit criteria:

- The problem-understanding prompt exposes all required framing and Polya
  fields through strict JSON.
- Invalid output is locally repaired, repaired by a bounded model call, or
  rejected safely.
- All ten local examples pass through the provider-neutral fake-client boundary
  and canonical contract mapping.
