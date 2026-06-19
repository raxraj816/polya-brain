# PolyaBrain

PolyaBrain is a brain-inspired problem-solving workbench for difficult technical investigations.

It is not a generic chatbot, a foundation model project, or a biological brain simulation. The product goal is to help users understand, investigate, solve, verify, and learn from hard problems through an auditable loop:

```text
problem input -> representation -> constraints -> gaps -> evidence/tools
  -> hypotheses -> plan -> execution -> verification -> reflection -> report
```

## Current Status

This branch closes the Chapter 1 foundation gate with a verified pre-platform proof harness.

What runs today:

```bash
./polyabrain investigate "Our API p95 latency jumped after deploy. Should we add Redis or inspect the query path first?" --clean
python3 proofs/pre_platform/verify_pre_platform_proof.py --run-dir proofs/pre_platform/runs/our_api_p95_latency_jumped_after_deploy
```

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
backend/      Future Python/FastAPI backend and Polya loop engines.
frontend/     Future Next.js investigation workbench UI.
infra/        Future Docker Compose and infrastructure files.
scripts/      Local developer scripts.
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

No platform services are required for the current proof harness.

Requirements:

- Python 3.11+
- Bash-compatible shell

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

Chapter 1 closes when the product direction is locked, repository foundation is clear, setup is visible, no secrets are committed, and a new developer can understand what runs locally.

The next chapters are:

1. Chapter 2: architecture decisions and risk register.
2. Chapter 3: local development environment.
3. Chapter 4: database baseline.
4. Chapter 5: core Pydantic models.

See `docs/03_implementation/Chapter_Backlog.md` for the active local backlog.
