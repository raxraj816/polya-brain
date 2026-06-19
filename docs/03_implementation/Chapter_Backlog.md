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

Status: not started.

Planned:

- Define first-class Pydantic v2 models for the core contract surface.
- Add value validation for modes, statuses, risk levels, and reasoning modes.
- Decide whether structured problem representation is one mutable current state
  per session or a versioned representation history.
- Add serialization tests and contract fixtures.
- Align API and engine-facing interfaces to these contracts before graph work.
