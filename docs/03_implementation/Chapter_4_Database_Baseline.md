# Chapter 4 Database Baseline

Status: complete on `feature/chapter-4-database-baseline`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 4 creates the first durable Postgres baseline for the MVP core loop. It
does not implement Chapter 5 Pydantic contracts, Chapter 6 LangGraph state, solve
APIs, frontend flows, auth, connectors, feedback, or full evaluation storage.

## Implemented

- SQLAlchemy 2.0 declarative base with deterministic naming conventions.
- `pgvector` Python dependency for SQLAlchemy vector columns.
- Alembic migration `20260620_0001` enabling the Postgres `vector` extension.
- Durable MVP tables for sessions, structured problems, gaps, evidence,
  hypotheses, plan tasks, reasoning events, verification reports, artifacts, and
  semantic knowledge chunks.
- `knowledge_chunks.embedding` as nullable `VECTOR(1536)` for the local semantic
  memory baseline.
- Explicit knowledge chunk provenance columns for content hash, embedding
  provider, embedding model, and embedding dimensions.
- Local seed utility that inserts one representative technical investigation
  session graph.
- Local smoke utility that verifies pgvector, migration head, expected tables,
  seed insert/retrieve behavior, evidence-to-hypothesis linkage, embedding
  provenance, and vector storage.
- Smoke seeding is guarded to local/test environments unless
  `POLYABRAIN_ALLOW_DB_SEED=1` is explicitly set.
- DB integration test gated by `POLYABRAIN_RUN_DB_TESTS=1`.
- GitHub Actions database job using `pgvector/pgvector:pg16`.

## Commands

```bash
make docker-up
make migrate
make db-seed
make db-smoke
make db-test
make docker-down
```

Standard checks remain:

```bash
make lint
make test
make proof
```

## Verification Completed

- `make lint`
- `make test`
- `make proof`
- `docker compose config --quiet`
- `make docker-up`
- `make migrate`
- `make db-smoke`
- `make db-test`

## Deferred To Chapter 5

- First-class Pydantic v2 contracts.
- Enum/value validation for modes, statuses, risk levels, and reasoning modes.
- Contract-level producers and consumers.
- API request/response models.
- Decide whether `structured_problems` remains the current canonical
  representation per session or becomes a versioned snapshot history. Chapter 4
  stores one row per session and expects reframe history to remain trace-visible
  in `reasoning_events.metadata` until that decision is made.

## Deferred Beyond Chapter 4

- Solve session API endpoints.
- LangGraph state and graph execution.
- Tool registry and tool-call persistence.
- User, organization, project, connector, feedback, evaluation, and model-cost
  tables.
- Approximate vector indexes, pending real retrieval volume and embedding model
  selection.
