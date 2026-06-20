# PolyaBrain

PolyaBrain is a brain-inspired problem-solving workbench for difficult technical investigations.

It is not a generic chatbot, a foundation model project, or a biological brain simulation. The product goal is to help users understand, investigate, solve, verify, and learn from hard problems through an auditable loop:

```text
problem input -> representation -> constraints -> gaps -> evidence/tools
  -> hypotheses -> plan -> execution -> verification -> reflection -> report
```

## Current Status

This branch implements the Chapter 7 engine interface contract on top of the
Chapter 6 LangGraph state object, Chapter 5 core Pydantic contracts, Chapter 4
database baseline, Chapter 3 local development environment, and the verified
pre-platform proof harness.

What runs today:

```bash
./polyabrain investigate "Our API p95 latency jumped after deploy. Should we add Redis or inspect the query path first?" --clean
python3 proofs/pre_platform/verify_pre_platform_proof.py --run-dir proofs/pre_platform/runs/our_api_p95_latency_jumped_after_deploy
```

Start the backend locally:

```bash
make dev
curl http://127.0.0.1:8000/health
```

Run the local checks:

```bash
make lint
make test
make proof
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
local/test environments or with `POLYABRAIN_ALLOW_DB_SEED=1`. Chapters 5, 6, and
7 add contracts and graph/engine primitives and do not require a database smoke
check.

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
frontend/     Future Next.js investigation workbench UI.
infra/        Infrastructure notes; Docker Compose lives at repo root.
scripts/      Local developer scripts and notes.
evals/        Future benchmark and evaluation runners.
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

- `OPENAI_API_KEY` for a live direct LLM baseline

Run the local proof:

```bash
./polyabrain investigate "Investigate why a background job started timing out after a dependency upgrade." --clean
python3 proofs/pre_platform/verify_pre_platform_proof.py --all
```

## Environment

Copy `.env.example` to a local `.env` when platform or live baseline work needs credentials. Never commit real secrets.

## Chapter Plan

Implementation is chapter-based, not date-based.

Chapters 1, 2, 3, 4, 5, 6, and 7 are complete on the active chapter branch.
Chapter 8 is the next implementation target.

The next chapters are:

1. Chapter 8: graph skeleton.
2. Chapter 9: event trace system.
3. Chapter 10: API shell.
4. Chapter 11: prompt and parser design.

See `docs/03_implementation/Chapter_Backlog.md` for the active local backlog.
