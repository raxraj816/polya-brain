# Architecture Decisions

Status: accepted for Chapter 2.

Source of truth: `../PolyaBrain_Product_Implementation_Master_Plan.md`

Purpose: record the architecture choices that unblock Chapter 3 while protecting
the PolyaBrain product vision. These decisions favor a narrow, auditable,
locally runnable technical investigation workbench before platform breadth or
research completeness.

## Decision Rules

- Follow the master plan when documents disagree.
- Keep the MVP modular in code and simple in deployment.
- Do not promote a concept into a core contract until it has a producer,
  consumer, verification path, failure-mode analysis, and product value.
- Prefer end-to-end loops over impressive isolated modules.
- Domain-specific behavior belongs in use-case packs, not in the core graph.
- Every serious answer must expose conclusion, confidence, evidence used,
  evidence against, checks performed, open questions, next action, and trace.
- Unsafe or weak engine output must route to clarification, research, reframe,
  replan, retry, or explicit insufficient evidence. It must not silently proceed.

## ADR Process

Architecture changes after Chapter 2 use `docs/adr/0000-template.md`.

Use an ADR when a change alters one of these surfaces:

- core contracts or first-class fields
- graph routing or engine boundaries
- persistence technology
- tool safety or approval behavior
- model/provider assumptions
- benchmark scope or scoring rules
- memory architecture
- deployment topology

Small implementation choices that do not affect these surfaces can stay in code
reviews, implementation notes, or tests.

## D-001: Build PolyaBrain Core Platform First

Status: accepted.

Owner: Acting Founding CTO.

Decision: PolyaBrain Core Platform is the product. The MVP implements the
stateful Polya loop first: problem input, representation, constraints, gaps,
evidence/tools, hypotheses, plan, execution, verification, reflection, and
report.

Rationale:

- This preserves the central product promise: help users understand,
  investigate, solve, verify, and learn from difficult problems.
- It avoids turning the project into a generic chatbot, domain demo, or
  neuroscience simulation.
- It gives every later use-case pack the same auditable core loop.

Tradeoffs:

- The first platform will feel narrower than the full long-term vision.
- Some domain-specific polish waits until the core loop proves value.

Verification path:

- The pre-platform proof harness already produces trace, evidence, hypotheses,
  verification, report, and baseline comparison artifacts.
- Chapter 3 and later chapters must preserve those user-visible artifacts while
  moving from local files to API and UI surfaces.

Revisit trigger:

- Only revisit if repeated user tests show the core loop is not the source of
  product value.

## D-002: Use A Python/FastAPI Modular Monolith First

Status: accepted.

Owner: Backend/platform owner.

Decision: Build one Python/FastAPI backend as a modular monolith. Engine modules
stay logically separate, but deployment stays single-process/single-service for
the MVP.

Rationale:

- Python fits Pydantic, LangGraph, AI/provider SDKs, data tooling, and local
  experimentation.
- FastAPI gives a small, typed API shell without heavy framework ceremony.
- A modular monolith reduces operational load while the product loop is still
  being validated.
- It keeps debugging, tracing, tests, and iteration fast for a solo or small
  team.

Rejected alternatives:

- Separate microservices per engine: too much deployment and observability cost
  before the loop is proven.
- Kubernetes-first deployment: infrastructure would outrun product validation.
- Non-Python backend: weaker fit for the immediate AI/data/orchestration stack.

Verification path:

- Chapter 3 must start the backend locally.
- Chapter 10 must expose the first session/run API shell.
- Tests must cover engine contracts before engines become complex.

Revisit trigger:

- Split services only after measured scaling, deployment, or ownership pressure
  makes the monolith a bottleneck.

## D-003: Use LangGraph For Stateful Orchestration

Status: accepted.

Owner: Orchestration owner.

Decision: Use one LangGraph state machine for the MVP Polya loop.

Rationale:

- The product requires explicit recoverable stages, not a hidden prompt chain.
- LangGraph supports stateful routing, loops, retries, and controlled
  transitions between engines.
- It maps naturally to stage gates: continue, clarify, research, reframe,
  replan, retry execution, finalize, or finalize with insufficient evidence.
- It can expose graph behavior in traces and diagrams.

Rejected alternatives:

- A linear script: too easy to let weak outputs flow forward.
- A multi-agent debate system: too much spectacle and too little control for
  the MVP.
- A bespoke graph runtime: unnecessary until LangGraph fails a concrete need.

Verification path:

- Chapter 6 defines `PolyaState`.
- Chapter 8 runs every stub engine through the graph and proves blocked stages
  stop safely.
- Chapter 9 records graph route decisions as trace events.

Revisit trigger:

- Revisit only if LangGraph blocks required state recovery, auditability, or
  deterministic routing.

## D-004: Use Postgres With pgvector As The First Durable Store

Status: accepted.

Owner: Data/platform owner.

Decision: Use Postgres 15+ with `pgvector` for sessions, artifacts, trace
events, evidence, hypotheses, plans, tool calls, model costs, feedback, and
logical semantic memory.

Rationale:

- The MVP needs relational consistency and inspectability more than specialized
  distributed stores.
- `pgvector` lets semantic memory begin inside the same operational database.
- Keeping semantic, episodic, and procedural memory in one physical store
  reduces local setup and debugging cost.
- Postgres supports migrations, indexing, transactions, and future production
  deployment cleanly.

Rejected alternatives:

- Neo4j first: graph traversal value is not yet proven.
- Pinecone/Milvus first: separate vector operations add cost and complexity
  before retrieval needs are measured.
- File-only persistence after the proof harness: insufficient for sessions,
  memory, feedback, cost, and auditability.

Verification path:

- Chapter 4 must create the database from migrations and insert/retrieve a
  sample session.
- Chapter 16 to Chapter 18 must prove semantic, episodic, and procedural memory
  can work logically in Postgres.

Revisit trigger:

- Add specialized stores only when benchmarked retrieval, graph traversal, or
  operational scale makes Postgres insufficient.

## D-005: Use Redis For Cache, Streaming Run State, And Rate Limits

Status: accepted.

Owner: Platform/runtime owner.

Decision: Add Redis in the local Docker Compose stack for cache, live run state,
rate limits, and future streaming support.

Rationale:

- Redis is a proven fit for transient state.
- It avoids overloading Postgres with short-lived polling and stream concerns.
- It supports the planned live trace UX through SSE or WebSockets.

Rejected alternatives:

- Postgres-only transient state: simple at first but likely to blur durable
  audit records with live runtime status.
- Kafka or other event infrastructure first: unnecessary for the MVP.

Verification path:

- Chapter 3 must include Redis in Docker Compose.
- Chapter 9 and Chapter 10 should preserve durable traces in Postgres while
  using Redis only for transient run state when needed.

Revisit trigger:

- Revisit if the MVP proves no live streaming or rate-limit need.

## D-006: Use Next.js For The Investigation Workbench UI

Status: accepted.

Owner: Frontend/product owner.

Decision: Use Next.js, TypeScript, Tailwind CSS, shadcn/ui, lucide-react, and
TanStack Query for the first frontend.

Rationale:

- The UI must expose workflow state, trace, evidence, hypotheses, verification,
  confidence, and final report clearly.
- Next.js and TypeScript provide a pragmatic path to a local product UI and
  later deployment.
- shadcn/ui and lucide-react support a utilitarian workbench interface without
  inventing a design system too early.

Rejected alternatives:

- Chat-only UI: violates the product boundary by hiding the Polya workflow.
- Dashboard polish before a useful loop: premature.
- Separate native app: not needed for the MVP.

Verification path:

- The first UI must make the reasoning workflow visible, not merely display a
  chat transcript.
- Chapter Block 1 in the acceleration playbook is complete only when a user can
  submit a problem, see a session, see trace activity, and read a saved report.

Revisit trigger:

- Revisit only if the frontend stack slows down the local product loop or blocks
  trace/evidence-heavy UX.

## D-007: Use Mixed Benchmark Categories From The Start

Status: accepted.

Owner: Evaluation owner.

Decision: Use the mixed benchmark surface from Chapter 1, while the first wedge
focuses on technical investigation.

Rationale:

- PolyaBrain must remain a general problem-solving core, not a hardcoded
  incident-response tool.
- Mixed categories expose wrong-problem framing, ambiguity, bad evidence,
  contradiction handling, tool choice, and verification behavior.
- The technical investigation wedge gives a practical first user workflow
  without narrowing the core architecture.

Required categories:

1. Mathematical reasoning.
2. Logic and puzzle solving.
3. Technical research.
4. Software debugging.
5. Algorithmic problem solving and coding contests.
6. Data analysis.
7. Planning and strategy.
8. Scientific/engineering reasoning.
9. Ambiguous or underspecified problems.
10. Adversarial or misleading problems.
11. Open-ended creative synthesis.

Verification path:

- Future eval cases must record problem statement, category, difficulty, allowed
  tools, expected behavior, ground truth or reference answer, expected
  clarification behavior, expected verification checks, and scoring rubric.
- Chapter 60 minimums remain the benchmark quality gate.

Revisit trigger:

- Revisit category weighting after enough real technical investigation usage
  exists to identify the first market wedge more precisely.

## D-008: Keep Domain Behavior In Use-Case Packs

Status: accepted.

Owner: Product architecture owner.

Decision: Domain-specific tools, schemas, playbooks, seed data, eval cases, and
report labels belong in use-case packs. The core graph owns engine contracts,
state, memory abstractions, tool registry, verification framework, trace UI,
auth, audit, and observability.

Rationale:

- This prevents payment fraud, DevOps, compliance, tutoring, or coding contest
  concerns from redefining the core.
- It keeps domain packs replaceable and testable against the same Polya loop.
- It protects the product from becoming a bundle of unrelated agents.

Use-case packs must not:

- change core graph routing directly
- bypass verification
- store memory without source metadata
- call tools outside the registry
- introduce domain assumptions into core prompts

Verification path:

- First domain-specific behavior starts as prompts, trace metadata, procedural
  strategy records, eval cases, or pack-local code before changing core
  contracts.

Revisit trigger:

- Promote domain concepts to core only after repeated cross-domain value is
  proven by evals and real runs.

## D-009: Use Small Typed Contracts And Stage-Gated Engine Results

Status: accepted.

Owner: Contracts/engine owner.

Decision: Define core contracts with Pydantic v2 first, then align database
schemas after model fields are stable. Every engine returns structured status,
confidence, missing inputs, recommended route, duration, errors, and version
metadata.

Rationale:

- The product depends on inspectable reasoning artifacts.
- Structured models make bad data fail clearly.
- Stage gates prevent low-confidence or incomplete outputs from silently moving
  through the loop.
- Contracts keep API, database, graph, and UI aligned.

Rejected alternatives:

- Prompt-only JSON without typed validation: too fragile.
- Expanding first-class fields for every idea: violates the core contract
  promotion rule.

Verification path:

- Chapter 5 tests model serialization and validation.
- Chapter 7 tests low-confidence and blocked routing behavior.
- Every engine-changing PR must include tests or eval coverage for new behavior.

Revisit trigger:

- Revisit individual fields only through the core contract promotion rule and an
  ADR when the change affects shared contracts.

## D-010: Version Reasoning Behavior And Preserve Audit Traces

Status: accepted.

Owner: Observability/evaluation owner.

Decision: Completed sessions must record code version, graph version, prompt
template versions, model provider and model version, tool versions, use-case pack
versions, evaluation case versions, memory snapshot references, configuration
flags, retrieval parameters, and verifier versions.

Rationale:

- Wrong answers must be debugged after the fact.
- Benchmark scores are meaningless if prompt, model, memory, and verifier
  versions are not visible.
- Trust requires a user-visible trace without exposing hidden chain-of-thought.

Verification path:

- Chapter 7 includes version metadata in engine results.
- Chapter 9 records engine start, completion, error, route decisions, and
  reasoning modes.
- Reports and session APIs expose structured trace and verification status.

Revisit trigger:

- Revisit only to add missing version dimensions discovered during eval failure
  analysis.

## D-011: Route All Tools Through A Risk-Aware Registry

Status: accepted.

Owner: Tool safety owner.

Decision: Tools must be defined with name, description, capabilities, input
schema, output schema, risk level, approval requirement, allowed roles, timeout,
and cost estimate. Tool calls must be logged with input, output, status,
duration, errors, approval, and linked evidence.

Rationale:

- The MVP must not perform unsafe autonomous actions.
- Tool output must become evidence with source metadata.
- Risk levels enable read-only automation while keeping medium/high-risk actions
  behind approval.

Verification path:

- Chapter 22 defines available data source metadata.
- Chapter 31 defines the tool registry.
- Chapter 43 requires human approval for medium/high-risk tasks.
- Security chapters later test prompt injection, tool injection, path traversal,
  SSRF-like fetch risks, and sandbox escape attempts.

Revisit trigger:

- Revisit only if real workflows require a risk category the current model
  cannot express.

## D-012: Keep The Pre-Platform Proof As A Regression Anchor

Status: accepted.

Owner: Evaluation owner.

Decision: The existing pre-platform proof harness remains a regression anchor
until the API/UI platform can produce equivalent or better artifacts.

Rationale:

- It proves the smallest useful investigation loop already works locally.
- It guards against replacing audited artifacts with infrastructure that hides
  the product value.
- It creates a concrete baseline for Chapter 3 onward.

Verification path:

- Run `python3 proofs/pre_platform/verify_pre_platform_proof.py --all` when
  changes could affect proof artifacts or product expectations.
- The platform version should eventually match or exceed the harness outputs:
  trace, evidence, hypotheses, verification checklist, report, and baseline
  comparison.

Revisit trigger:

- Retire the harness only after equivalent coverage exists in automated API/UI
  evals.
