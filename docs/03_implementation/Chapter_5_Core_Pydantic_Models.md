# Chapter 5 Core Pydantic Models

Status: complete on active implementation branch.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Scope

Chapter 5 defines the first strict Pydantic v2 contract layer for the MVP
reasoning artifacts. These contracts are the API and engine-facing surface that
Chapter 6 will use to build the LangGraph state object.

This chapter does not add API endpoints, graph execution, database migrations,
tool approval flows, frontend screens, or persistence adapters.

## Implemented

- Added strict core contracts in `backend/app/models/contracts.py`.
- Added shared validation defaults: unknown fields are rejected, strings are
  stripped, assignments are validated, and ORM-style attributes are supported
  for future adapters.
- Added constrained score types for confidence, reliability, relevance, and
  verification confidence deltas.
- Added stable enum values for product modes, priorities, plan risk levels,
  hypothesis origins, hypothesis statuses, and trace-visible reasoning modes.
- Added Pydantic models for:
  - structured problem
  - knowledge gap
  - evidence item
  - hypothesis
  - plan task
  - verification report
  - reflection
- Added cross-field guards:
  - evidence items require source URI or raw excerpt provenance
  - selected hypotheses require evidence, verification checks, falsification
    criteria, and selection rationale
  - verification reports require at least one check run
  - passing verification reports cannot carry failed checks
  - failing verification reports must include failure detail or a recommended route
- Re-exported the contract models from `backend/app/models`.
- Added serialization, validation, and benchmark-category contract-bundle tests in
  `backend/tests/test_core_contracts.py`.

## Contract Decisions

- `StructuredProblem` is the current canonical representation for a session.
  Reframe history remains trace metadata until a later chapter proves versioned
  structured-problem history is needed.
- Chapter 5 keeps reflection lean: outcome summary, what worked, what failed,
  reusable lessons, memory updates, strategy notes, and follow-up actions. Full
  reflection prompt and engine behavior remain deferred to Chapters 53 and 54.
- `PlanTask.id` is a non-empty string instead of UUID-only so future contracts
  can reference database UUIDs or stable proof/evaluation identifiers.
- Risk levels are limited to `low`, `medium`, and `high`; approval behavior is
  deferred to the tool registry and execution chapters.

## Commands

```bash
make lint
make test
make proof
```

Chapter 5 does not require Docker/Postgres verification because it does not
change persistence.

## Verification Completed

- `backend/tests/test_core_contracts.py`
- JSON round-trip tests for every Chapter 5 model
- malformed data rejection tests for extra fields, empty required strings,
  invalid enum values, evidence provenance, score bounds,
  selected-hypothesis requirements, and verification report consistency
- full contract-bundle fixture coverage for math, technical research, software
  debugging, data analysis, planning, and ambiguous-problem cases

## Deferred To Chapter 6

- `PolyaState`
- state initialization helper
- graph event reducers
- execution outputs in graph state
- iteration limits and final answer fields

## Deferred Beyond Chapter 5

- Engine interface result contract and routing statuses
- API request/response models for solve sessions
- database schema changes
- tool definitions, tool calls, approval flows, and risk enforcement
- frontend rendering of contracts
