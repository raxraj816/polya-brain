# Phase 2 Action Items

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

This note records the tactical execution order for Phase 2 so implementation can
continue from a shared checklist instead of conversation memory.

## Immediate Branch

1. Review and merge `feature/chapter-12b-13-openrouter-representation`, including
   its live-investigation artifacts and provider-policy caveat.

## Execution Order

1. Add the minimum production capability set to the persisted cognitive runtime.
2. Complete Chapter 13-C with a fair end-to-end tool-enabled outcome comparison.

This order keeps tests deterministic before live provider work and prevents
under-specified user input from flowing too far into later engines.

## Chapter 13-C: General Cognitive Control Proof

Status: in progress on `feature/chapter-12b-13-openrouter-representation` because
the branch already contained uncommitted Chapter 12-B/13 work and repository
rules prohibit switching branches before disposition.

Done:

- Established PolyaBrain as the controller and models/tools as capabilities in
  the master plan, doctrine, MVP decisions, and kernel architecture note.
- Added experimental action, capability, decision, observation, and state-update
  contracts outside the sacred core contract module.
- Added deterministic state-dependent candidate generation and selection.
- Added capability availability, support, approval, risk, cost, and sanitized
  exception boundaries.
- Added typed observation-to-state updates, gap resolution, recovery history,
  independent verification gating, reflection gating, and safe stopping.
- Added cross-domain action-selection tests and a complete calculate through
  verified-stop kernel test.
- Added a ten-category offline structural proof, including deliberate search
  failure followed by an inspection recovery action.
- Added failed-verification invalidation and a verified
  `verify -> replan -> execute -> verify` recovery proof.
- Added in-process procedural memory that learns only from verified completed
  runs and changes a related future action decision.
- Added durable verified semantic, episodic, and procedural memory to the
  persisted runtime.
- Recorded a same-model live first-action comparison: controller 10/10 versus
  direct model 8/10, with two invalid direct-model structured responses.
- Recorded action quality, repeated non-progress, verification recovery,
  latency, model-token, and estimated capability-cost metrics.
- Added a raw-input runtime and typed Chapter 13 representation adapter; proved
  successful representation-to-verified-stop and clarification-to-needs-input
  paths.
- Added the first production capability set: schema-validated model proposals
  for gaps, hypotheses, plans, bounded analytic execution, verification, and
  reflection; deterministic calculator and arithmetic procedures; human-input
  pause; canonical artifact persistence; and an auditable report endpoint.
- Completed a persisted Docker arithmetic outcome with passing verification and
  reflection without using a model where a deterministic procedure suffices.
- Proved that malformed outputs and provider rate limits fail closed and that an
  unchanged failed action is not repeated.
- Added production web acquisition, evidence evaluation, artifact inspection,
  table measurement/querying, safe Python, simulation, and experiment paths.
- Added and contract-tested a fair six-category full-outcome harness with the
  same model, tools, observations, call budget, token limit, and alternating
  condition order. The first live attempt was provider-blocked by HTTP 429.

Remaining before Chapter 13-C completion:

- Record complete cases with the implemented full-outcome harness when the
  configured provider has capacity; do not use the fixture, first-action proof,
  or HTTP 429 as outcome-superiority evidence.
- Keep the experimental action models out of core contracts until that outcome
  evidence establishes stable product value.

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

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Done:

- Production OpenRouter adapter behind the provider-neutral interface, selected
  by the user's configured provider.
- Environment-driven model configuration.
- Provider error mapping into typed client errors.
- Usage/cost capture when provider metadata is available.
- Tests that keep network calls out of default unit runs.
- Fail-closed provider-routing defaults for data collection, optional ZDR, and
  required JSON parameters.
- Live smoke validation plus a documented benchmark-only compatibility override
  for the configured free endpoint.

Additional provider adapters remain later scope after this interface has proven
stable.

## Chapter 13: First Real Engine

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Done:

- Problem Representation Engine using the prompt/parser/client boundary.
- State update for `structured_problem`.
- Trace events for selected framing, rejected alternate framing, selected mode,
  parser repair, and fallback decisions.
- Canonical `structured_problems` persistence after successful validation, using
  `../01_architecture/Phase_2_Engine_Output_Persistence.md`.
- Golden examples and fake-client tests.
- Stage-gated clarification that does not promote ambiguous output into
  canonical state or storage.
- Narrow zero-model fallbacks for exact golden cases, simple arithmetic, and
  explicit underspecified requests.
- Three reproducible live technical investigations comparing the same configured
  direct model on correctness, evidence quality, decision time, token overhead,
  and a clearly labeled reuse proxy.

## Chapter 15: Clarifying Question Flow

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

The persisted cognitive session now pauses on missing user-owned information,
stores expiring questions, emits them through trace and SSE, accepts one answer
through `POST /respond`, preserves the prior trace, re-runs representation,
canonicalizes a successful clarified problem, and rejects duplicate or expired
responses safely.

## Chapter 14: Constraint Discovery Engine

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

The controller now requires constraint discovery after representation and before
gap acquisition, hypothesis generation, or planning. The deterministic engine
records explicit constraints and derives time-window, privacy, data-availability,
payment/PCI, causality, confidence-threshold, resource, and success constraints.
Missing success conditions or user-owned decision boundaries route to
clarification. Accepted constraints update canonical state and persistence.

Constraints affect action selection: when sensitive-data handling is required,
the controller rejects registered capabilities not explicitly approved for that
data and can choose an approved recovery capability. A passing verification
report is also downgraded when it does not contain at least one check per
explicit success criterion, and its proposed final answer is withheld.

## Non-Blockers

- Redis caching, streaming run state, and rate limiting are not required before
  the first real engine works.
- Anthropic is not required before the OpenAI adapter proves the provider
  interface.
- Full eval harness work remains later chapter scope, though Chapter 13 should
  add focused golden examples.
