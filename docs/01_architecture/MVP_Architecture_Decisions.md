# MVP Architecture Decisions

This document clarifies what to build first. It does not replace the master plan.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## MVP Shape

Build PolyaBrain Core Platform first as a modular monolith:

- One Python/FastAPI backend.
- One LangGraph state machine.
- One Next.js frontend.
- One Postgres database with `pgvector`.
- Redis for cache, streaming run state, and rate limits.
- Docker Compose for local development.
- Optional external LLM provider.
- Optional external search provider.

The code should be modular by engine, but deployment should stay simple until the end-to-end loop is useful.

## Build Now

- A domain-independent cognitive controller that selects state-dependent
  actions; models and external systems remain replaceable capabilities.
- An experimental cognitive-action model and capability registry kept outside
  core contracts until cross-domain evaluation proves promotion.
- Typed engine interfaces.
- Stateful Polya loop.
- Problem representation.
- Problem reframe pass using trace details rather than new core fields.
- Approach selection using existing product modes and problem types, inferred when the user does not provide a mode.
- Constraint discovery.
- Knowledge gap detection.
- Research and evidence evaluation.
- Divergent hypothesis generation, convergent filtering, and planning.
- Knowledge-rich analogical transfer from memory when structural similarity may help.
- Bounded reframe/incubation pass after evidence gathering, with verification required for any changed claim.
- Safe tool execution.
- Verification checklists by mode and replanning.
- Stage-gated routing so weak outputs ask, recover, reframe, gather evidence, or stop safely instead of flowing forward.
- Reflection and logical semantic, episodic, and procedural memory.
- Evaluation harness across mixed problem categories.
- User-visible trace, reasoning mode, evidence, hypotheses, final report, confidence, and open questions.

## Defer Until After MVP Proof

- Neo4j.
- Pinecone, Milvus, or other separate vector databases.
- Kubernetes.
- Separate microservices per engine.
- Fine-tuning.
- Reinforcement learning.
- Multi-agent debate.
- Autonomous production changes.
- Real PII storage.

## Memory Decision

Use three logical memory types in one physical store first:

- Semantic memory: `knowledge_chunks` plus `pgvector`.
- Episodic memory: sessions, reasoning events, evidence, and outcomes.
- Procedural memory: strategies, strategy scores, applicability rules, and tool patterns.

Move to a graph database only when measured retrieval or traversal bottlenecks justify it.

## Engine Decision

The MVP implementation uses nine logical modules:

1. Problem Representation Engine.
2. Constraint Discovery Engine.
3. Knowledge Gap Detector.
4. Research and Acquisition Engine.
5. Evidence Evaluation Engine.
6. Hypothesis and Reasoning Engine.
7. Execution Engine.
8. Verification Engine.
9. Reflection and Memory Engine.

Each engine needs typed input/output, tests, prompts, and telemetry.

The engines do not own the run independently. The cognitive controller owns
selection of the next action from canonical state. Engine, model, memory, and
tool results enter as observations and cannot directly finalize, verify, or
write durable learned knowledge without the corresponding kernel gates.

Creative problem-solving behavior belongs inside these engines, not in a separate "creativity engine." The Reasoning Engine owns divergent generation and convergent filtering. Memory retrieval owns analogical candidates. Verification owns falsification and contradiction checks. Reflection owns strategy learning from which hypotheses, reframes, and analogies helped or failed.

## Product Boundary

PolyaBrain is the core problem-solving platform. Domain-specific behavior belongs in use-case packs only.

Payment fraud, coding contests, DevOps incidents, compliance, research, tutoring, and enterprise decision support are validation or packaging surfaces, not separate core architectures.

## Source-Of-Truth Rule

If this document or any architecture/research document disagrees with the master plan, follow the master plan.
