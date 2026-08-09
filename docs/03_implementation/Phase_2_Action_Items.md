# Phase 2 Action Items

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

This note records the tactical execution order for Phase 2 so implementation can
continue from a shared checklist instead of conversation memory.

## Immediate Branches

1. Review and merge `feature/chapter-11-prompt-parser`, including the Chapter
   12-A boundary it builds upon.
2. Start Chapter 12-B from the tested prompt, parser, and client boundaries.

## Execution Order

1. Chapter 12-B: first real provider adapter.
2. Chapter 13: problem representation engine.
3. Chapter 15: clarifying question flow.
4. Chapter 14: constraint discovery engine.

This order keeps tests deterministic before live provider work and prevents
under-specified user input from flowing too far into later engines.

## Chapter 12-A: LLM Boundary

Status: complete on `feature/chapter-12-llm-client`.

Deliver:

- Provider-neutral request and response models.
- `LLMClient` protocol or equivalent local abstraction.
- Fake deterministic client for engine and parser tests.
- JSON mode capability flag in request options.
- Timeout and retry/backoff behavior at the boundary.
- Token usage fields on responses.
- Sanitized errors and logs.

Do not require Redis or multiple real providers before this boundary is proven.

## Chapter 11: Prompt And Parser Boundary

Status: complete on `feature/chapter-11-prompt-parser`.

Done:

- Versioned problem-understanding prompt templates.
- Prompt input formatting from `PolyaState`.
- Structured output schema for problem representation.
- Parser validation against the Chapter 5 contracts.
- JSON repair and retry policy.
- Local examples for math, logic, software debugging, research, data analysis,
  planning, scientific reasoning, ambiguous input, low-confidence mode selection,
  and wrong-problem framing.
- Executable ten-example gate through `make chapter11-proof`.
- Bounded deterministic local repair and bounded LLM repair with safe
  exhaustion.
- Prompt-only intelligence kept outside the canonical core contract while
  accepted output maps to `StructuredProblem`.

## Chapter 12-B: First Real Provider

Deliver:

- OpenAI adapter behind the provider-neutral interface.
- Environment-driven model configuration.
- Provider error mapping into typed client errors.
- Usage/cost capture when provider metadata is available.
- Tests that keep network calls out of default unit runs.

Anthropic support remains a later adapter after the interface proves stable.

## Chapter 13: First Real Engine

Deliver:

- Problem Representation Engine using the prompt/parser/client boundary.
- State update for `structured_problem`.
- Trace events for selected framing, rejected alternate framing, selected mode,
  parser repair, and fallback decisions.
- Canonical `structured_problems` persistence after successful validation, using
  `../01_architecture/Phase_2_Engine_Output_Persistence.md`.
- Golden examples and fake-client tests.

## Chapter 15 Before Chapter 14

Implement clarifying-question flow before constraint discovery so the product can
stop safely on missing or ambiguous inputs instead of extracting constraints from
weak framing.

## Non-Blockers

- Redis caching, streaming run state, and rate limiting are not required before
  the first real engine works.
- Anthropic is not required before the OpenAI adapter proves the provider
  interface.
- Full eval harness work remains later chapter scope, though Chapter 13 should
  add focused golden examples.
