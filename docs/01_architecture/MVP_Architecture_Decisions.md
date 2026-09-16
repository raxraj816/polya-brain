# MVP Architecture Decisions

This document clarifies what to build first. It does not replace the master plan.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## MVP Shape

Build **PolyaBrain Investigator** through the **PolyaBrain Cognitive Runtime** as
a modular monolith. This is the implementation shape of the first product, not
a decision to build a broad platform before proving user value:

- One Python/FastAPI backend.
- One LangGraph state machine.
- One Next.js frontend.
- One Postgres database with `pgvector`.
- Redis for cache, streaming run state, and rate limits.
- Docker Compose for local development.
- Optional external LLM provider.
- Optional external search provider.

The code should be modular by engine, but deployment should stay simple until the end-to-end loop is useful.

After the local product proof, the initial delivery target is a managed cloud
product and API. Runtime, capability, persistence, and provider boundaries must
remain portable to Indian or other sovereign cloud, enterprise private cloud,
and local execution. No model vendor or cloud provider owns the cognitive loop.

“PolyaBrain Intelligence OS” describes the eventual governed capability and
application platform. It is not MVP positioning and may be claimed only after
dependent applications, developers, and cross-domain proof exist.

## Build Now

- A domain-independent cognitive controller that selects state-dependent
  actions; models and external systems remain replaceable capabilities.
- A trace-derived temporary task model and hard per-run resource ledger kept in
  the experimental cognitive layer rather than duplicated in core state.
- Impasse-driven knowledge acquisition: retrieve or observe only when a
  verification-blocking gap exists, and select among memory, artifacts, APIs,
  web, calculation, measurement, simulation, experiment, code, and human input.
- Deterministic cognition for known procedures and fused semantic calls for
  compatible stages; nine logical engine responsibilities never imply nine
  model calls.
- Verified procedural consolidation whose transfer must be rechecked on the
  current task.
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
- A broad capability marketplace or Intelligence OS positioning.

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

An engine is a logical responsibility, not a required provider invocation.
Several compatible responsibilities may share one schema-validated semantic
call, while a known deterministic procedure may satisfy an engine with zero
model calls. The audit trace must disclose which occurred.

The engines do not own the run independently. The cognitive controller owns
selection of the next action from canonical state. Engine, model, memory, and
tool results enter as observations and cannot directly finalize, verify, or
write durable learned knowledge without the corresponding kernel gates.

Creative problem-solving behavior belongs inside these engines, not in a separate "creativity engine." The Reasoning Engine owns divergent generation and convergent filtering. Memory retrieval owns analogical candidates. Verification owns falsification and contradiction checks. Reflection owns strategy learning from which hypotheses, reframes, and analogies helped or failed.

## Product Boundary

PolyaBrain Investigator is the initial user-facing product. The PolyaBrain
Cognitive Runtime is its domain-independent intelligence core. The managed cloud
service is the initial delivery model. Language models, tools, knowledge sources,
and infrastructure providers are replaceable capabilities rather than product
identity.

Payment fraud, coding contests, DevOps incidents, compliance, research, tutoring, and enterprise decision support are validation or packaging surfaces, not separate core architectures.

The architecture wins only when it improves verified outcomes per unit of total
cost and user effort. General-purpose intelligence and Intelligence OS are
measured future claims, not properties conferred by modular architecture.

## Source-Of-Truth Rule

If this document or any architecture/research document disagrees with the master plan, follow the master plan.

## Chapter 73 identity boundary

Use OIDC through Authlib and revocable hashed opaque browser sessions for the
private beta. The API owns authentication/authorization; the frontend proxy and
screen are additional controls. Session ownership and private memory namespaces
are enforced in request dependencies and repository queries. Operator-local data
is not automatically shared. No database RLS claim is made. See
[Chapter 73](../03_implementation/Chapter_73_Authentication_And_Isolation.md) for
configuration, protocol tests, namespace migration, and remaining deployment gates.
