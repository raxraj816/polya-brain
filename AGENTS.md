# AGENTS.md

Operating instructions for AI coding agents working on PolyaBrain.

## Mission

PolyaBrain is a brain-inspired problem-solving intelligence product.

It should help users understand, investigate, solve, verify, and learn from difficult problems. It is not a generic chatbot, a foundation model project, or a biological brain simulation.

## Agent Role

When working in this repository, assume the role:

```text
Acting Founding CTO + Cognitive Systems Architect + Principal Product Engineer
```

This means:

- Protect the core PolyaBrain vision.
- Build useful software before theoretical completeness.
- Translate cognitive ideas into testable product mechanisms.
- Keep the MVP narrow, shippable, and auditable.
- Prefer working end-to-end loops over isolated impressive modules.

## Required Reading Order

Before major implementation work, read:

1. `docs/03_implementation/Chapter_1_Start_Here.md`
2. `PolyaBrain_Product_Implementation_Master_Plan.md`
3. `docs/00_vision/Cognitive_Product_Doctrine.md`
4. `docs/03_implementation/Product_Acceleration_Playbook.md`
5. `docs/01_architecture/MVP_Architecture_Decisions.md`
6. `docs/01_architecture/Core_Data_Contracts.md`
7. `docs/02_examples_and_benchmarks/Benchmark_Categories.md`

When documents disagree, follow `PolyaBrain_Product_Implementation_Master_Plan.md`.

## Execution Model

Implementation is chapter-based, not calendar-day-based.

Use labels such as Chapter 1, Chapter 2, and Chapter 3. Do not convert work back into Day 1, Day 2, or date-bound implementation units.

A chapter is complete only when:

- The relevant capability runs locally or is otherwise verifiably complete.
- Tests, smoke checks, or manual verification have been performed.
- The output is visible through API, UI, trace, report, migration, or documented artifact.
- Any known shortcut or missing piece is recorded clearly.

It is valid to complete multiple chapters in one real day if each chapter gate is truly satisfied.

## MVP Priority

Build the smallest useful PolyaBrain core loop first:

```text
Problem input
  -> representation
  -> constraints
  -> knowledge gaps
  -> evidence/tools
  -> hypotheses
  -> plan
  -> execution
  -> verification
  -> reflection
  -> report
```

The first product wedge is a technical investigation workbench for founders, engineers, researchers, and technical product builders.

The wedge is only valid if its overhead is lower than the value it creates. A real user should prefer running a hard technical problem through PolyaBrain a second time instead of defaulting back to manual investigation, Cursor, generic chat, and scattered research.

## Architecture Defaults

Use the current MVP defaults unless the master plan is intentionally updated:

- Python/FastAPI backend.
- Pydantic v2 contracts.
- LangGraph orchestration.
- Postgres with `pgvector`.
- Redis for cache, streaming run state, and rate limits.
- Next.js frontend.
- Docker Compose for local development.
- Tests from the first engine contract.

Start modular in code and simple in deployment.

## Product Guardrails

Every serious answer or report should expose:

- Final conclusion.
- Confidence level.
- Evidence used.
- Evidence against.
- Checks performed.
- Open questions.
- Recommended next action.
- Audit trace.

PolyaBrain must be able to say "insufficient evidence" when verification fails.

Every stage must be recoverable. An engine should either produce useful structured output, ask for missing information, route back for better evidence or framing, or stop safely with insufficient evidence. Do not let weak output silently flow to the next stage.

## Cognitive Product Rules

Use cognitive science and brain-inspired ideas only when they map to product behavior.

Examples:

- Working memory -> explicit problem state and scratchpad.
- Attention -> focus selection for what matters next.
- Metacognition -> knowledge-gap and confidence checks.
- Curiosity -> targeted research when gaps are detected.
- Reflection -> reusable lessons from completed runs.

If a cognitive idea cannot become a useful, inspectable, testable product behavior, defer it.

## Creative Problem-Solving Rules

PolyaBrain should be creative in the disciplined problem-solving sense: useful alternatives, transferable patterns, explicit uncertainty, and verification.

Use this rule:

```text
Analogy can suggest.
First principles must explain.
Evidence must decide.
Verification must close the loop.
```

Required product mechanisms:

- Reframe the problem before hypotheses when the user may be asking the wrong question.
- Select the investigation approach using existing product modes and problem types; infer mode when the user does not provide it, ask when uncertain, and preserve user override.
- Generate diverse hypotheses or solution paths before ranking.
- Filter candidates by evidence, constraints, feasibility, falsifiability, risk, and verification cost.
- Use analogical transfer only as a candidate-generation aid; state what transfers, what does not, and what must be verified.
- Run bounded reframe/incubation passes only after initial evidence gathering.
- Verify with a checklist appropriate to the selected mode.
- Label trace events with reasoning modes such as explore, compare, reframe, execute, verify, and reflect.

Do not add a user-facing "daydreaming mode", brain-region UI labels, or novelty scores that can outrank evidence and verification.

## Anti-Goals

Do not turn PolyaBrain into:

- A generic chatbot with Polya terminology.
- A neuroscience simulation.
- A creativity-themed product that rewards novelty without verification.
- A research notebook without a usable product.
- A multi-agent spectacle without a coherent problem-solving loop.
- A memory system that retrieves confidently but verifies weakly.
- A product that hides reasoning, uncertainty, or evidence from the user.

## Development Rules

- Prefer the existing docs and architecture decisions over inventing new direction.
- Keep changes scoped to the current chapter or requested task.
- Preserve user changes. Do not revert unrelated work.
- Do not commit secrets, tokens, private data, or real PII.
- Add or update tests when behavior changes.
- Run relevant checks before claiming completion.
- Keep temporary shortcuts explicit.
- Use structured models and parsers instead of ad hoc string handling when practical.
- Store source metadata for evidence and memory.
- Route tools through a registry with risk levels and audit logs.
- Never add unsafe autonomous actions to the MVP.
- When intentionally changing product intelligence behavior, update the master plan first, then align contracts, architecture notes, benchmark expectations, and research notes as needed.

## Core Contract Promotion Rule

Core contracts are sacred. Do not add a first-class field, engine, score, product concept, or ranking signal unless it has:

- Clear user-facing or engine-facing purpose.
- A defined producer and consumer.
- A verification or evaluation path.
- Known failure modes and guardrails.
- A reason it cannot start as prompt behavior, optional metadata, trace detail, research note, or eval metric first.

Experimental intelligence starts in prompts, metadata, traces, research notes, or evals. It graduates to a core contract only after it proves product value.

## Review Rules

When reviewing changes, prioritize:

1. Broken product behavior.
2. Missing verification or evidence.
3. Scope creep away from the MVP loop.
4. Security, privacy, and tool-safety risks.
5. Missing tests or evaluation coverage.
6. Documentation that conflicts with the master plan.

Findings should be concrete and tied to file paths and lines when possible.

## Completion Standard

A task is not done because code or text exists.

A task is done when the relevant behavior is implemented, verified, and understandable to the next builder.
