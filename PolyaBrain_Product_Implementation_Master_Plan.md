# PolyaBrain End-to-End Implementation Master Plan

Senior Staff Engineering Plan for turning the PolyaBrain idea into a useful, real-world product.

Date prepared: 2026-05-25

## 1. Product Decision

This section is the binding product-identity decision for every PolyaBrain
builder, document, architecture choice, benchmark, and roadmap chapter.

> **PolyaBrain is a product-first, initially cloud-hosted, model-agnostic
> Cognitive Runtime that turns difficult objectives into verified outcomes by
> acquiring knowledge on demand, using deterministic procedures whenever
> possible, invoking bounded model reasoning when necessary, and learning
> reusable procedures from verified work.**

PolyaBrain is a brain-inspired problem-solving intelligence system. To the
person using it, PolyaBrain is a cognitive workbench that helps them understand,
investigate, solve, verify, and learn from difficult problems. It must make
reasoning visible, evidence inspectable, uncertainty explicit, resource use
auditable, and learning reusable. These statements define the intended human
experience; “Cognitive Runtime” defines the technical architecture that must
produce it.

PolyaBrain is inspired by George Pólya's method: understand the problem, devise
a plan, carry out the plan, and look back. General-purpose intelligence is the
long-term architectural ambition. It is not the initial market category or a
claim that may be made without cross-domain evidence.

### 1.1 Product, Runtime, Deployment, OS, And Model Boundaries

These terms describe different layers and must not be treated as competing
product choices:

| Layer | Binding decision |
|---|---|
| Initial user-facing product | **PolyaBrain Investigator**, a verified technical problem-solving workbench for founders, engineers, researchers, technical product builders, and small technical teams. |
| Enduring intelligence core | **PolyaBrain Cognitive Runtime**, the domain-independent control system that owns task state, knowledge gaps, action selection, budgets, evidence admission, verification, recovery, and learning. |
| Initial delivery | A managed cloud product and API for fast iteration, provider routing, connected knowledge, and shared capability operations. The runtime must remain portable rather than cloud-dependent. |
| Later deployment surfaces | Indian or other sovereign cloud, enterprise private cloud, and local or edge execution when privacy, latency, resilience, economics, or procurement justify them. |
| Eventual platform category | **PolyaBrain Intelligence OS**, but only after external applications and developers depend on its runtime, capability contracts, procedure system, and governance. “OS” is an internal architecture before it is an earned market position. |
| Language models | Replaceable semantic processors for interpretation, candidate generation, synthesis, and difficult judgment. A model is never PolyaBrain and never owns the control loop. |
| Knowledge and action sources | Memory, web, files, code, databases, APIs, papers, calculators, simulators, experiments, sensors, and people are registered capabilities selected only when the current task warrants them. |

The initial product promise is:

```text
Bring PolyaBrain a difficult objective.
It determines what must be known and done,
acquires or asks for only what blocks progress,
executes the best available procedure,
verifies the result,
and leaves behind an auditable report and reusable learning.
```

The product is not a generic chat interface around this architecture. Chat may
be one interaction surface, but the unit of value is a verified problem outcome.

### 1.2 Product Evolution

Development is chapter-gated, not date-gated:

1. **PolyaBrain Investigator:** win a narrow, high-value technical
   investigation workflow with lower overhead than manual work and generic
   chat.
2. **PolyaBrain Cognitive Runtime API:** expose the proven task model,
   capability registry, evidence, verification, budgets, trace, and procedure
   interfaces to other products.
3. **Organizational intelligence:** build permissioned organizational evidence,
   episode, and verified-procedure networks without leaking or flattening
   tenant knowledge.
4. **Capability ecosystem:** allow governed external capabilities, evaluators,
   and procedure packs to extend the same runtime.
5. **PolyaBrain Intelligence OS:** claim the platform category only when the
   runtime has real dependent applications, developers, and cross-domain proof.

Each stage must earn the next. Infrastructure breadth, integrations, and
platform language may not outrun demonstrated user value.

### 1.3 Non-Negotiable Intelligence Hierarchy

PolyaBrain is the problem-solving intelligence. An LLM is not PolyaBrain and
must never become the implicit owner of the problem-solving loop. Language
models, web search, memory retrieval, calculators, code execution, databases,
simulators, APIs, documents, sensors, and human input are replaceable
capabilities that PolyaBrain may select when the current problem state warrants
their use.

The domain-independent cognitive kernel owns:

1. The goal and current problem representation.
2. Working state, assumptions, constraints, and unresolved knowledge gaps.
3. Candidate explanations, solution paths, and plans.
4. Selection of the next cognitive or external action.
5. Interpretation of action results as observations rather than automatic truth.
6. Belief and hypothesis updates after new observations.
7. Verification, recovery, stopping, and insufficient-evidence decisions.
8. Reflection and learning of reusable strategies from verified outcomes.

The governing control loop is:

```text
observe current state
  -> detect the obstacle to progress
  -> generate candidate cognitive actions
  -> select by expected usefulness, cost, risk, and constraints
  -> execute through a registered capability
  -> interpret and validate the observation
  -> update state and competing hypotheses
  -> verify progress
  -> continue, backtrack, reframe, ask, or stop
  -> reflect and learn
```

Technical investigation is the first executable proof surface because it
provides inspectable evidence and tools. It is not PolyaBrain's product identity
or long-term boundary. Mathematics, logic, research, debugging, data analysis,
planning, scientific reasoning, ambiguous input, and creative synthesis must
ultimately exercise the same cognitive kernel. Domain packs may add knowledge,
tools, and verification procedures, but they may not replace or directly route
the kernel.

Generality is a measured property, not an architecture claim. It is proven only
when the same state-dependent control cycle selects useful actions, recovers,
verifies, and learns across materially different problem categories.

### 1.4 Invention Mandate

PolyaBrain may invent and build any new algorithm, representation, runtime
mechanism, verifier, procedure language, memory mechanism, capability interface,
small specialized model, or infrastructure component required to win its
measured problem categories. The mandate is broad; promotion into the product
core is evidence-gated.

Every proposed invention must:

1. Resolve a demonstrated failure or binding limitation in a real product loop.
2. Have a defined producer, consumer, observable behavior, and failure mode.
3. Be evaluated against the simplest strong alternative and a direct-model
   baseline where applicable.
4. Improve verified outcome quality, cost, latency, transfer, safety, or user
   overhead materially enough to justify its complexity.
5. Begin in prompts, metadata, traces, research notes, optional capabilities,
   or evals until evidence justifies promotion into sacred core contracts.

This mandate does not authorize speculative neuroscience modules, an
unmeasured agent swarm, or foundation-model training for prestige. A proprietary
small model is justified only when accumulated verified traces show that it can
perform a stable operation better or cheaper than routing to existing models or
deterministic code.

### 1.5 Winning Standard

The primary optimization target is:

> **Verified useful outcomes per unit of total cost: rupees, time, tokens,
> compute, risk, and human attention.**

Minimizing model calls is subordinate to this target. Zero calls with a wrong
answer loses; an expensive call that uniquely enables a valuable verified
outcome may win.

PolyaBrain wins a problem category only when repeated held-out evaluation shows:

1. Verified outcome quality is at least as high as the strongest practical
   direct-model, full-context, ordinary-retrieval, and manual-workflow baselines
   relevant to that category.
2. Unsupported conclusions and verification failures are lower than or no
   worse than those baselines.
3. Total model calls, tokens, latency, money, acquisition work, or human effort
   produce a meaningfully better quality-cost frontier.
4. Verified procedural reuse reduces work on related second tasks without
   lowering outcome quality or transferring a procedure incorrectly.
5. Real target users voluntarily bring another difficult problem because the
   product's overhead is lower than the value it creates.

Required product metrics include verified task success, unsupported-conclusion
rate, cost and latency per verified outcome, calls and tokens per verified
outcome, deterministic completion rate, acquisition work, procedure reuse and
transfer savings, human intervention, and repeat use.

A narrow benchmark win must be labeled narrowly. “General-purpose” or
“Intelligence OS” superiority requires the same kernel to win across materially
different categories such as investigation, multi-rule reasoning, debugging,
planning, data analysis, and scientific problem solving.

### 1.6 First Product And Core Runtime Scope

The implementation must build the smallest useful **PolyaBrain Investigator**
through the **PolyaBrain Cognitive Runtime**:

1. A stateful Polya loop.
2. A typed problem representation layer.
3. Knowledge-gap detection.
4. Dynamic research and information acquisition.
5. Evidence evaluation.
6. Hypothesis generation and planning.
7. Tool execution.
8. Verification and replanning.
9. Reflection and memory update.
10. A user experience that exposes evidence, uncertainty, checks, resource use,
    and the final outcome clearly.

PolyaBrain must be tested across many problem types from the beginning. The MVP should not depend on one domain to prove the idea. It should use a **General Problem Benchmark Suite** covering math, logic, research, software debugging, data analysis, planning, scientific/technical questions, and intentionally underspecified problems.

Core job: given a messy problem in any supported domain, PolyaBrain should:

1. Understand the problem.
2. Discover constraints and missing information.
3. Retrieve internal and external evidence.
4. Generate hypotheses.
5. Execute data/tool checks.
6. Verify or reject hypotheses.
7. Produce an auditable investigation report.
8. Store the case, evidence, outcome, and lessons learned for future reuse.

The technical-investigation wedge earns the right to expand. Cross-domain
benchmarks simultaneously test that the core remains domain-independent.
Domain-specific logic belongs in optional use-case packs: tools, schemas,
playbooks, seed data, evaluation cases, and UI labels. Use-case packs may extend
the runtime but may not replace its controller, evidence gates, budgets, or
verification rules.

## 2. Sources Reviewed

The plan synthesizes the active local documents in this workspace:

- `docs/00_vision/PolyaBrain_Final_Foundational_Design.md`
- `docs/00_vision/PolyaBrain_Vision_Summary.md`
- `docs/01_architecture/Core_Architecture_Report.md`
- `docs/01_architecture/MVP_Architecture_Decisions.md`
- `docs/01_architecture/Nine_Engine_Framework.md`
- `docs/01_architecture/Stateful_Polya_Loop.md`
- `docs/01_architecture/Core_Data_Contracts.md`
- `docs/02_examples_and_benchmarks/Problem_Solving_Examples.md`
- `docs/02_examples_and_benchmarks/Benchmark_Categories.md`
- `docs/02_examples_and_benchmarks/Additional_Polya_Loop_Examples.md`
- `docs/03_implementation/Chapter_1_Start_Here.md`
- `docs/04_research/Concept_to_Code.md`
- `docs/04_research/Polya_Principles_to_Practice.md`
- `docs/04_research/Research_Reading_Guide.md`

The plan also preserves and references historical source material under `docs/archive/`, including older implementation plans, fraud-focused research reports, and duplicate PDF, DOCX, and PPTX source exports. Archived documents are background context only; the master plan remains the implementation source of truth.

## 3. Senior Staff Architecture Decisions

### 3.1 Keep the MVP Smaller Than the Vision

The long-term documents describe nine engines plus semantic, episodic, and procedural memory. That is the right target architecture, but the MVP should not start with separate distributed services for every engine. Start modular in code, monolithic in deployment.

MVP architecture:

- One Python/FastAPI backend.
- One LangGraph state machine.
- One Next.js frontend.
- One Postgres database with `pgvector`.
- Redis for cache, streaming run state, and rate limits.
- Optional external LLM provider.
- Optional search provider.
- Docker Compose locally.
- Cloud deployment only after the end-to-end loop works locally.

Before investing in the full platform shell, run a pre-platform proof harness for
the technical investigation wedge. The harness should produce trace, evidence,
hypotheses, verification checklist, report, and direct LLM baseline comparison
artifacts from one local command. This proof does not replace the MVP
architecture; it prevents infrastructure from outrunning validated product value.

Add Neo4j, Kubernetes, model fine-tuning, multi-agent debate, and separate microservices only after the MVP proves value.

### 3.2 Map the Nine Engines Into Buildable Modules

The MVP code should still reflect the final architecture:

1. Problem Representation Engine
2. Constraint Discovery Engine
3. Knowledge Gap Detector
4. Research and Acquisition Engine
5. Evidence Evaluation Engine
6. Hypothesis and Reasoning Engine
7. Execution Engine
8. Verification Engine
9. Reflection and Memory Engine

Each engine is a Python module with typed input/output, tests, prompts, and telemetry.

### 3.3 Use Three Memory Types, One Physical Store First

The documents recommend semantic, episodic, and procedural memory. Implement all three logically, but store them initially in Postgres:

- Semantic memory: `knowledge_chunks` table plus `pgvector` embeddings.
- Episodic memory: `problem_sessions`, `reasoning_events`, `evidence_items`, `case_outcomes`.
- Procedural memory: `strategies`, `strategy_scores`, `strategy_applicability`, `tool_patterns`.

Move procedural memory to Neo4j only when graph traversal becomes a real bottleneck.

### 3.4 Product Quality Bar

The MVP is useful only if users trust it. Every final answer must include:

- Final conclusion.
- Confidence level.
- Evidence used.
- Evidence against.
- Checks performed.
- Open questions.
- Recommended next action.
- Full audit trace.

The product must say "insufficient evidence" when verification fails.

To reduce compound failure across the loop, every stage must be stage-gated. Each engine must either produce useful structured output, ask for missing information, route back for better evidence or framing, or stop safely with an explicit insufficient-evidence state. No stage should silently pass weak output forward as if it were verified.

### 3.5 Version Everything That Affects Reasoning

PolyaBrain behavior must be reproducible. Every completed session should record:

- code version,
- graph version,
- prompt template versions,
- model provider and model version,
- tool versions,
- use-case pack versions,
- evaluation case versions,
- memory snapshot references,
- configuration flags,
- retrieval parameters,
- verifier versions.

This is required so a wrong answer can be debugged later and so benchmark scores mean something over time.

### 3.6 Creative Problem-Solving Intelligence

Recent creativity and problem-solving research should improve PolyaBrain only when it becomes inspectable product behavior. The MVP should implement creative intelligence as disciplined reasoning mechanisms, not neuroscience labels or a user-facing "daydreaming" gimmick.

Build these mechanisms into the existing Polya loop:

1. **Divergent hypothesis pass:** generate several meaningfully different hypotheses, mechanisms, or solution paths before ranking. Do not over-score ideas during the first generation pass.
2. **Convergent filtering pass:** rank and prune hypotheses using constraints, evidence, verification cost, feasibility, falsifiability, and risk.
3. **Knowledge-rich analogical transfer:** retrieve structurally similar past cases, strategies, and patterns, including cross-domain cases when useful, then require the system to state what transfers and what does not.
4. **Incubation/reframe pass:** after initial research and evidence evaluation, produce candidate reframes, overlooked assumptions, and alternative angles. Any reframe that affects the answer must return through evidence evaluation and verification.
5. **Trace-visible reasoning modes:** reasoning events should expose whether the system is exploring, reframing, comparing, verifying, executing, or reflecting.

Anti-goals:

- Do not claim to simulate the default mode network, executive network, salience network, cerebellum, or any biological brain structure.
- Do not expose brain-region terminology in the product UI unless it is part of a research explanation requested by the user.
- Do not let novelty outrank truth. Creative candidates must still be testable, evidence-linked, and allowed to fail.

### 3.7 Problem Framing and Mode-Specific Verification

Practical problem-solving research and expert advice reinforce a product rule: PolyaBrain must avoid solving the wrong problem with impressive execution. The MVP should therefore add lightweight framing and checklist behavior inside the existing loop, not a new engine or core schema expansion.

Build these mechanisms:

1. **Problem reframe pass:** before hypotheses, generate the literal problem framing, a possible deeper framing, and a wrong-problem warning when applicable.
2. **Approach selection:** classify the task into the existing product mode and problem type, then choose the matching playbook or checklist.
3. **Verification checklist by mode:** use different required checks for technical research, debugging/root-cause analysis, architecture tradeoffs, data analysis, ambiguous input, and creative synthesis.

These mechanisms should be implemented first as prompt behavior, trace details, procedural strategy records, and eval criteria. Do not add new core fields unless implementation proves a stable producer, consumer, and product value.

## 4. Platform Scope and General Benchmark Suite

### 4.1 Core Platform Capabilities

The MVP must implement these domain-independent capabilities:

1. Accept a raw problem statement.
2. Convert it into structured problem representation.
3. Generate candidate problem reframes and warn when the user may be asking the wrong question.
4. Select the appropriate product mode, problem type, and verification checklist.
5. Extract explicit and implicit constraints.
6. Identify knowledge gaps.
7. Decide whether to ask the user, search memory, search external sources, or call tools.
8. Evaluate evidence quality.
9. Generate diverse, testable hypotheses before ranking.
10. Retrieve and evaluate relevant analogical patterns from memory when they may transfer.
11. Create an executable plan.
12. Execute safe tools.
13. Verify intermediate and final results using mode-specific checks.
14. Reframe or replan when verification fails or evidence reveals a better problem construction.
15. Reflect and update semantic, episodic, and procedural memory.
16. Show the reasoning trace to the user, including the current reasoning mode.

### 4.2 MVP Benchmark Categories

From Chapter 1, PolyaBrain should be evaluated on multiple categories:

1. **Mathematical reasoning:** word problems, optimization, algebra, probability, constraints.
2. **Logic and puzzle solving:** deduction, contradiction detection, grid-style reasoning.
3. **Technical research:** current APIs, libraries, papers, standards, and evolving technology questions.
4. **Software debugging:** codebase investigation, failing tests, root-cause analysis, patch planning.
5. **Algorithmic problem solving / coding contests:** LeetCode, HackerRank, Codeforces, Advent of Code-style problems; parse constraints, infer algorithms, prove complexity, implement code, generate edge cases, and verify against tests.
6. **Data analysis:** CSV/table interpretation, anomaly explanation, comparison, segmentation.
7. **Planning and strategy:** project planning, tradeoff analysis, implementation sequencing.
8. **Scientific/engineering reasoning:** hypothesis generation, experiment design, evidence evaluation.
9. **Ambiguous/underspecified problems:** cases where the correct behavior is to ask clarifying questions.
10. **Adversarial or misleading problems:** cases with false assumptions, bad evidence, or contradictions.
11. **Open-ended creative synthesis:** generate several possible approaches, use analogies or reframes when useful, and verify feasibility.

### 4.3 Optional Use-Case Packs

Use-case packs can be added after the core platform works, but they must not redefine the product. They are domain adapters over the same PolyaBrain loop:

1. DevOps/SRE incident investigation.
2. Software bug root-cause analysis.
3. Algorithmic problem solving and coding contest assistant.
4. Compliance change impact analysis.
5. Scientific/technical research assistant.
6. Math and first-principles tutoring/problem solving.
7. Enterprise decision analysis.
8. Payment fraud detection and fraud operations.

Payment fraud detection is a strong use case because it contains exactly the kind of reasoning PolyaBrain is designed for: messy signals, hidden causes, changing adversarial behavior, incomplete information, evidence gathering, hypothesis testing, verification, and high-value decisions. It should be implemented as a domain pack, not embedded into the core platform.

### 4.4 Out of Scope for MVP

- Autonomous production changes.
- Autonomous high-risk external actions.
- Fine-tuning custom models.
- Self-hosted large language models.
- Full production-grade multi-domain support.
- Separate graph database.
- Reinforcement learning.
- Complex browser automation.
- Real PII storage.

### 4.5 Product Modes

MVP supports four modes:

- **Investigate:** analyze a problem, anomaly, or incident and produce root-cause hypotheses.
- **Compare:** compare current metrics to baseline and explain differences.
- **Review:** evaluate a user's proposed conclusion against evidence.
- **Explore:** solve an unknown or underspecified problem by clarifying, researching, planning, testing, and reflecting.

Mode is optional user input. If absent, the Problem Representation Engine infers `mode` and `problem_type` from the raw problem, records the classification reason in the trace, asks a clarifying question when confidence is low or multiple modes are plausible, and allows user override.

## 5. Final Technology Stack

Backend:

- Python 3.11+
- FastAPI
- Pydantic v2
- LangGraph
- SQLAlchemy
- Alembic
- Postgres 15+ with `pgvector`
- Redis
- OpenTelemetry
- pytest
- ruff, black, mypy

Frontend:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- lucide-react
- TanStack Query
- Server-sent events or WebSockets for live run traces

AI and retrieval:

- OpenAI or Anthropic for reasoning.
- OpenAI/Cohere/local SentenceTransformers for embeddings.
- Tavily/Brave/Bing search for external research.
- Optional reranker after first retrieval pass.

Infrastructure:

- Local Docker Compose first.
- AWS later: ECS/Fargate or a small EKS cluster, RDS Postgres, ElastiCache Redis, S3, CloudWatch/Grafana.
- Terraform only when deploying shared/cloud infrastructure.

Security:

- No PII in prompts by default.
- Field-level masking before LLM calls.
- Tool allowlist.
- Audit log for all tool calls.
- Per-user/project RBAC.
- Secrets in `.env` locally and cloud secrets manager later.

### 5.1 API Contract v1

The first public/internal API should stay small and stable:

- `POST /api/v1/solve`: create a problem-solving session and start the Polya loop.
- `GET /api/v1/solve/{session_id}`: fetch current session state, final answer, evidence, trace, and verification status.
- `GET /api/v1/solve/{session_id}/stream`: stream live trace events with server-sent events or WebSockets.
- `POST /api/v1/solve/{session_id}/respond`: submit clarifying answers and resume a paused session.
- `POST /api/v1/feedback`: submit user feedback, corrections, and usefulness ratings.
- `GET /api/v1/memory/search`: inspect memory retrieval during development with source and confidence metadata.

The API must expose structured trace and verification status, not hidden chain-of-thought.

## 5.2 Use-Case Pack Contract

Every domain-specific capability must be added as a use-case pack. The core platform owns the Polya loop, engine contracts, state, memory abstractions, tool registry, verification framework, trace UI, auth, audit, and observability. Use-case packs own domain knowledge only.

Recommended structure:

```text
backend/app/use_cases/
├── software_debugging/
│   ├── schemas.py
│   ├── tools.py
│   ├── playbooks.py
│   ├── prompts.py
│   ├── seed_data.py
│   ├── eval_cases/
│   └── README.md
├── data_analysis/
├── technical_research/
├── math_reasoning/
├── algorithmic_problem_solving/
├── scientific_research/
├── devops_incidents/
├── compliance_analysis/
├── payment_fraud/
└── domain_template/
```

Each use-case pack must provide:

1. Domain schema extensions.
2. Tool definitions and permissions.
3. Seed domain memory.
4. Procedural playbooks.
5. Evaluation cases with expected outcomes.
6. Report labels and templates.
7. Safety constraints.

Each use-case pack must not:

1. Change the core graph routing directly.
2. Bypass verification.
3. Store memory without source metadata.
4. Call tools outside the registry.
5. Introduce domain-specific assumptions into core engine prompts.

## 6. Core Data Contracts

Core contracts should stay small and stable. Do not add a first-class field, score, ranking signal, or engine output unless it has a clear producer, consumer, user or engine value, verification/evaluation path, failure-mode analysis, and a reason it cannot begin as prompt behavior, optional metadata, trace detail, research note, or eval metric.

Research ideas should usually move through this path:

```text
research note -> prompt/trace/metadata experiment -> eval metric -> core contract
```

Only promote behavior into the core contract after it proves product value.

### 6.1 Problem Session

Fields:

- `id`
- `user_id`
- `raw_input`
- `domain`
- `mode`
- `status`
- `created_at`
- `completed_at`
- `final_answer`
- `confidence`
- `verification_status`

### 6.2 Structured Problem

Fields:

- `core_question`
- `problem_type`
- `domain`
- `knowns`
- `unknowns`
- `constraints`
- `success_criteria`
- `affected_entities`
- `time_window`
- `required_data_sources`

### 6.3 Knowledge Gap

Fields:

- `description`
- `gap_type`
- `priority`
- `why_needed`
- `suggested_source`
- `filled`
- `evidence_ids`

### 6.4 Evidence Item

Fields:

- `source_type`
- `source_uri`
- `claim`
- `raw_excerpt`
- `reliability_score`
- `relevance_score`
- `supports_hypothesis_ids`
- `contradicts_hypothesis_ids`

### 6.5 Hypothesis

Fields:

- `statement`
- `mechanism`
- `origin`
- `analogical_source_ids`
- `expected_signals`
- `evidence_for`
- `evidence_against`
- `verification_checks`
- `falsification_criteria`
- `confidence`
- `selection_rationale`
- `status`

Hypothesis diversity is evaluated at the run level, not stored as a core per-hypothesis score. Preserve plausible unusual candidates through `selection_rationale`, then select by evidence, constraint fit, and verification.

### 6.6 Plan Task

Fields:

- `id`
- `action`
- `tool_name`
- `params`
- `depends_on`
- `expected_output`
- `risk_level`

### 6.7 Reasoning Event

Fields:

- `id`
- `session_id`
- `engine_name`
- `event_type`
- `reasoning_mode`
- `summary`
- `metadata`
- `created_at`

`reasoning_mode` should use stable values such as `explore`, `compare`, `reframe`, `execute`, `verify`, and `reflect`.

### 6.8 Verification Report

Fields:

- `passed`
- `checks_run`
- `failed_checks`
- `contradictions`
- `confidence_delta`
- `recommended_route`

### 6.9 Tool Definition and Tool Call

Tool definition fields:

- `name`
- `description`
- `capabilities`
- `input_schema`
- `output_schema`
- `risk_level`
- `requires_approval`
- `allowed_roles`
- `timeout_seconds`
- `cost_estimate`

Tool call fields:

- `id`
- `session_id`
- `tool_name`
- `input`
- `output`
- `status`
- `started_at`
- `completed_at`
- `duration_ms`
- `error_type`
- `approval_id`
- `evidence_ids`

### 6.10 Artifact

Fields:

- `id`
- `session_id`
- `artifact_type`
- `name`
- `uri_or_storage_key`
- `content_hash`
- `metadata`
- `source`
- `sensitivity`
- `created_at`

Artifacts include code files, uploaded documents, tables, logs, web snippets, generated reports, screenshots, and benchmark fixtures.

### 6.11 Evaluation Case

Fields:

- `id`
- `category`
- `difficulty`
- `problem_statement`
- `artifacts`
- `allowed_tools`
- `expected_behavior`
- `ground_truth`
- `rubric`
- `tags`
- `version`

### 6.12 User, Organization, and Project

User fields:

- `id`
- `email`
- `display_name`
- `role`
- `organization_id`
- `created_at`

Organization/project fields:

- `id`
- `name`
- `settings`
- `budget_limits`
- `retention_policy`
- `enabled_tools`
- `created_at`

### 6.13 Feedback

Fields:

- `id`
- `session_id`
- `user_id`
- `rating`
- `feedback_type`
- `comment`
- `corrected_answer`
- `created_at`
- `review_status`

### 6.14 Connector

Fields:

- `id`
- `organization_id`
- `connector_type`
- `display_name`
- `status`
- `config`
- `secret_ref`
- `last_health_check_at`
- `last_error`
- `created_at`

### 6.15 Model Call and Cost Record

Fields:

- `id`
- `session_id`
- `engine_name`
- `provider`
- `model`
- `input_tokens`
- `output_tokens`
- `estimated_cost`
- `latency_ms`
- `status`
- `created_at`

## 7. Chapter-Based Implementation Plan

The plan assumes one strong developer with AI assistance. With a team, parallelize frontend, backend, infra, and evaluation streams.

### Phase 0: Commitment and Setup

#### Chapter 1: Product Lock and Repository Foundation

Tasks:

1. Write the one-page product brief: PolyaBrain Core Platform, benchmark categories, target users, MVP modes, non-goals.
2. Create or clean the repository structure: `backend`, `frontend`, `docs`, `infra`, `scripts`, `evals`.
3. Create `README.md` with local setup, vision, and current MVP scope.
4. Add `.env.example` with required keys.
5. Add `.gitignore`, editor config, and pre-commit config.
6. Create a GitHub project board or local issue tracker with this plan as the source.

Done when:

- Repo can be cloned by a new developer.
- MVP scope is visible in the README.
- No secret values are committed.

#### Chapter 2: Architecture Decisions and Risk Register

Tasks:

1. Write `docs/architecture_decisions.md`.
2. Record decisions: Python monolith first, Postgres+pgvector first, LangGraph orchestration, PolyaBrain core-first architecture, mixed benchmark suite from Chapter 1.
3. Write `docs/risk_register.md`.
4. List risks: hallucination, bad data, LLM cost, PII leakage, tool misuse, infinite loops, poor UX trust.
5. Define mitigation for each risk.
6. Create a lightweight ADR template.

Done when:

- Every major architecture choice has a reason.
- Every critical risk has an owner and mitigation.

#### Chapter 3: Local Development Environment

Tasks:

1. Create Python virtual environment.
2. Install FastAPI, Pydantic, SQLAlchemy, Alembic, pytest, ruff, mypy, LangGraph, Redis client, Postgres driver.
3. Create Docker Compose for Postgres, Redis, and backend.
4. Add Makefile commands: `make dev`, `make test`, `make lint`, `make migrate`.
5. Add `/health` endpoint.
6. Add CI job for lint and tests.

Done when:

- `make dev` starts the backend locally.
- `make test` passes.
- CI passes on a clean checkout.

#### Chapter 4: Database Baseline

Tasks:

1. Create database connection module.
2. Add Alembic.
3. Create tables for users, organizations, projects, sessions, artifacts, reasoning events, evidence items, hypotheses, plan tasks, tool definitions, tool calls, memory chunks, strategies, feedback, connectors, eval cases, and model-call cost records.
4. Enable `pgvector`.
5. Add seed script for local development.
6. Add migration tests.

Done when:

- Fresh database can be created from migrations.
- A sample session can be inserted and retrieved.

#### Chapter 5: Core Pydantic Models

Tasks:

1. Implement models for structured problem, knowledge gap, evidence, hypothesis, plan task, verification report, reflection.
2. Add validation rules for confidence scores and required fields.
3. Add serialization/deserialization tests.
4. Add fixtures for math, research, debugging, data-analysis, planning, and ambiguous-problem use cases.

Done when:

- All models round-trip through JSON.
- Bad data fails clearly.

### Phase 1: Stateful Polya Loop Skeleton

#### Chapter 6: LangGraph State Object

Tasks:

1. Define `PolyaState`.
2. Include session id, structured problem, gaps, evidence, hypotheses, plan, execution outputs, verification, reflection, iteration count, final answer.
3. Add `max_iterations`.
4. Add state reducer for event messages.
5. Write state initialization helper.

Done when:

- A raw input can become a valid initial state.

#### Chapter 7: Engine Interface Contract

Tasks:

1. Define base engine interface: `run(state) -> state`.
2. Add common telemetry wrapper.
3. Add engine result object with status, confidence, missing inputs, recommended route, duration, errors, and token usage.
   - Initial status values: `ok`, `needs_input`, `needs_evidence`, `low_confidence`, `blocked`, `failed`, `insufficient_evidence`.
   - Initial route values: `continue`, `clarify`, `research`, `reframe`, `replan`, `retry_execution`, `finalize`, `finalize_insufficient_evidence`.
4. Add version metadata for engine, prompt, model, tool, verifier, and graph version.
5. Add structured logging helpers.
6. Add tests for wrapper behavior, version propagation, and low-confidence/blocked routing.

Done when:

- All future engines can be implemented consistently.
- Engines cannot silently pass low-confidence or incomplete outputs to the next stage.

#### Chapter 8: Graph Skeleton

Tasks:

1. Add graph nodes for all nine engines.
2. Implement stub node functions.
3. Add graph routes: gaps to research, missing inputs to clarification, low confidence to clarification/research, verification failure to replan/research/execute, insufficient evidence to final report and reflection, and success to reflection.
4. Add iteration guard.
5. Export graph Mermaid diagram to docs.
6. Add a test that runs "What is 2+2?" through all stubs.
7. Add a test proving a blocked stage stops safely instead of continuing with weak output.

Done when:

- Graph runs end-to-end with stubs.
- Routing is visible in documentation.
- The graph is recoverable, not a blind linear chain.

#### Chapter 9: Event Trace System

Tasks:

1. Add `reasoning_events` persistence.
2. Store each engine start, completion, error, route decision, and reasoning mode.
3. Add API endpoint to fetch session trace.
4. Add tests for event ordering.
5. Ensure logs do not store secrets.

Done when:

- Every run produces an inspectable trace.
- Users can tell whether the system was exploring, comparing, reframing, executing, verifying, or reflecting at each major step.

#### Chapter 10: API Shell

Tasks:

1. Create `POST /api/v1/sessions`.
2. Create `GET /api/v1/sessions/{id}`.
3. Create `GET /api/v1/sessions/{id}/events`.
4. Create `POST /api/v1/sessions/{id}/run`.
5. Add OpenAPI tags and examples.
6. Add API tests.

Done when:

- A client can create and run a session through the stub graph.

### Phase 2: Problem Understanding

Phase 2 introduces the first real intelligence outputs. Canonical engine outputs
should be persisted only after the producing engine completes successfully and
the output passes parser and contract validation. The initial Phase 2 persistence
boundary is a simple batch flush after successful engine execution; per-step,
streaming, and partial-output persistence are deferred until async/retry chapters
need them. Trace events remain the append-only audit history for accepted,
rejected, failed, or repaired outputs.

Implementation sequencing note: start Phase 2 with the fake-testable LLM client
boundary, then build prompt/parser infrastructure, then add the first real
provider adapter. This means Chapter 12-A can land before Chapter 11, Chapter
12-B can follow Chapter 11, and Chapter 13 should start only after both the
client and parser boundaries are testable. Keep Redis runtime features and
additional provider adapters out of the critical path for the first real engine.

#### Chapter 11: Prompt and Parser Design

Tasks:

1. Write problem-understanding prompt.
2. Define output JSON schema.
3. Include Pólya fields: given, unknown, constraints, goal, success criteria.
4. Include problem framing behavior: literal framing, possible deeper framing, and wrong-problem warning when applicable.
5. Include approach selection using existing product modes and problem types; infer mode when absent, ask when uncertain, and record the reason.
6. Add prompt examples for math, logic, software bug, research query, data analysis, planning, scientific reasoning, ambiguous input, low-confidence mode selection, and wrong-problem framing.
7. Add prompt version identifiers and changelog.
8. Add response parser with JSON repair and retry.

Done when:

- Prompt produces valid structured output on at least 10 local examples.

#### Chapter 12: LLM Client Abstraction

Tasks:

1. Add provider-neutral LLM client.
2. Support model name, temperature, max tokens, JSON mode if available.
3. Add per-attempt timeout, total retry deadline, and bounded retry rules. A
   structured-output repair must share the originating capability deadline.
4. Track token usage and estimated cost.
5. Add fake LLM client for tests.

Done when:

- Engines can use the fake client in tests and real provider locally.

#### Chapter 13: Problem Representation Engine

Tasks:

1. Implement engine using LLM client and parser.
2. Persist the validated structured problem to the `structured_problems` table
   after successful engine execution.
3. Emit trace details for selected framing, rejected alternate framing, and selected approach mode without adding new core contract fields.
4. Add deterministic fallback for obvious structured inputs such as simple math, missing-field requests, and benchmark examples.
5. Add tests using fake client.
6. Add golden examples.

Done when:

- Benchmark prompts parse into stable structured problems across several categories.

#### Chapter 13-C: General Cognitive Control Proof

Status: in progress in the current working tree. The same-model/same-tool
six-category full-outcome harness is implemented and offline contract-tested.
It now uses the Chapter 13-D fused two-stage semantic path under the same
per-call output ceiling as the direct condition. Model capability versions are
scoped to the configured model route, and retries plus structured-output repair
share a hard total capability deadline. On 2026-08-22, `openrouter/auto`
completed the math pair with both conditions passing, then returned empty
content on pagination. A pinned `deepseek/deepseek-v4-flash-0731` pre-fusion
diagnostic completed pagination with both conditions passing but exposed six
Polya model calls, 15,488 tokens, and 224,219 ms versus two direct calls, 2,369
tokens, and 11,419 ms. After fusion and deadline correction, the pinned route
again returned empty content before a pair completed. After correcting strict
OpenRouter parameter compatibility, `google/gemini-3.7-flash` completed a
post-fusion six-category qualification run: Polya and direct both passed 6/6,
but Polya used 32,725 tokens and 8,933 ms mean latency versus 14,945 tokens and
5,101 ms for direct. Polya used two model calls versus direct's three in the
recovery case, confirming controller-level call savings there, but the overall
run is not a win. Chapter 13-I then removed that redundant semantic work and
completed all 18 balanced pairs: Polya passed 18/18 with zero model tokens and
direct passed 17/18 using 47,656 tokens. The predeclared general gate remains
false because the 5.56-point pass-rate advantage is below 10 points. This is a
narrow known-procedure compute win, not end-to-end superiority. Chapter 13-J
subsequently passed its 24-pair synthetic adversarial epistemic-control gate at
equal measured quality with 65.2% fewer model calls and 31.8% fewer tokens.
Separately keyed blinded review and non-synthetic field cases still remain
required for a broader product-value claim; see
`docs/03_implementation/Chapter_13C_Outcome_Benchmark_Operations.md`.

Purpose: prove that PolyaBrain selects what to do next from explicit problem
state instead of merely advancing through a fixed chain of LLM prompts.

Tasks:

1. Define an experimental universal cognitive-action taxonomy covering
   understanding, clarification, reframing, decomposition, recall, research,
   observation, measurement, calculation, simulation, experimentation,
   hypothesis generation, comparison, planning, execution, verification,
   backtracking, stopping, and reflection.
2. Define experimental action-candidate, action-decision, and observation
   models outside the sacred core contracts.
3. Require every candidate to state its target obstacle or gap, purpose,
   expected observation, expected usefulness, cost, risk, required capability,
   and success/failure conditions.
4. Implement a deterministic controller that generates and ranks candidate
   actions from `PolyaState`; an LLM may propose candidates but cannot select or
   execute them without controller validation.
5. Route selected actions only through a typed capability registry with risk,
   permission, timeout, and audit metadata.
6. Treat capability results as observations that must be interpreted, linked to
   evidence, and checked before changing hypothesis status or confidence.
7. Demonstrate state-dependent recovery: at least one unexpected or failed
   observation must cause the kernel to choose a different next action.
8. Add interactive evaluation cases across the active benchmark categories,
   including clarification, research, calculation, inspection, experiment,
   verification, backtracking, and safe stopping behavior.
9. Compare against the same base model with the same tools so the evaluation
   isolates value created by the cognitive controller.
10. Keep action scores and policy details in experimental models and trace
    metadata until evaluation establishes stable producers, consumers, failure
    modes, and product value.

Done when:

- One executable observe-decide-act-update-verify loop runs without making an
  LLM the controller.
- The same controller selects appropriate next actions across materially
  different problem categories.
- Action decisions are auditable, bounded, and recover from at least one failed
  action.
- The proof records correctness, action quality, recovery, verification catch
  rate, latency, and cost against a tool-enabled direct-model baseline.
- Failed or inconclusive runs stop truthfully rather than producing a forced
  answer.

#### Chapter 13-D: On-Demand Task Learning and Compute-Efficiency Proof

Status: implementation proof and narrow exact-lookup outcome gate complete;
the general problem-solving outcome gate remains open. The 2026-08-22 offline
unfamiliar-task proof passes six cases across three paired structural families,
and the production-composed explicit-artifact live probe completes with zero
model calls. The premium-model post-evidence fused probe completes with two
calls. The repeated live four-condition unfamiliar-corpus gate also passes:
Polya 18/18 verified outcomes with zero tokens, full-context 17/18, and ordinary
retrieval 16/18. This supports only a narrow exact-lookup efficiency claim, not
general superiority. This
chapter moves the essential parts of Chapters 164, 167, and 168 into the first
cognitive-product proof. Low model-call count is
not a late performance optimization for PolyaBrain; it is part of the product
hypothesis that explicit state, targeted acquisition, deterministic procedures,
and verified reuse can substitute for repeated parametric inference.

Purpose: prove that PolyaBrain can construct a temporary task model, acquire
only knowledge that blocks the current task, spend expensive inference only
when it has positive expected verification value, and reuse verified procedures
on structurally related tasks.

Tasks:

1. Define experimental task-model, impasse, resource-budget, resource-usage,
   and expected-verified-progress models outside the sacred core contracts.
2. Derive a trace-visible temporary task model from canonical `PolyaState`;
   keep facts, unknowns, constraints, current impasse, evidence, plan, and
   verification status inspectable without creating a second source of truth.
3. Add a hard per-run ledger for model calls, external acquisitions, tokens,
   and normalized cost units. A capability that cannot fit the remaining
   budget must be rejected or routed to a cheaper recovery action before it is
   executed.
4. Use deterministic gap construction whenever explicit unknowns and declared
   sources already make the procedure known. Do not call a model merely to
   restate an inspectable missing field.
5. Rank cognitive actions by expected verified progress per marginal cost,
   subject to risk, provenance, privacy, and failure-history gates.
6. Fuse compatible semantic stages. One bounded deliberation may propose
   hypotheses, the smallest verification plan, and an inspectable analytic
   output; one independent conclusion check may verify and reflect. Logical
   engines remain separate responsibilities, not mandatory model calls.
7. Acquire knowledge only for the current blocking gap. Search is one possible
   acquisition capability alongside memory, supplied artifacts, APIs,
   measurement, calculation, simulation, experiment, code, and human input.
8. Admit new facts to canonical evidence only with source metadata and an
   evidence-quality decision. Failed acquisition must change the action or
   terminate truthfully.
9. Consolidate only verified completed behavior into procedural memory. Reuse
   must remain a proposal whose transfer is checked against current evidence.
10. Add unfamiliar micro-world cases whose rules, manuals, or APIs are supplied
    at run time and are intentionally absent from model pretraining.
11. Compare four conditions with fair capabilities and budgets where
    applicable: direct model, full-context brute force, ordinary retrieval, and
    PolyaBrain adaptive cognition.
12. Add paired transfer cases. The second structurally related case must record
    whether verified procedure reuse reduces model calls, tokens, or acquisition
    work without lowering outcome or verification quality.

Done when:

- A production-composed run exposes its task-model snapshots and complete
  resource ledger in the audit trace.
- Explicit unknowns route to deterministic gap construction with zero model
  calls for gap detection.
- Compatible hypothesis, planning, execution-analysis, verification, and
  reflection work requires at most two semantic model calls after evidence is
  available, unless a trace-visible recovery justifies more.
- The runtime technically prevents the configured model-call and acquisition
  budgets from being exceeded and stops with an honest terminal reason.
- At least six unfamiliar micro-world cases across at least three structural
  task families complete through the same loop.
- The benchmark reports outcome, provenance, verification, model calls, tokens,
  latency, acquisitions, normalized cost, and second-task transfer savings for
  all four conditions.
- PolyaBrain is not declared a winner until repeated held-out results show a
  useful quality-cost frontier improvement; structural fixture success alone is
  labeled implementation proof, not scientific validation.

#### Chapter 13-E: Verifier Factory and Procedure Compiler

Status: verifier implementation and narrow repeated live verifier gate complete;
governed procedure execution and trace-derived replay evidence are implemented;
real procedure-transfer and end-to-end general outcome gates remain open. On
2026-08-22, the six-case, two-family, three-repetition
premium-model comparison produced 18/18 correct Polya verdicts, zero false
passes, full criterion coverage, zero model calls, and zero tokens. Direct-model
and full-context checking also scored 18/18 while using 23,944 and 26,978
tokens; fixed ordinary retrieval scored 8/18 while using 30,901 tokens. Median
latency was about 2.2 ms for Polya, 4.9 seconds for direct-model checking, 13.4
seconds for full context, and 14.4 seconds for retrieval. This is evidence for a
narrow known-verifier efficiency win, not end-to-end or general superiority.
The experimental contracts remain outside canonical `PolyaState` while real
procedure transfer and broader task evidence are gathered.

Purpose: turn “verify the answer” and “learn from the run” from descriptive
model behaviors into executable system mechanisms. PolyaBrain should compile
declared success criteria, constraints, evidence requirements, and candidate
claims into inspectable verifier specifications; after a verified outcome, it
should compile the successful trace into a guarded, versioned procedure that
can be replay-tested before present-case use.

Tasks:

1. Define an experimental `VerifierSpecification` with objective, verifier
   kind, inputs, executable operation or capability reference, expected
   invariant, evidence requirements, independence level, applicability,
   timeout, cost, risk, and explicit failed/inconclusive semantics.
2. Define the verifier lifecycle `proposed -> validated -> executed ->
   passed|failed|inconclusive`. Reject a verifier that has no observable
   result, depends only on the claim it is checking, exceeds its declared
   boundary, or cannot distinguish failure from missing evidence.
3. Implement deterministic verifier synthesis for criteria whose procedure is
   known: exact evidence/provenance matching, numeric comparisons and
   tolerances, set and multi-rule constraint satisfaction, structured execution
   output checks, and contradiction requirements. Route genuinely semantic
   criteria to a registered bounded checker rather than pretending they are
   executable.
   Structured declarations must be fingerprint-bound to a trusted task-
   specification event; a model-authored plan cannot authorize its own
   thresholds or expected result.
4. Execute validated deterministic verifiers independently of candidate
   generation. Emit each specification, input binding, result, failure reason,
   and resource use into the append-only audit trace. Passing reports must
   cover every declared success criterion.
5. Define an experimental compiled-procedure format containing purpose,
   structural task family, applicability and preconditions, ordered capability
   steps, expected observations and postconditions, verifier specifications,
   provenance, resource profile, known failure modes, regression cases,
   version, and invalidation conditions.
6. Define the procedure lifecycle `observed -> proposed -> replay_tested ->
   verified -> deployed -> monitored -> retired`. A single success may create
   only an observed/proposed procedure; deployment requires replay tests or an
   explicitly narrow, mechanically proven procedure.
   Mechanical-proof promotion is restricted to an allowlisted verifier family
   with an inspectable invariant; it is not a generic caller override.
7. Compile procedures only from completed, reflected, verified runs. Remove
   volatile action ids and task-specific literals from the structural template,
   retain source-session provenance, and never compile unsafe autonomous
   permissions or unverified observations.
8. Add an applicability checker that returns applicable, inapplicable, or
   inconclusive with reasons. The runtime must not execute a recalled procedure
   when current constraints, capability versions, provenance requirements, or
   regression assumptions differ.
9. Replay a candidate procedure against stored regression cases before verified
   status. Every present-case reuse must run its verifier suite again; memory is
   a proposal, never present truth.
   Replay evidence must be generated by governed execution of the proposed
   procedure, not accepted as a caller's unsupported success assertion.
10. Integrate verifier and procedure artifacts through experimental trace
    metadata and existing procedural-memory metadata before considering a core
    contract or database migration.
11. Add held-out multi-rule reasoning and small debugging/structured-output
    cases, including poisoned memory, incorrect applicability, partial success,
    contradictory evidence, stale capability versions, and deliberately weak
    self-verification.
12. Compare PolyaBrain with direct-model, full-context, and ordinary-retrieval
    conditions on verified outcome, false-pass rate, criterion coverage,
    procedure transfer accuracy, calls, tokens, latency, and total normalized
    cost.

Done when:

- At least two materially different task families synthesize and execute typed
  verifier suites whose individual results are visible in the trace.
- A verifier cannot pass merely because a candidate or model says that it
  passed; deterministic checks use independently bound evidence or execution
  output, and semantic checks remain explicitly bounded and auditable.
- A completed source task produces a typed procedure; replay on a structurally
  related task saves work without reducing verification quality.
- An inapplicable, stale, poisoned, or unverified procedure is rejected before
  execution, with the reason visible in the trace.
- Present-case verification catches at least one deliberately incorrect reused
  result and routes to recovery or insufficient evidence.
- Repeated held-out results demonstrate a better verified quality-cost frontier
  before the mechanism is promoted into canonical contracts or described as a
  general intelligence win.

#### Chapter 13-F: Adaptive Cognitive Scheduler and Capability Health

Status: complete in the current working tree. Chapter 13-D introduced declared costs and hard run
budgets; Chapter 13-E demonstrated that real model routes can be correct yet
slow, unavailable, or wasteful. This chapter makes observed capability health a
bounded input to action selection without allowing cost or latency to override
safety, provenance, applicability, or verification requirements.

Purpose: learn which registered capability is likely to create verified
progress for the present task family, action type, and resource budget. Polya
must distinguish declared capability metadata from empirical operational
reliability, verified-outcome contribution, latency, calls, tokens, and cost.

Tasks:

1. Measure capability duration at the registry boundary and retain it in the
   audit trace next to action id, capability version, status, and resource use.
2. Define experimental performance-sample, capability-profile, and adaptive-
   estimate contracts outside canonical `PolyaState`.
3. Learn only from bounded trace-derived samples. Separate operational success
   from contribution to a completed verified outcome; a tool returning output
   is not automatically evidence that the action was useful.
4. Key profiles by task family, action type, capability, and version. A version
   change starts a new profile rather than inheriting stale reliability.
5. Use conservative priors and sample-confidence weighting so one success or
   failure cannot dominate routing. Bound every learned adjustment.
6. Adjust expected verified progress and effective marginal cost using observed
   reliability, verified yield, latency, model/external calls, tokens, and
   normalized cost. Preserve the controller's hard budget, permission,
   sensitive-data, applicability, and failure-history gates before ranking.
7. Emit the selected and rejected adaptive estimates into the action-decision
   rationale or trace metadata so a user can inspect why a cheaper, faster, or
   more reliable capability was preferred.
8. Keep an in-process bounded ledger for the first experimental product path;
   define a durable tenant-aware boundary before production promotion.
9. Add degraded-provider tests showing that repeated timeouts/failures route a
   later related task to a healthy deterministic, memory, artifact, or human
   alternative when one can resolve the same obstacle.
10. Add recovery tests showing that sparse performance data never authorizes an
    unsafe capability, exceeds a budget, skips required evidence, or turns a
    failed verification into a conclusion.
11. Benchmark static routing against adaptive routing on rotated healthy,
    degraded, recovered, and version-changed capability conditions.
12. Report verified outcomes, wrong-route rate, recovery, calls, tokens,
    latency, regret relative to the best eligible action, and overhead added by
    the scheduler.

Done when:

- Every capability observation records bounded duration and resource telemetry.
- Repeated degraded-provider evidence changes a later eligible action choice,
  while a single failure does not cause permanent avoidance.
- A capability-version change does not inherit the previous version's profile.
- Adaptive routing improves or matches verified outcomes while reducing
  wrong-route calls, tokens, or latency against the static controller on
  repeated held-out degraded-provider cases.
- All safety, privacy, budget, evidence, and present-case verification gates
  remain effective under adversarial performance data.
- The scheduler adds less overhead than the work it avoids and exposes an
  auditable explanation for every adjustment.

Evidence: the repeated offline routing gate covers 12 held-out task families
and four capability regimes over five repetitions. Adaptive routing produced
60/60 verified route outcomes versus 45/60 for static routing, with 45 versus
60 external calls and 43,200 ms versus 160,500 ms of modeled capability
latency. The auditable artifact is
`evals/chapter_13f/results/2026-08-22/121908/summary.json`. This is a
scheduler-specific win and does not support a general-intelligence superiority
claim.

#### Chapter 13-G: Deadline-Aware Cognition

Status: complete in the current working tree. Live Chapter 13-C diagnostics showed that a small declared
call count can still create unacceptable latency when every provider attempt,
retry, and structured-output repair receives a fresh timeout. Chapter 12 now
supports a shared model-call deadline; this chapter extends bounded time into
the cognitive resource ledger and controller.

Purpose: ensure Polya can decide that there is not enough time left to admit a
capability, prefer another eligible route, or stop with insufficient evidence.
Wall-clock budget is a hard product constraint, not a soft ranking signal.

Tasks:

1. Add a maximum run-duration field to the experimental cognitive budget and
   measured duration to resource usage.
2. Charge actual capability duration through the same append-only resource
   events as calls, tokens, and normalized cost.
3. Include remaining wall-clock duration in reservation checks using each
   capability's declared timeout.
4. Reject a capability before execution when its worst-case timeout cannot fit
   the remaining run budget, and expose the shortage in the decision rationale.
5. Apply the same reservation and charging behavior to governed compiled
   procedures.
6. Ensure model retries and repair share the declared capability deadline; do
   not reset the deadline per attempt.
7. Add adversarial tests for zero remaining time, actual-duration charging,
   alternative-route selection, and safe stopping without a forced conclusion.
8. Report timeout/provider failures separately from reasoning or benchmark
   losses.

Done when:

- Every executed capability charges a non-negative measured duration.
- A capability whose declared timeout cannot fit is never called.
- A lower-timeout eligible route can be selected when a slower route is
  rejected.
- Exhausted time produces an auditable insufficient-evidence stop, not a final
  answer.
- Existing safety, privacy, call, token, and cost gates remain effective.

Evidence: focused tests prove alternative-route selection under a 20-second
remaining budget, zero-call insufficient-evidence termination at an exhausted
deadline, measured-duration charging, and pre-execution rejection of a compiled
procedure that cannot fit. The full repository verification passes 317 tests
with 23 integration tests skipped; Ruff, formatting, and strict mypy over 99
source files pass.

#### Chapter 13-H: Semantic Capability Broker

Status: complete in the current working tree for controller-registered
model-backed cognitive capabilities. Chapter 13-C showed different failure
behavior between `openrouter/auto` and a pinned model. Polya now owns bounded,
deterministic selection and fallback across explicitly configured semantic
routes instead of delegating availability to a single endpoint.

Purpose: treat model endpoints as replaceable semantic processors. The broker
selects and falls back among explicitly configured routes using schema-specific
health, declared order, circuit state, and one shared deadline. Models never
select the task action or authorize their own output.

Tasks:

1. Define experimental semantic-route, attempt, health-profile, and broker
   contracts outside canonical `PolyaState`.
2. Count every provider attempt, including transport retries and structured-
   output repair, as a real model call.
3. Key route health by cognitive capability and configured model slug/version.
4. Prefer healthy routes deterministically; open a bounded circuit after
   repeated failures without permanently blacklisting the route.
5. Preserve part of the total capability deadline for configured fallback
   routes rather than allowing the first route to consume the entire budget.
6. Fall back only on typed provider, timeout, unavailable, malformed-output, or
   schema-validation failure. A valid but unfavorable semantic result remains
   subject to controller and verifier recovery rather than silent rerouting.
7. Expose route order, success/failure kind, duration, and provider-attempt
   count in capability payloads and trace-visible resource accounting.
8. Support one primary and explicit fallback model slugs from settings, with
   deduplication and no implicit discovery or provider-controlled expansion.
9. Share a bounded in-process route-health ledger across production session
   runners; defer durable tenant-aware promotion until evaluation evidence.
10. Add tests for primary success, typed failover, deadline partitioning,
    circuit opening/recovery, version isolation, call accounting, and
    non-retryable semantic outcomes.

Done when:

- A typed failure on the primary route can complete through a configured
  fallback inside one hard capability deadline.
- Failed provider attempts are included in the model-call ledger.
- Repeated degradation changes route order, while probes permit recovery.
- Model-route changes start fresh health profiles.
- With no successful route, the capability fails safely and produces no final
  answer.
- The controller, safety, evidence, and present-case verification boundaries
  remain unchanged above the broker.

Evidence: eight focused broker tests prove primary success, typed failover,
deadline partitioning, actual retry/repair call accounting, circuit
opening/recovery, route-version isolation, non-fallback authentication failure,
and a no-answer all-route failure whose attempt history is visible in the
durable trace. The same policy now covers initial problem representation:
three-call primary failover succeeds, four-call exhaustion produces no
structured problem, and parser repair cannot restart the total deadline.
Bootstrap rejects more than one explicit fallback. The full repository suite
passes 338 tests with 23 integration tests skipped; repository Ruff,
affected-tree formatting over 156 Python files, and strict mypy over 102
application source files pass.

Bounded claim: this chapter proves typed route resilience and truthful resource
accounting across representation and controller-registered semantic
capabilities, not reasoning-quality, verified-outcome, or general-intelligence
superiority. Route health is intentionally process-local and not yet tenant
aware or durable.

#### Chapter 13-I: Evidence Closure and Semantic Necessity Gate

Status: complete in the current working tree for the first exact-attestation
mechanism. The stable Chapter 13-C qualification run passed all six
cases in both conditions but showed that Polya still spends two semantic calls
after a trusted tool observation already contains the complete answer. This is
the wrong compute behavior: known, independently checkable procedures must
close deterministically before the controller considers a model.

Purpose: make semantic computation conditional on residual uncertainty. A
trusted deterministic capability may attest that one exact, source-visible
claim covers every declared success criterion. Polya can then construct the
candidate, replayable check, verification report, final answer, and reflection
without asking an LLM to restate the same evidence.

Tasks:

1. Define an experimental trace-only deterministic evidence attestation with
   producer capability/version, exact claim hash, source URI, covered criteria,
   and checks performed. Do not add a canonical state field.
2. Accept attestations only from an explicit capability/version allowlist
   assembled by product composition; ordinary web, model, memory, and arbitrary
   artifact content are not trusted attesters.
3. Require one exact admitted evidence item, source provenance, claim/excerpt
   identity, maximum declared reliability and relevance, and exact coverage of
   every current success criterion.
4. Add a deterministic procedure that constructs a hypothesis, plan, and
   execution record from the attested claim, then independently recomputes the
   hash, provenance, producer version, and criterion coverage before finalizing.
5. Make the controller prefer this procedure at hypothesis and verification
   impasses only when a candidate attestation exists. A failed validation must
   produce no final answer and route back to semantic or evidence work.
6. Expose zero model-call use and the closure decision in the durable trace.
7. Give the direct benchmark condition the same attestation fields so the
   comparison does not hide information; measure whether Polya avoids calls and
   tokens while preserving correctness.
8. Add negative tests for forged producer version, changed claim, partial
   criterion coverage, multiple evidence claims, missing provenance, and
   non-deterministic source types.

Done when:

- A trusted complete tool result reaches a verified final answer with zero
  post-evidence model calls.
- Any integrity, provenance, trust, or coverage mismatch prevents finalization.
- Tasks without a valid attestation continue through the ordinary deliberator
  and conclusion-checker route.
- The mechanism improves quality-adjusted compute on held-out cases without a
  benchmark-only task ID, answer term, or hard-coded domain solution.

Bounded claim: this gate can eliminate redundant semantic work after a known
typed procedure. It does not make semantic entailment deterministic, validate
arbitrary retrieved text, or prove general problem-solving superiority.

Evidence: the controller now prefers an allowlisted deterministic evidence
closure procedure while retaining semantic fallbacks. Focused tests reject a
forged producer version, changed claim, partial criterion coverage, multiple
claims, missing provenance, untrusted source type, and tampered replay. Across
the repeated 18-pair same-model/same-tool live run at
`evals/chapter_13c/live_outcome_runs/2026-08-22/134337-16a8dce2/summary.json`,
Polya completed 18/18 verified outcomes with zero model calls, zero tokens, 3/3
recovery trials, and 3.38 ms mean latency. Direct completed 17/18 using 47,656
tokens and 5,158 ms mean latency. Both conditions received the same attestation
fields. The general Chapter 13-C superiority gate remains false because the
5.56-point pass-rate advantage is below its predeclared 10-point threshold.
This is a narrow quality-adjusted compute win for fully attested deterministic
tool results, not a general intelligence claim. The full repository suite
passes 338 tests with 23 integration tests skipped; repository Ruff,
affected-tree formatting over 156 Python files, and strict mypy over 102
application source files pass.

#### Chapter 13-J: Adversarial Epistemic Control Gate

Status: complete in the current working tree for the first synthetic
adversarial epistemic-control mechanism and automated gate. Chapter 13-I proved that a
fully attested deterministic result can close without semantic work. It did not
prove that Polya can govern incomplete, conflicting, stale, adversarial, or
unavailable information. Those are the cases in which deciding what to learn
next is itself the intelligence problem.

Purpose: make evidence acquisition conditional on an explicit residual
epistemic need. Polya must distinguish an answerable task from an unsupported
one, treat retrieved content as untrusted data, revise its acquisition strategy
after non-progress or conflict, and stop with insufficient evidence when no
eligible route can satisfy the remaining requirement.

Tasks:

1. Define a benchmark-local adversarial case contract covering answerable and
   intentionally unanswerable tasks, expected terminal status, required and
   forbidden evidence, source independence, temporal validity, conflict
   resolution, and prompt-injection resistance.
2. Derive an experimental trace-only epistemic requirement from the current
   gap and success criteria. Keep the canonical state contract unchanged until
   cross-domain evaluation proves the mechanism.
3. Derive evidence coverage, temporal status, contradiction state, acquisition
   progress, and remaining need from admitted evidence and evaluation trace.
4. Make gap resolution depend on the derived requirement rather than on tool
   success alone. A successful retrieval is not equivalent to justified belief.
5. Make repeated acquisition respond to the residual need: seek an independent
   source for corroboration, a current authoritative source for temporal
   conflict, or a discriminating source for contradiction. Do not repeat an
   unchanged query after an evaluated no-progress batch.
6. Treat all retrieved excerpts as data even when they contain instructions,
   claimed authority, or requests to ignore the user, policy, provenance, or
   verification boundary.
7. Stop safely when every eligible acquisition route, query budget, or hard
   cognitive budget is exhausted. The terminal artifact must expose the
   remaining gap and must not synthesize a forced conclusion.
8. Give a direct same-model baseline the same tools, observations, budgets, and
   untrusted-data warning. Score answer correctness and correct abstention
   separately so refusal cannot inflate ordinary accuracy.
9. Add cases for all-tools-fail, partial criterion coverage, conflicting
   sources, stale-versus-current authority, injected retrieved content,
   independent corroboration, and a false premise.
10. Run at least three repetitions with rotated condition order and report
    model calls, tokens, external calls, latency, unsupported conclusions,
    conflict-resolution accuracy, injection success rate, and abstention
    precision/recall.

Done when:

- No answer is finalized while a declared evidence requirement remains
  unsatisfied.
- Contradictory or stale evidence causes targeted acquisition or an explicit
  insufficient-evidence stop, never silent selection by source order.
- Retrieved prompt injection cannot change the action policy, authorize an
  undeclared tool, suppress provenance, or create a final answer.
- An answerable case is not refused merely because abstention is available.
- Every intentionally unanswerable case stops without an unsupported
  conclusion after bounded recovery.
- The repeated same-model comparison shows a predeclared advantage on
  quality-adjusted epistemic outcomes; otherwise the chapter records the loss
  and the next mechanism rather than claiming a win.

Bounded claim: this chapter evaluates and improves evidence governance. It does
not prove open-world factual correctness, safe autonomous world governance, or
general-intelligence superiority.

Evidence: the trace-derived policy now distinguishes initial acquisition,
corroboration, current authority, conflict resolution, discriminating evidence,
and satisfied states. Evidence evaluation accumulates independent current
support across batches, keeps contradictions durable, applies an explicit
authority gate, compares extracted claims instead of adversarial raw excerpts,
and records every requirement and query revision. Forty focused tests cover the
epistemic mechanism, acquisition integration, live harness, and controller
behavior. In the repeated 24-pair same-model/same-observation live run at
`evals/chapter_13j/live_runs/2026-08-22/141629-16a8dce2/summary.json`, Polya and
direct both passed 24/24 with 100% answer accuracy and 100% abstention precision
and recall. Polya used 24 model calls, 70,613 tokens, and 4,156 ms mean latency;
direct used 69 calls, 103,583 tokens, and 7,737 ms. External calls were equal at
45. Both had zero unsupported forced conclusions and zero forbidden-output
hits. The predeclared automated gate passed. A separately keyed 24-pair blinded
review packet is generated beside the run artifact; human review remains
pending, so `product_value_claim_ready` remains false. Repository-wide
regression verification passes 356 tests with 23 integration tests skipped;
repository Ruff, formatting over 161 Python files, strict mypy over 103
application source files, focused mypy over both Chapter 13-J evaluation
programs, and `git diff --check` pass.

#### Chapter 13-K: Non-Synthetic Investigator Product-Value Gate

Status: in progress in the current working tree. Chapters 13-D through 13-J
prove isolated mechanisms and synthetic quality-cost gates. They do not prove
that the production-composed Cognitive Runtime can investigate a real technical
defect from source-visible artifacts, identify the right failure mechanism,
recommend a testable correction, and produce lower-overhead value than a strong
direct same-model workflow.

Purpose: exercise the actual runtime against frozen, provenance-bearing defects
from real open-source projects and later fresh private field cases. Ground truth
must be executable wherever practical. The direct condition receives the same
issue description, source artifacts, failing observations, model route, and
resource ceiling. Structural report completeness is not a success metric unless
the diagnosis and next action are also correct.

Tasks:

1. Define an evaluation-only field-case contract containing origin, license,
   immutable upstream revision, problem statement, visible artifacts, hidden
   gold semantics, executable reproduction, success criteria, and contamination
   status.
2. Start with reduced reproductions of real defects from BugsInPy or an
   equivalent reproducible benchmark. Preserve upstream provenance and hashes;
   label reductions honestly rather than calling them full-project execution.
3. Give Polya and direct the same source-visible evidence packet. Do not expose
   the developer patch, fixed implementation, hidden rubric, or condition label
   to either condition.
4. Run Polya through the real `CognitiveRuntime`/`CognitiveKernel`, deterministic
   gap detection, explicit artifact acquisition, evidence evaluation,
   deliberation, verification, recovery, budget, and trace boundaries. Do not
   use the deterministic pre-platform report template as the Polya condition.
5. Preflight every case by showing that the frozen buggy reproduction fails and
   the corresponding fixed reproduction passes. A case that cannot reproduce is
   excluded and recorded, never silently scored.
6. Score diagnosis mechanism, implicated component, corrective action,
   evidence citation, check quality, unsupported claims, terminal truthfulness,
   model calls, tokens, latency, and acquisition work separately. Preserve raw
   outputs for independent review.
7. Generate a separately keyed condition-blind packet. Automated rubric results
   may qualify the harness but may not make `product_value_claim_ready` true
   without independent human review.
8. Add paired defects sharing a structural debugging pattern. Admit a reusable
   procedure only after the first result is executable and verified, then test
   whether the related second case reduces acquisition or semantic work without
   incorrect transfer.
9. Add fresh, post-selection technical cases from real product use after the
   public historical harness is stable. Report public-benchmark contamination
   risk explicitly.
10. Compare against at least the direct same-model condition first. Add current
    practical product and human-workflow baselines before any external product
    superiority claim.

First diagnostic field pilot (2026-08-22):

- The one-pair PySnooper reduced-reproduction pilot is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/145237-02dec531/summary.json`.
- The direct condition produced the correct concrete mechanism, exact one-line
  correction, and executable regression check in one call. The initial lexical
  rubric incorrectly scored that semantic answer as a failure; the scorer must
  retain this raw output as a regression case before another qualification run.
- Polya's real runtime correctly represented the problem and deterministically
  inspected all three explicit visible artifacts. It then spent two unnecessary
  model attempts on semantic admission of local source-visible evidence; the
  model evaluator failed its contract and Polya stopped safely with insufficient
  evidence. No unsupported conclusion escaped.
- The representation's four unknowns all required the identical explicit local
  artifact set, but the deterministic gap detector emitted four separate gaps.
  This creates avoidable reacquisition and duplicate-evidence failure risk.
- Required mechanism correction: when provenance, containment, readability,
  lexical relevance, source class, and temporal rules are deterministically
  decidable for explicitly selected local artifacts, evidence admission must not
  call a model. Multiple unknowns served by the same bounded local inspection
  must be consolidated before acquisition while preserving every unknown in the
  inspectable gap text. Semantic deliberation and verification remain separate;
  deterministic admission does not make artifact claims true by itself.
- The diagnostic result is a failed pilot, not evidence of product value. The
  configured route was `openrouter/auto`; it must not be described as a pinned
  premium model. Repeated qualification remains pending after the mechanisms and
  scorer are corrected and regression-tested.
- The corrected one-pair rerun is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/150142-02dec531/summary.json`. Direct
  passed in one call. Polya and direct happened to receive the same actual model
  from the auto route, and Polya reduced its model use to the single
  representation call, but Polya still stopped without a diagnosis.
- The rerun exposed two deterministic no-progress defects. Inspector-added line
  prefixes such as `1:` and `7:` entered numeric contradiction logic and created
  a false conflict between complementary issue and source-code excerpts. After
  that unresolved result, repeated inspection of the identical artifact snapshot
  was counted as success until the cycle ceiling. Source-location metadata must
  be stripped before semantic claim comparison, and a repeated unchanged local
  artifact snapshot must return an explicit no-new-evidence observation rather
  than masquerading as progress.
- A third diagnostic attempt at
  `evals/chapter_13k/live_runs/2026-08-22/150431-02dec531/summary.json` was not a
  valid comparison: both Polya representation provider attempts returned no text
  while the later direct request succeeded. The runtime stopped safely, but the
  harness mislabeled the pair as completed and treated the direct-only actual
  model identity as route equivalence. A condition with provider attempts and no
  successful response must make the pair provider-blocked, and actual-model
  equivalence requires a successful direct response plus either a successful
  same-model Polya response or a genuinely zero-attempt deterministic Polya
  result. Provider failure is not a cognitive-quality observation.
- The first healthy pinned-premium comparison is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/150846-16a8dce2/summary.json` using
  `google/gemini-3.7-flash`, selected from the account-filtered official model
  catalog because it declares structured-output support and no expiration. Both
  conditions used that exact actual model. Both identified the correct mechanism
  and correction, and both supplied an executable `check.verify` path-write
  assertion. The initial scorer rejected the check because it looked only at the
  normalized checklist field and ignored the concrete regression procedure in
  Polya's final report; full user-visible check content must be scored and the raw
  outputs retained as regressions.
- Correcting that scorer does not create a product win. Polya used three model
  calls and 14,518 tokens versus direct's one call and 3,063 tokens. The field
  case shows the next intelligence objective: deterministic task framing for
  explicit source-visible investigations where the representation procedure is
  known, followed by the smallest semantic proposal and an executable governed
  verifier. Additional prose-producing calls are overhead unless they improve a
  hidden outcome or replace human work.
- Chapter 13-K's next experimental mechanism is the source-patch verification
  loop. It starts outside core contracts: a bounded model proposal names one
  admitted source URI, one exact old substring, one replacement, one admitted
  check URI, a diagnosis, and a check summary. Deterministic guards require both
  files to be visible canonical evidence under an allowlisted root, require the
  old substring exactly once, and reject multi-file or ambiguous edits.
- A governed source-patch sandbox may then execute only an in-memory copy inside
  the existing ephemeral networkless, read-only-root, non-root Docker boundary.
  It receives no host mount and no hidden fixed artifact. It loads the patched
  source plus the independently supplied visible check and records a structured
  pass/fail output. A trusted deterministic verifier may finalize only when the
  sandbox output is present, error-free, bound to every declared criterion, and
  passes present-case replay. Failed execution cannot be repaired by a prose-only
  semantic verifier.
- The predeclared value hypothesis is one Polya proposal call versus one direct
  call, with Polya adding executable patch verification at zero model calls.
  Diagnosis correctness remains conjunctive. The harness must report model
  tokens and latency plus executable-verification rate and the remaining manual
  verification steps. A verified patch cannot compensate for a wrong mechanism,
  and an unexecuted proposal cannot receive the human-work-reduction credit.
- The first live one-call source-patch diagnostic is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/152119-16a8dce2/summary.json`. Polya
  proposed the correct one-line edit, passed the supplied check inside the
  networkless sandbox, and finalized deterministically with one model call,
  4,261 tokens, and 5,413 ms. Direct used one call, 3,324 tokens, and 3,923 ms
  and also proposed a valid check, although the initial lexical check scorer
  rejected its wording. The run is diagnostic because it has one repetition.
- That trace also exposed two attestation guards required before qualification.
  `execution_attestations` is harness-owned and must always be cleared from
  direct model output; observed historical failure is not present-case patch
  execution. The sandbox/verifier must emit and bind distinct facts for admitted
  source identity, diagnosis-to-edit grounding, exact edit application, and
  independent check success. One `patch_verified` boolean may not be represented
  as independent proof of every semantic criterion. The hidden semantic rubric
  remains the independent diagnosis scorer.
- The next tightened diagnostic at
  `evals/chapter_13k/live_runs/2026-08-22/152530-16a8dce2/summary.json` preserved
  those guards: Polya and direct each used one successful call, Polya proposed
  the correct edit, and only Polya's patch passed the admitted check in the
  sandbox. The report nevertheless missed the check rubric by one token at a
  71.4% overlap boundary despite stating that `verify` passes a `Path`, writes a
  trace string, and asserts matching file contents. This is a scorer defect, not
  permission to tune case phrases after every run.
- For an eligible condition, a harness-owned present-case pass of the admitted
  immutable regression check is conclusive evidence that the check requirement
  is satisfied. It may replace lexical check-description matching only for that
  criterion. Mechanism, correction, evidence reference, forbidden-conclusion,
  and unsupported-conclusion gates remain independently conjunctive. A
  model-authored claim, historical failing observation, or unbound execution
  event cannot receive this credit. Direct prose without execution continues to
  use the same frozen semantic check rubric.
- A failed source-patch proposal guard must preserve a safe reason code and the
  model-call/usage telemetry already spent; collapsing it to a generic exception
  makes compute governance and recovery impossible. Artifact identity is a
  deterministic resolution problem once the admitted set is known: accept the
  exact canonical base URI, or a unique exact filename among admitted artifacts.
  Never use fuzzy matching, infer an ambiguous file, or admit a new path from
  model output. The semantic model owns diagnosis and edit content; code owns
  canonical identity and guard enforcement.
- Inspector line numbers are provenance metadata, not executable source text.
  Exact-edit validation must deterministically reconstruct the admitted excerpt
  without those display prefixes before matching a model-proposed edit. The
  original numbered excerpt stays in evidence for audit, and the sandbox still
  rechecks the edit against the canonical allowlisted file before execution.
- The first six-case one-repetition diversity pilot is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/153208-16a8dce2/summary.json`. It is not
  a gate pass. Polya scored 4/6 and direct 5/6 with one call per case; all six
  Polya patches actually passed their admitted sandbox checks, although the
  harness reported 5/6 because it incorrectly coupled execution credit to the
  separate final semantic-verification result.
- The two observed Polya score failures were evaluation/finalization defects,
  not permission to count the run as passed. In `fastapi_skip_defaults`, both
  conditions explicitly diagnosed ignored `skip_defaults` and prescribed
  `response.dict(skip_defaults=skip_defaults)`, but long grammatical rubric
  phrases diluted the discriminating-token overlap. In `httpie_unset_header`,
  the correct edit and check passed, but diagnosis grounding demanded half of
  the newly introduced syntax words rather than accepting edit-context overlap
  plus the changed concept `None`.
- Semantic phrase support therefore uses the strict coverage rule, or—for
  phrases with at least four shared discriminating terms—a lower 50% coverage
  floor. Cross-case correct answers must remain negative controls, and generic
  wrong diagnoses must still fail. Diagnosis-to-edit grounding requires at
  least two source/edit context terms plus at least one changed term; it does not
  by itself replace the hidden diagnosis rubric. Executable-verification rate is
  derived solely from the trace-owned present-case sandbox pass, while terminal
  diagnosis success remains conjunctive with semantic verification.
- The deterministic rubric tokenizer must preserve full identifiers and also
  decompose snake_case and CamelCase into semantic components. Otherwise
  `skip_defaults`, `skip-default`, and `skip defaults`, or `ResponseModel` and
  `response model`, are falsely treated as unrelated. This normalization is
  case-independent and remains bounded by the same positive and negative
  regression controls.
- The corrected six-case diversity rerun is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/153746-16a8dce2/summary.json`. Polya and
  direct each passed 6/6 with one identical pinned-model call per case. Polya
  executed and passed 6/6 admitted checks versus 0/6 for direct, while using
  26,236 versus 20,012 tokens (1.311x) and 5,053 versus 3,692 ms mean latency.
  This supports proceeding to repetition; it is not a gate result or a cheaper-
  compute claim.
- The scorer, executable-attestation rule, case corpus, and value frontier are
  frozen before the three-repetition qualification. A later outcome-informed
  change invalidates that run and requires a new clearly identified evaluation
  generation. The predeclared advantage is equal model-call count and equal
  diagnosis quality plus trace-owned executable verification that replaces a
  manual step; token or latency superiority is not expected in this generation.
- The frozen three-repetition qualification is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/153932-16a8dce2/summary.json` and failed:
  direct passed 18/18; Polya passed 17/18, despite all 18 Polya patches passing
  their admitted executable checks. Polya used 18 model calls versus direct's
  19, but lower answer quality correctly prevented the value-frontier win.
- The lone failure was not a benchmark-rubric change. Polya proposed the correct
  `response.dict(skip_defaults=skip_defaults)` repair and passed the check, then
  its own deterministic finalizer suppressed the report because bare-token
  symmetric difference erased the changed qualified identifier
  `response.dict`. The 17/18 run remains failed. Any grounding correction begins
  a new evaluation generation.
- Diagnosis/edit grounding must preserve qualified code identifiers such as
  `response.dict`, `response.name`, and `value.decode` alongside their component
  tokens. A diagnosis is edit-grounded only when it overlaps the edit context
  and names at least one term or qualified identifier whose presence changes.
  The independent frozen semantic rubric still decides benchmark correctness.
- The generation-2 one-case regression pilot is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/154346-16a8dce2/summary.json`. The
  formerly suppressed skip-default case passed in both conditions with one call
  each, and Polya's admitted patch passed present-case execution. Evaluation
  generation 2 is frozen at this point before repeating the 18-pair run; the
  generation-1 17/18 failure is not overwritten or retrospectively rescored.
- The frozen generation-2 qualification is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/154420-16a8dce2/summary.json` and passes
  the automated historical gate. Polya passed 18/18 diagnoses and 18/18 admitted
  executable patch checks with 18 model calls. Direct passed 17/18 frozen-rubric
  diagnoses, executed 0/18 patches, and used 19 model calls because one output
  required schema repair. Every pair observed the same pinned actual model;
  Polya had zero unsupported/forbidden conclusions.
- The demonstrated advantage is narrow: verified outcome at no greater model-
  call count, not token or latency efficiency. Polya used 77,961 versus 64,455
  tokens (1.210x) and 5,575 versus 4,515 ms mean latency. Public historical
  contamination risk, reduced fixtures, a single provider/model, and the direct
  condition's one frozen-rubric paraphrase miss all remain explicit.
- `product_value_claim_ready` remains false. Independent condition-blind human
  review, fresh post-selection private field cases, and a controlled paired-case
  procedure-transfer result are still mandatory. The passing automated result
  must not be described as general intelligence, frontier-product superiority,
  full-repository autonomy, or a mandate to govern people or institutions.
- Generation 3 targets token efficiency without adding calls. The experimental
  source-patch capability receives a deterministic minimal-sufficient state
  projection containing only the represented problem, observed failing
  reproduction, constraints, success criteria, canonical admitted artifact
  identities, and full admitted excerpts. It must omit duplicated raw prompt,
  gap, hypothesis, plan, execution, verification, and trace state. Inspector
  display line numbers are removed from the model view while canonical URI
  provenance remains.
- The projection is capability-specific and versioned; it does not truncate an
  admitted source or check, omit contrary evidence, or summarize semantic
  content through another model. The normal full-state gateway remains the
  default for every other capability. A projection that cannot preserve the
  complete admitted evidence boundary must fail back to the full view rather
  than silently hide evidence.
- The generation-3 one-case context-compilation pilot is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/155136-16a8dce2/summary.json`. Both
  conditions passed with one call; Polya also passed the admitted executable
  repair and used 2,899 total tokens versus direct's 3,538 (0.819x). Polya input
  fell from 3,097 tokens in the generation-2 regression pilot to 1,674 (46.0%)
  without changing the corpus or external scorer. This is a pilot, not a
  repeated efficiency claim.
- The generation-3 six-case diversity run is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/155204-16a8dce2/summary.json` and failed
  quality at 5/6 despite 6/6 passing Polya sandbox checks. It nevertheless
  measured 16,252 versus 22,435 direct tokens (0.724x) and 6 versus 7 calls.
  The failed case used the semantically equivalent qualified reference
  `ResponseModel.dict` while the concrete edit used `response.dict`; the hard
  changed-token grounding rule again suppressed a correct report.
- Deterministic `diagnosis_grounded` therefore means only what code can prove
  without another semantic call: the diagnosis is nontrivially bound to the
  exact edit context through at least two source/edit identifiers. It remains
  separate from exact edit application and present-case check success. It does
  not certify prose-level causal correctness; the frozen external semantic
  rubric and human review own that judgment. Requiring exact changed-token
  overlap falsely conflates lexical form with semantic grounding and is removed
  in evaluation generation 4.
- The generation-4 regression pilot is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/155514-16a8dce2/summary.json`; the
  formerly suppressed case passed with one call per condition, a passing Polya
  sandbox check, and 0.777x direct tokens.
- The generation-4 six-case diversity pilot is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/155529-16a8dce2/summary.json`. Both
  conditions passed 6/6 with six calls. Polya passed 6/6 executable checks and
  used 15,939 versus 20,732 direct tokens (0.769x); Polya mean latency was 4,755
  versus 4,912 ms. Generation 4's product mechanisms, projection, corpus,
  external scorer, and value rule are frozen before repeated qualification.
- The frozen generation-4 repeated qualification is preserved at
  `evals/chapter_13k/live_runs/2026-08-22/155648-16a8dce2/summary.json` and passes
  the automated historical gate. Polya passed 18/18 diagnoses and 18/18 admitted
  executable checks with 18 model calls and 48,287 tokens. Direct passed 18/18
  diagnoses, executed 0/18 patches, and used 19 calls and 64,257 tokens. Polya
  therefore used 0.751x direct tokens (24.9% fewer) and one fewer call while
  adding present-case execution. Polya mean latency was 5,043 versus 4,358 ms,
  so latency superiority is not claimed.
- This is the first repeated evidence for the intended low-compute mechanism:
  deterministic framing, evidence admission, context compilation, sandbox
  execution, and verification surround one irreducible semantic proposal. It is
  still limited to six public historical reduced Python reproductions and one
  pinned model, with potential training contamination. It does not satisfy the
  independent-human, fresh-private, procedure-transfer, full-repository,
  cross-domain, or general-intelligence gates. `product_value_claim_ready`
  remains false.
- Blind review artifacts must remove both case-local and repository-root paths
  recursively from visible evidence and every response field. Replacing paths
  only in the problem packet is insufficient because a response can cite an
  absolute URI containing the product/repository name and leak condition
  provenance. Regenerating a sanitized packet from frozen raw results does not
  change outputs, scores, or the evaluation generation; the separate condition
  key retains the untouched audit mapping.

Done when:

- Every admitted case has immutable provenance plus failing-buggy and
  passing-fixed executable preflight evidence.
- Polya's result comes from the production-composed cognitive loop and exposes
  the selected actions, admitted evidence, checks, uncertainty, and resources.
- Both conditions are scored on the same hidden semantic rubric and independent
  human reviewers receive condition-blind outputs.
- Repeated evaluation preserves outcome quality and safety while showing a
  predeclared material advantage in either correctness, unsupported-conclusion
  rate, total compute, latency, or human investigation overhead.
- A related second-task study shows verified procedural transfer lowers work;
  otherwise no compounding-intelligence claim is made.
- `product_value_claim_ready` remains false until non-historical field cases and
  independent review pass.

Bounded claim: passing this chapter's first public historical gate would prove
that Polya's runtime can be evaluated end to end on field-derived executable
defects. It would not establish contamination-free current frontier
superiority, general software-engineering autonomy, or cross-domain general
intelligence.

#### Chapter 13-L: Investigator Runtime Delivery

Status: local runtime delivery gate complete. Deliver the proven runtime through the local product
entrypoint while Chapter 13-K's independent review and fresh-case gates remain
open. This chapter does not declare those gates passed.

The public `polyabrain investigate` command must run the same configured
Cognitive Runtime as the API and export its actual state, evidence, hypotheses,
execution results, verification, reflection, resource ledger, and report.
Curated template demonstrations remain under an explicit `proof` command.
Known deterministic tasks work offline; other tasks require the existing
OpenRouter configuration and stop honestly when it is unavailable. No provider
credentials or settings dump may enter exported artifacts.
Unconfigured semantic capabilities must not be registered as usable routes or
charge fictitious provider calls through a fake test client.

Deterministic representation must have its own zero-model-call capability
reservation. A zero-call budget must not reject known arithmetic or explicit
clarification merely because the semantic representation route reserves model
retries. The controller may select the deterministic route only when the
existing deterministic parser recognizes the input, and that capability must
reject an unrecognized input before any provider invocation.
The same reservation distinction applies to the existing deterministic arithmetic
deliberation and conclusion checks; a known procedure must not reserve model
tokens merely because it shares implementation with a semantic capability.

Before source-patch execution is exposed, bind both source and check contents
to complete admitted snapshots. Reject changed or partially admitted files
before launching a container, and record snapshot hashes with the execution.
Passing a supplied regression check demonstrates only that check's scope;
lexical diagnosis grounding is not independent proof of causal correctness.

Delivery gates:

1. One command produces real auditable outcomes without Postgres or Redis.
2. Verified completion, missing input, failed verification, unavailable provider,
   and budget exhaustion have truthful artifacts and distinct exit behavior.
3. Artifact exports are private by default, never overwrite an existing run,
   and identify code version, actual capability versions, budgets, and usage.
4. Local arithmetic, explicit-artifact lookup, and failure paths are checked
   through the public entrypoint; source-patch snapshot regressions pass.
5. Documentation distinguishes implementation proof, historical qualification,
   remaining product-value gates, and future frontend/cloud delivery.

Verification: 423 tests pass locally with database integration enabled against
a fresh migrated Postgres/pgvector instance. Ruff, formatting, strict mypy,
legacy proof artifacts, Chapter 11 examples, and Compose validation pass. No
new live provider superiority claim is made. The complete product, fresh-case
evaluation, independent review, frontend, and cloud gates remain open.

#### Chapter 13-M: Recoverable Local Investigations

Status: local recovery gate complete. Close the local workflow gap between a
bounded run, a clarification, and the next useful action before frontend polish.

Persist validated state at capability boundaries in an owner-private local
recovery store. Reports are exports, never executable checkpoints: recovery
must load only the local store, preserve the original budget and accumulated
usage, require the same runtime code and capability configuration, and consume
each checkpoint at most once. Record an in-flight marker before dispatch;
uncertain interrupted calls must never be silently replayed or charged as zero.
Concurrent recovery must not duplicate external work. Redaction that changes
state makes that snapshot ineligible for execution.

Expose `polyabrain resume RUN_DIRECTORY`. Continue safely completed cycles
without repeating their tools. For a missing-input pause, accept a full revised
problem through `--answer`, revalidate its representation and all conclusions,
and preserve session identity, prior resource charges, and parent audit lineage.
Answering does not grant additional tool permissions or reset any resource cap.
Export each continuation into a new private directory and retain earlier reports.

Verification gates: public CLI continuation and clarification; uninterrupted
versus resumed outcome equivalence; cumulative budget enforcement; concurrent
and repeated claim rejection; modified export and checkpoint rejection;
in-flight interruption refusal; configuration/code mismatch refusal; and honest
documentation of recovery limits. This does not complete fresh-case evaluation,
independent review, repeat-use, frontend, or cloud delivery gates.

Validation: 433 tests pass with database integration enabled against an isolated
fresh Postgres/pgvector instance; repository lint, backend formatting, and strict
mypy pass. A public CLI pause/resume produces a verified arithmetic report with
zero model calls and preserved session identity. See
`docs/03_implementation/Chapter_13M_Recoverable_Local_Investigations.md` for
private-store retention, frozen-evidence semantics, and unreconciled in-flight
or terminal-export failure boundaries.

#### Chapter 14: Constraint Discovery Engine

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Tasks:

1. Implement explicit constraint extraction.
2. Implement implicit constraint extraction: time window, privacy, data availability, PCI, causality, confidence threshold.
3. Add validation that every final answer must satisfy success criteria.
4. Store constraints in state.
5. Add tests for missing/ambiguous constraints.

Done when:

- System can identify what must be true for an answer to count as solved.

#### Chapter 15: Clarifying Question Flow

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Tasks:

1. Detect when required fields are missing.
2. Add `needs_user_input` session status.
3. Generate clear clarifying questions.
4. Add endpoint to submit clarifying answers.
5. Pause the graph with status `awaiting_user_input` and emit the question through the live trace stream.
6. Resume the same session after `POST /api/v1/solve/{session_id}/respond`.
7. Track clarifying questions and user answers in the session trace.
8. Add timeout behavior for abandoned clarification flows.
9. Re-run understanding after answer is provided.

Done when:

- Ambiguous input leads to a useful question instead of fake certainty.
- A paused session can resume without losing trace, evidence, or prior state.

### Phase 3: Memory Foundation

#### Chapter 16: Semantic Memory Schema

Status: complete on the active branch. Sourced, reliability- and
freshness-gated pgvector ingestion/retrieval is documented in
`docs/03_implementation/Chapter_16_20_Memory_Foundation.md`.

Tasks:

1. Add `knowledge_chunks` table with embedding vector.
2. Add chunk metadata: source, domain, created_at, reliability, tags.
3. Add ingestion service.
4. Add retrieval service.
5. Add tests with local embeddings/fake embeddings.

Done when:

- Text chunks can be inserted and retrieved by similarity.

#### Chapter 17: Episodic Memory Schema

Status: complete on the active branch. Only verified, reflected completed runs
are admitted, with similarity retrieval tested across five problem categories.

Tasks:

1. Add case summary fields.
2. Link sessions to outcomes and reflections.
3. Add query for similar historical sessions.
4. Add fixtures for past solved problems across math, debugging, research, planning, and data analysis.
5. Add tests.

Done when:

- New sessions can retrieve similar past cases.

#### Chapter 18: Procedural Memory Schema

Status: complete on the active branch. Seven unverified human-authored
playbooks are seeded, while controller preference is restricted to strategies
supported by verified run outcomes. Successful and failed actions update the
observed rate idempotently.

Tasks:

1. Add strategy records: name, problem types, preconditions, steps, success rate.
2. Seed initial strategies: solve-by-substitution, verify-boundaries, reproduce-bug, search-official-docs, compare-baselines, decompose-plan, ask-clarifying-question.
3. Add strategy retrieval by problem type.
4. Add update function for success/failure.
5. Add tests.

Done when:

- Planner can ask for known strategies for a problem type.

#### Chapter 19: Knowledge Base Seed Data

Status: complete on the active branch. Five governed source documents and a
20-query cross-domain retrieval proof are available through `make memory-seed`
and `make memory-proof`.

Tasks:

1. Create `docs/knowledge/math_reasoning.md`.
2. Create `docs/knowledge/software_debugging.md`.
3. Create `docs/knowledge/technical_research.md`.
4. Create `docs/knowledge/data_analysis.md`.
5. Create `docs/knowledge/problem_solving_playbooks.md`.
6. Ingest seed docs into semantic memory.
7. Verify retrieval for 20 sample queries.

Done when:

- Retrieval returns useful domain knowledge for core use cases.

#### Chapter 20: Memory API

Status: complete on the active branch. Read-only semantic, episodic,
procedural, and bounded-context inspection endpoints expose provenance and
quality fields and exclude stale, weak, or irrelevant retrievals.

Tasks:

1. Create internal memory service methods.
2. Add API endpoints for development inspection.
3. Add memory search endpoint with filters.
4. Add source display fields for frontend.
5. Limit prompt injection to the top 3 most relevant memories by default.
6. Add tests that irrelevant or stale memories do not pollute reasoning context.

Done when:

- Developer can inspect semantic, episodic, and procedural memory.
- Memory retrieval is useful without flooding prompts.

### Phase 4: Knowledge Gap Detection

#### Chapter 21: Gap Detection Prompt

Tasks:

1. Write prompt that compares structured problem to knowns, constraints, and available memory.
2. Require each gap to explain why it matters.
3. Require suggested source/tool for each gap.
4. Add priority scoring.
5. Add examples where no external research is needed.

Done when:

- Prompt distinguishes missing data from optional curiosity.

#### Chapter 22: Available Data Source Registry

Status: complete on the active branch. See
`docs/03_implementation/Chapter_22_26_Knowledge_Acquisition.md`.

Tasks:

1. Define generic data source metadata: local files, documents, web search, APIs, databases, code repositories, metrics, calculators, and code execution.
2. Add schemas for mock data sources.
3. Add capability descriptions.
4. Add permission tags.
5. Add tests for source lookup.

Done when:

- Gap detector knows what data sources exist.

#### Chapter 23: Knowledge Gap Detector Engine

Tasks:

1. Implement memory lookup for relevant facts, cases, and strategies.
2. Implement LLM-based gap detection.
3. Merge duplicate gaps.
4. Rank by priority.
5. Store gaps in state and database.

Done when:

- Core benchmark scenarios produce actionable gaps such as missing facts, missing constraints, missing dataset, missing code context, missing source, or missing user clarification.

#### Chapter 24: Gap Quality Evaluation

Tasks:

1. Create 30 benchmark inputs with expected gaps.
2. Add scoring script: precision, recall, useless-gap rate.
3. Run evaluation.
4. Tune prompt and thresholds.
5. Document failure modes.

Done when:

- Gap detector reaches at least 80% useful-gap precision on local benchmark.

#### Chapter 25: Gap-to-Action Mapping

Tasks:

1. Map gap types to research or execution actions.
2. Examples: historical baseline -> SQL tool; public outage -> web search; similar incident -> episodic memory.
3. Add routing metadata to gaps.
4. Add tests.

Done when:

- Every high-priority gap has a next action.

### Phase 5: Research and Evidence

#### Chapter 26: Research Engine Interface

Status: complete on the active branch. The production Brave adapter is
transport-tested; live-provider verification awaits a configured search key.
See `docs/03_implementation/Chapter_22_26_Knowledge_Acquisition.md`.

Tasks:

1. Define search provider interface.
2. Add fake provider for tests.
3. Add real Tavily/Brave/Bing provider behind feature flag.
4. Normalize result schema.
5. Add rate limit and timeout.
6. Add per-session `research_budget` with max query count and max external fetch count.

Done when:

- Search can run safely and return normalized evidence candidates.
- Research stops gracefully when budget is exhausted.

#### Chapter 27: Query Formulation

Tasks:

1. Convert knowledge gaps into search queries.
2. Add domain-specific query templates.
3. Prefer official/reputable sources.
4. Limit query count per session.
5. Retry once with a rewritten query when top results are irrelevant.
6. Log query, gap id, source type, and result quality.
7. Add tests for query quality.

Done when:

- Queries are specific, bounded, and tied to gaps.

#### Chapter 28: Document Extraction

Tasks:

1. Fetch search results.
2. Extract title, URL, snippet, text where allowed.
3. Remove boilerplate.
4. Store raw candidates in evidence staging.
5. Add source attribution.
6. Deduplicate near-identical sources and keep the strongest source.
7. Chunk long pages and keep only relevant passages with source offsets when available.

Done when:

- Research results are saved with enough source metadata to audit.

#### Chapter 29: Evidence Evaluation Prompt

Status: complete on the active branch. See
`docs/03_implementation/Chapter_29_Evidence_Evaluation.md`.

Tasks:

1. Write prompt to score relevance, reliability, recency, and contradiction risk.
2. Require extracted claim in structured form.
3. Require "supports", "contradicts", or "background".
4. Add examples.
5. Add tests with fake evidence.

Done when:

- Evaluator separates useful evidence from noise.

#### Chapter 30: Evidence Evaluation Engine

Status: complete on the active branch. Candidate evaluation, canonical-state
integration, durable evidence rehydration, current-session contradiction
checks, and governed semantic-memory cross-checks are implemented. Episodic
memory remains case context rather than being misrepresented as factual
evidence.

Tasks:

1. Implement evaluator.
2. Cross-check evidence against existing memory.
3. Reject low-reliability evidence unless marked as weak signal.
4. Store evaluated evidence.
5. Feed validated evidence back into state.

Done when:

- Research loop returns validated evidence, not raw web clutter.

### Phase 6: Execution Tools

#### Chapter 31: Tool Registry

Status: in progress. The cognitive capability registry supplies allowlisted
discovery, risk metadata, execution boundaries, and durable call traces. Tool
description plus explicit input/output schema metadata remain to complete the
chapter contract.

Tasks:

1. Define base tool interface.
2. Register tools by name, description, input schema, output schema, risk level.
3. Add allowlist.
4. Add tool call persistence.
5. Add tests.

Done when:

- Executor can discover tools by capability.

#### Chapter 32: Mixed Benchmark Artifacts

Tasks:

1. Create mixed benchmark artifacts for the core product.
2. Include mixed benchmark data: numeric tables, log snippets, small code projects, research snippets, ambiguous prompts, and misleading evidence.
3. Add seed script for local benchmark fixtures.
4. Add ground-truth labels, expected clarifying questions, expected tools, and expected verification checks.
5. Document artifact schemas for tables, code, documents, logs, and problem statements.

Done when:

- Product can be tested across categories without real sensitive data.

#### Chapter 33: Safe Code Execution and Test Runner

Status: complete for bounded Python and assertion-based tests. See
`docs/03_implementation/Chapter_33_Safe_Code_Execution.md`.

Tasks:

1. Implement a sandboxed code execution tool for small Python programs and generated solutions.
2. Add CPU, memory, wall-clock, file-system, and network restrictions.
3. Add test runner support for sample tests, generated tests, and brute-force cross-checks for small inputs.
4. Capture stdout, stderr, exit code, runtime, and structured test results.
5. Add adversarial sandbox tests for timeout, infinite loop, file access, and blocked network access.

Done when:

- PolyaBrain can safely execute and verify generated code for algorithmic and debugging problems.

#### Chapter 34: Table, File, and Query Tools

Status: complete on the active branch. Read-only bounded CSV/JSON loading,
exact numeric distributions, change/anomaly summaries, configurable grouping,
and authorizer-protected in-memory SQL-style queries are implemented.

Tasks:

1. Implement read-only CSV/JSON/table loading.
2. Support generic metrics: rate, count, average, distribution, baseline, anomaly score, top contributors.
3. Support grouping by configurable dimensions from the input dataset.
4. Add safe SQL-style querying over local benchmark tables.
5. Add tests for malformed files, missing columns, large files, and correct aggregation.

Done when:

- Tool can answer "what changed, where, and when?"

#### Chapter 35: Math, Logic, and Statistical Analysis Tools

Status: in progress. Exact arithmetic, percent change, distributions, standard
deviation, anomaly counts, grouped contributors, and approximate controlled
effect intervals are implemented. Symbolic algebra, derivatives, unit
conversion, confidence-interval variants, and logic satisfiability remain.

Tasks:

1. Implement calculator and symbolic helpers for algebra, equations, derivatives, constraints, and unit conversions.
2. Implement statistical helpers: percent change, z-score, confidence intervals, anomaly baseline, and top contributors.
3. Implement simple logic helpers for satisfiability-style constraint checks where practical.
4. Add tests with known math, logic, and data-analysis outputs.
5. Store outputs as structured evidence with tool provenance.

Done when:

- PolyaBrain can verify numerical, symbolic, and statistical claims without relying only on an LLM.

#### Chapter 36: Web, API, and Document Research Tools

Tasks:

1. Add web/search provider interface with source metadata, rate limits, and domain allow/block controls.
2. Add document ingestion for local Markdown, text, PDF-extracted text, and HTML snippets.
3. Normalize retrieved facts, snippets, URLs, timestamps, and source types.
4. Cache repeated search and extraction results in Redis with a short TTL.
5. Add tests for stale sources, contradictory sources, unavailable pages, and prompt-injection text in sources.
6. Add research outputs to the evidence evaluator.

Done when:

- System can gather external or document-based information while preserving source boundaries.

#### Chapter 37: Repository, Log, and Event Tools

Tasks:

1. Add local code-repository reader for benchmark projects with file allowlists and size limits.
2. Add search over files, symbols, errors, stack traces, and small logs.
3. Add synthetic event/change log tool for debugging, data-analysis, and incident-style problems.
4. Add tests for missing files, large repositories, path traversal, and irrelevant logs.
5. Format repository/log findings as evidence.

Done when:

- System can inspect small codebases, logs, and event histories as part of problem solving.

#### Chapter 38: Tool Result Verification Basics

Tasks:

1. Validate tool outputs against schema.
2. Detect empty, stale, or partial results.
3. Add retry for transient errors.
4. Add tool error classification.
5. Add tests.

Done when:

- Tool failures become actionable feedback, not silent bad evidence.

### Phase 7: Reasoning and Planning

#### Chapter 39: Hypothesis Prompt

Tasks:

1. Write prompt to generate hypotheses from structured problem, gaps, memory, and evidence.
2. Require mechanism, expected signals, required checks, and confidence.
3. Require a divergent pass that produces meaningfully different hypotheses before any ranking.
4. Require at least one alternative hypothesis.
5. Require "what would falsify this?"
6. Require analogical transfer candidates when memory contains structurally similar cases.
7. Add examples.

Done when:

- Hypotheses are testable, not generic.
- The prompt avoids premature convergence and produces alternatives that can be verified or rejected.

#### Chapter 40: Hypothesis Engine

Tasks:

1. Implement hypothesis generation.
2. Deduplicate hypotheses.
3. Link evidence for/against.
4. Run convergent filtering after divergent generation.
5. Rank hypotheses.
6. Store hypothesis origin, falsification criteria, analogical sources, and selection rationale.
7. Store to database.

Done when:

- Investigation-style inputs produce ranked causes with expected checks.
- Ranked hypotheses show why one candidate survived over plausible alternatives.

#### Chapter 41: Plan Schema and Planner Prompt

Tasks:

1. Define plan DAG schema.
2. Write prompt that turns hypotheses into executable tasks.
3. Require dependencies and tool selection.
4. Require expected output per task.
5. Add examples.

Done when:

- Planner emits a valid DAG.

#### Chapter 42: Planner Engine

Tasks:

1. Implement plan generation.
2. Validate DAG: no cycles, all dependencies exist, tools allowed.
3. Add fallback rule-based plans for core use cases.
4. Store plan tasks.
5. Add tests.

Done when:

- Planner can create executable plans for synthetic scenarios.

#### Chapter 43: Plan Review Before Execution

Tasks:

1. Add risk assessment for each task.
2. Auto-execute only read-only low-risk tasks.
3. Require human approval for medium/high-risk tasks.
4. Add local approval flag for development.
5. Add tests.

Done when:

- The product cannot accidentally perform unsafe actions.

#### Chapter 44: Execution Engine

Tasks:

1. Execute DAG tasks in dependency order.
2. Run independent read-only tasks in parallel.
3. Store each tool call and output.
4. Feed outputs into evidence store.
5. Add failure routing.

Done when:

- A plan can run through tools and produce structured results.

#### Chapter 45: First Mixed End-to-End Polya Runs

Tasks:

1. Run one synthetic mixed-domain case from each category: math, research, debugging, data analysis, planning, and ambiguous input.
2. Parse problem.
3. Detect gaps.
4. Generate hypotheses.
5. Execute the relevant tools: code runner, calculator, table query, research, repository/log search, or clarifying-question flow.
6. Save evidence and trace.
7. Document failures.

Done when:

- One end-to-end run per core category completes, even if final answers are rough.

### Phase 8: Verification

#### Chapter 46: Verification Strategy Design

Tasks:

1. Define verification types: constraint, numerical, causal, source, contradiction, completeness.
2. Map each hypothesis type to required checks.
3. Define verification checklist templates by mode: technical research, debugging/root-cause analysis, architecture tradeoff, data analysis, ambiguous input, and creative synthesis.
4. Define confidence scoring formula.
5. Define failure routes, including insufficient evidence, ask user, gather more evidence, reframe, replan, retry execution, final report, reflection, and stop safely.
6. Document in `docs/verification.md`.

Done when:

- Verification is explicit, mode-specific, and not just "ask the LLM if correct."
- Verification can stop the loop without forcing a confident conclusion.

#### Chapter 47: Numeric Verification

Tasks:

1. Implement checks for percentage changes and baselines.
2. Check segment contribution sums.
3. Check time-window alignment.
4. Add tests with known data.
5. Add reports to verification output.

Done when:

- Claims like "metric rose 35%", "test X fails because of Y", or "source A supports claim B" are validated against evidence.

#### Chapter 48: Causal Plausibility Verification

Tasks:

1. Check whether proposed cause precedes effect.
2. Check whether affected segment matches cause.
3. Check whether unaffected controls behave differently.
4. Add tests.
5. Add confidence adjustment.

Done when:

- System rejects causes that do not explain the observed pattern.

#### Chapter 49: Contradiction Search

Tasks:

1. Search evidence against top hypothesis.
2. Generate expected counter-signals.
3. Run tool checks for those counter-signals.
4. Store evidence against.
5. Add tests.

Done when:

- Verification tries to disprove the answer before accepting it.

#### Chapter 50: Verification Engine Integration

Tasks:

1. Implement verification engine node.
2. Route passed cases to reflection.
3. Route information failure to gap/research.
4. Route strategic failure to hypothesis/planner.
5. Route execution failure to executor retry.

Done when:

- Failed verification causes useful replanning.

#### Chapter 51: Replanning Loop

Tasks:

1. Implement max 3 iterations.
2. Add failure context into subsequent planning.
3. Prevent repeating same failed plan.
4. Track confidence over iterations.
5. Add tests with a designed false hypothesis.

Done when:

- System improves after a failed first hypothesis.

#### Chapter 52: Final Answer Composer

Tasks:

1. Write structured report prompt.
2. Include conclusion, confidence, evidence, checks, rejected hypotheses, open questions, recommended action.
3. Ensure unsupported claims are omitted or flagged.
4. Add Markdown output.
5. Add tests for required sections.

Done when:

- Final answer is readable and auditable.

### Phase 9: Reflection and Learning

#### Chapter 53: Reflection Prompt

Tasks:

1. Write prompt to analyze full trace.
2. Extract what worked, what failed, reusable strategy, memory updates.
3. Require no new unsupported facts.
4. Add examples.
5. Add tests.

Done when:

- Reflection produces useful lessons, not generic self-praise.

#### Chapter 54: Reflection Engine

Tasks:

1. Implement reflection node.
2. Persist case summary to episodic memory.
3. Persist validated facts to semantic memory.
4. Update strategy success/failure.
5. Add tests.

Done when:

- Every completed session improves future retrieval.

#### Chapter 55: Memory Conflict Handling

Tasks:

1. Detect when new facts conflict with existing memory.
2. Mark older memory as superseded or disputed.
3. Add manual review flag.
4. Add tests.
5. Document conflict policy.

Done when:

- Memory does not blindly accumulate contradictions.

#### Chapter 56: Strategy Scoring

Tasks:

1. Update procedural strategies based on verification outcomes.
2. Track usage count and success rate.
3. Add decay for stale strategies.
4. Use strategy scores in planning context.
5. Add tests.

Done when:

- Successful problem-solving patterns become more likely in future runs.

#### Chapter 57: Evaluation Harness

Tasks:

1. Create `evals/` runner.
2. Add 30 synthetic cases with ground truth across math, logic, research, debugging, algorithmic coding, data analysis, planning, ambiguous, adversarial, and creative synthesis categories.
3. Score outcome correctness, problem framing quality, approach selection quality, evidence quality, hypothesis diversity, analogical transfer quality, reframe quality, mode-specific verification checklist completeness, correct clarification behavior, latency, and cost.
4. Add baseline simple LLM answer for comparison.
5. Add ablation runs for no-gap-detector, no-verifier, and no-memory variants.
6. Output report as JSON and Markdown.

Done when:

- Product quality can be measured repeatedly.

#### Chapter 58: First Evaluation Run

Tasks:

1. Run all 30 cases.
2. Record pass/fail.
3. Identify top 10 failure modes.
4. Create backlog items.
5. Tune only obvious prompt/schema defects.

Done when:

- There is a truthful baseline score.

#### Chapter 59: Regression Suite

Tasks:

1. Convert solved/fixed failures into regression tests.
2. Add CI smoke eval on small case subset.
3. Add nightly/full eval command.
4. Track metrics over time.
5. Document how to add new cases.

Done when:

- Improvements cannot silently break old cases.

#### Chapter 60: MVP Alpha Gate

Tasks:

1. Review architecture, traces, evaluation, and product UX.
2. Confirm all nine logical engines exist.
3. Confirm at least one end-to-end case succeeds with verification in math, research, debugging, data analysis, and planning.
4. Confirm critical safety controls exist.
5. Confirm creative synthesis cases show divergent candidates, convergent filtering, and verification of the selected path.
6. Write Alpha Gate report.

Done when:

- PolyaBrain is a rough but real alpha, not just a set of modules.

### Phase 10: Frontend Product Experience

#### Chapter 61: Frontend Bootstrap

Tasks:

1. Create Next.js app.
2. Install Tailwind, shadcn/ui, lucide-react, TanStack Query.
3. Add app shell layout.
4. Add API client.
5. Add environment config.

Done when:

- Frontend runs and can call backend health endpoint.

#### Chapter 62: Problem Input Screen

Tasks:

1. Build textarea for user problem.
2. Add mode selector: Investigate, Compare, Review.
3. Add optional structured fields: time window, metric, entity.
4. Add submit flow.
5. Add validation and loading states.

Done when:

- User can submit a problem from the UI.

#### Chapter 63: Live Trace Screen

Tasks:

1. Build pipeline visualization: Understand, Gaps, Research, Hypotheses, Execute, Verify, Reflect.
2. Add event stream from backend.
3. Show current step and duration.
4. Show failures/retries clearly.
5. Add tests for trace rendering.

Done when:

- User can watch PolyaBrain work in real time.

#### Chapter 64: Evidence Panel

Tasks:

1. Show evidence items with source, reliability, relevance, and claim.
2. Separate evidence for and against.
3. Add filtering by source type.
4. Add copy/share link.
5. Add empty states.

Done when:

- Trust is grounded in visible evidence.

#### Chapter 65: Hypothesis Panel

Tasks:

1. Show ranked hypotheses.
2. Show expected signals and checks.
3. Show status: pending, supported, refuted, verified.
4. Show confidence changes.
5. Add compact and expanded views.

Done when:

- User can see how the system chooses and rejects explanations.

#### Chapter 66: Final Report Screen

Tasks:

1. Render final answer sections.
2. Show confidence and verification status.
3. Show open questions and recommended next action.
4. Add export to Markdown.
5. Add print-friendly layout.

Done when:

- Output is useful as an expert problem-solving note.

#### Chapter 67: Session History

Tasks:

1. Add list of past sessions.
2. Add status, date, confidence, problem summary.
3. Add search/filter.
4. Add session detail page.
5. Add tests.

Done when:

- Users can return to previous problem-solving sessions.

#### Chapter 68: Human Feedback

Tasks:

1. Add feedback buttons: useful, wrong, incomplete, unsafe.
2. Add correction field.
3. Store feedback linked to session.
4. Use feedback in reflection/manual review queue.
5. Add tests.

Done when:

- Human corrections become product data.

#### Chapter 69: UX Polish

Tasks:

1. Review responsive layout.
2. Fix loading, error, empty, and long-text states.
3. Add accessible labels.
4. Add keyboard navigation for main flows.
5. Run visual QA.

Done when:

- UI feels like a real internal tool, not a demo page.

#### Chapter 70: Frontend Integration Gate

Tasks:

1. Run three end-to-end sessions from UI.
2. Verify trace, evidence, hypotheses, report, and history.
3. Fix blocking UX bugs.
4. Record short demo script.
5. Update README with UI instructions.

Done when:

- Non-developer can run the alpha locally.

### Phase 11: Security, Governance, and Observability

#### Chapter 71: PII Masking

Tasks:

1. Define sensitive fields for generic user data: credentials, tokens, personal data, proprietary data, financial data, health data, and private source code.
2. Implement masking before LLM calls.
3. Add audit record showing masked/unmasked boundaries.
4. Add tests.
5. Add docs.

Done when:

- Sensitive user data cannot accidentally enter prompts.

#### Chapter 72: Tool Permission Model

Tasks:

1. Add user/project permissions.
2. Add per-tool risk level.
3. Enforce allowlist.
4. Add approval requirement for non-read-only tools.
5. Add tests.

Done when:

- Tool access is controlled and auditable.

#### Chapter 73: Authentication

Tasks:

1. Add simple auth for MVP.
2. Protect API routes.
3. Add user identity to sessions and tool calls.
4. Add tests.
5. Document local dev bypass.

Done when:

- Product is not an open unauthenticated agent endpoint.

#### Chapter 74: Audit Logging

Tasks:

1. Persist all external calls, tool calls, prompts metadata, response metadata, approvals.
2. Exclude raw secrets and PII.
3. Add audit export endpoint.
4. Add tests.
5. Document retention policy.

Done when:

- A problem-solving session can be audited after the fact.

#### Chapter 75: Observability Baseline

Tasks:

1. Add OpenTelemetry traces.
2. Track engine durations, token usage, cost, tool latency, route decisions.
3. Add Prometheus metrics endpoint.
4. Add local Grafana dashboard.
5. Add alerts for errors and high cost.

Done when:

- You can see where time and money go per session.

#### Chapter 76: Prompt Injection Controls

Tasks:

1. Add content boundary rules for retrieved documents.
2. Ensure web/document text cannot override system instructions.
3. Add detection for suspicious instructions in sources.
4. Add tests with malicious documents.
5. Document policy.

Done when:

- Retrieved text is evidence, not an instruction channel.

#### Chapter 77: Cost Controls

Tasks:

1. Add per-session token budget.
2. Add per-day budget.
3. Add per-session research/search budget.
4. Add semantic cache for repeated retrieval/summarization.
5. Add cost display in trace.
6. Add warning threshold and hard-stop threshold for expensive sessions.
7. Add tests.

Done when:

- The product fails gracefully before runaway spending.

#### Chapter 78: Failure Mode Playbook

Tasks:

1. Document common failures and what the system should do.
2. Add user-facing messages for unavailable data, low confidence, tool failure, and verification failure.
3. Add support/debug instructions.
4. Add tests for failure responses.
5. Add frontend error states.

Done when:

- Failures look professional and honest.

#### Chapter 79: Security Review

Tasks:

1. Review auth, masking, tool permissions, audit logs, dependencies.
2. Run dependency scanner.
3. Run basic API abuse tests.
4. Fix critical issues.
5. Write security review notes.

Done when:

- No obvious MVP security holes remain.

#### Chapter 80: Beta Readiness Gate

Tasks:

1. Run evaluation suite.
2. Run security checklist.
3. Run UI end-to-end tests.
4. Confirm observability dashboards.
5. Decide beta blockers.

Done when:

- Product is ready for trusted internal expert reviewers.

### Phase 12: General Problem Depth and Product Usefulness

#### Chapter 81: Expand General Problem Benchmark Library

Tasks:

1. Add 50 synthetic cases.
2. Cover math, logic, technical research, debugging, data analysis, planning, scientific reasoning, ambiguous problems, and misleading evidence.
3. Add ground truth.
4. Add expected evidence.
5. Add to evaluation harness.

Done when:

- Evaluation reflects real problem variety.

#### Chapter 82: General Problem-Solving Playbook Memory

Tasks:

1. Write playbooks for each scenario type.
2. Ingest into procedural memory.
3. Link playbooks to strategy records.
4. Add retrieval tests.
5. Update planner context.

Done when:

- Plans look like disciplined Polya-style workflows across problem categories.

#### Chapter 83: Segment Analysis Upgrade

Tasks:

1. Add top-contributor decomposition.
2. Add before/after segment deltas.
3. Add control group comparison.
4. Add output charts data.
5. Add tests.

Done when:

- PolyaBrain can say not just "a metric changed", but which slice, cause, or assumption explains it.

#### Chapter 84: Timeline Reconstruction

Tasks:

1. Build evidence timeline from events, changes, metric shifts, source updates, and tool outputs.
2. Sort by time and confidence.
3. Add timeline to final report.
4. Add frontend timeline view.
5. Add tests.

Done when:

- Root-cause reasoning is time-aware.

#### Chapter 85: Recommended Action Generator

Tasks:

1. Generate recommended next actions with risk labels.
2. Separate "investigate", "mitigate", "monitor", "do not do".
3. Require evidence link for each recommendation.
4. Add tests.
5. Add report section.

Done when:

- Output helps a user take the next practical step.

#### Chapter 86: Human Review Mode

Tasks:

1. Let user provide their own hypothesis.
2. Run evidence gathering and verification against it.
3. Return support/refutation report.
4. Add UI mode.
5. Add tests.

Done when:

- Product can augment human experts, not just operate from scratch.

#### Chapter 87: Compare Mode

Tasks:

1. Implement period-over-period comparison.
2. Add metric selection.
3. Add baseline window selection.
4. Generate summary and anomalies.
5. Add UI support.

Done when:

- Users can ask "what changed?" without writing SQL.

#### Chapter 88: Report Quality Rubric

Tasks:

1. Define rubric: correctness, evidence, completeness, actionability, clarity, calibrated confidence.
2. Add LLM-as-judge only as secondary evaluator.
3. Add human review template.
4. Score previous sessions.
5. Track rubric over time.

Done when:

- Quality is measurable beyond pass/fail.

#### Chapter 89: Improve Low-Scoring Cases

Tasks:

1. Pick the 10 worst cases.
2. Inspect traces.
3. Fix prompts, tools, data, or routes.
4. Add regressions.
5. Re-run eval.

Done when:

- Quality improves on the exact failures that matter.

#### Chapter 90: General Problem MVP Gate

Tasks:

1. Run 80+ scenario eval.
2. Target: 70%+ correct or usefully verified outcome on synthetic cases.
3. Target: 90%+ reports include required evidence/check sections.
4. Target: 80%+ creative synthesis cases include a useful alternative, analogy, or reframe that is explicitly accepted, rejected, or deferred with evidence.
5. Target: zero unsafe tool calls.
6. Write General Problem MVP report.

Done when:

- Product is genuinely useful on representative mixed-domain problem cases.

### Phase 13: Cloud and Pilot Preparation

#### Chapter 91: Deployment Architecture

Tasks:

1. Choose deployment target: ECS/Fargate for simplicity or EKS if needed.
2. Draw deployment diagram.
3. Define environments: dev, staging, prod.
4. Define secrets management.
5. Document rollback strategy.

Done when:

- Deployment plan is concrete and not overbuilt.

#### Chapter 92: Container Hardening

Tasks:

1. Build backend image.
2. Build frontend image.
3. Use non-root users.
4. Add health checks.
5. Add image scanning.

Done when:

- Containers are deployable and reasonably hardened.

#### Chapter 93: Terraform Baseline

Tasks:

1. Create infra modules for network, database, Redis, app service, secrets.
2. Add remote state decision.
3. Add staging workspace.
4. Add README.
5. Run plan.

Done when:

- Cloud infra can be created reproducibly.

#### Chapter 94: Staging Deployment

Tasks:

1. Deploy backend.
2. Deploy frontend.
3. Connect database and Redis.
4. Configure environment variables.
5. Run smoke tests.

Done when:

- Staging URL works end-to-end.

#### Chapter 95: Staging Observability

Tasks:

1. Connect logs.
2. Connect metrics.
3. Connect traces.
4. Add alerts.
5. Verify dashboard with test sessions.

Done when:

- Staging can be operated without SSH guessing.

#### Chapter 96: Backup and Restore

Tasks:

1. Enable database backups.
2. Test restore into scratch database.
3. Define retention.
4. Document restore runbook.
5. Add backup alert.

Done when:

- You know how to recover memory and sessions.

#### Chapter 97: Load Test

Tasks:

1. Create load test script.
2. Test 1, 5, 10 concurrent sessions.
3. Measure latency, cost, queue behavior.
4. Identify bottlenecks.
5. Add remediation backlog.

Done when:

- You understand realistic capacity and cost.

#### Chapter 98: Queue and Async Reliability

Tasks:

1. Add background task queue if synchronous requests are too brittle.
2. Persist run status.
3. Make runs resumable after backend restart.
4. Add tests.
5. Update UI polling/streaming.

Done when:

- Long problem-solving runs survive normal service restarts.

#### Chapter 99: Pilot Data Contract

Tasks:

1. Define exact data required from pilot user/company.
2. Define safe anonymized schema.
3. Define ingestion format.
4. Create sample CSV/SQL templates.
5. Document data handling rules.

Done when:

- A pilot partner knows exactly what to provide.

#### Chapter 100: Pilot Onboarding Docs

Tasks:

1. Write quickstart.
2. Write sample prompts.
3. Write interpretation guide.
4. Write limitations.
5. Write feedback instructions.

Done when:

- An expert reviewer can use beta without a live walkthrough.

### Phase 14: Beta Pilot

#### Chapter 101: Recruit Pilot Reviewers

Tasks:

1. Identify 3-5 expert reviewers across engineering, math, research, data analysis, and product/problem-solving.
2. Share scope and limitations.
3. Schedule sessions.
4. Prepare consent/data boundaries.
5. Prepare feedback rubric.

Done when:

- Real users are scheduled.

#### Chapter 102: Pilot Dry Run

Tasks:

1. Run all demo scenarios in staging.
2. Verify no broken flows.
3. Prepare fallback demo data.
4. Check dashboards.
5. Fix blockers.

Done when:

- Demo can survive ordinary chaos.

#### Chapter 103: Pilot Session 1

Tasks:

1. Observe user submitting a problem.
2. Record where they hesitate.
3. Collect report quality feedback.
4. Ask what they would do next.
5. Log issues.

Done when:

- First human feedback is captured.

#### Chapter 104: Pilot Session 2

Tasks:

1. Test a different scenario.
2. Compare PolyaBrain output to user's manual solution.
3. Collect trust concerns.
4. Record missing integrations.
5. Log issues.

Done when:

- You know whether output is operationally useful.

#### Chapter 105: Pilot Session 3

Tasks:

1. Test human review mode.
2. Let user provide a hypothesis.
3. Observe support/refute workflow.
4. Collect feedback.
5. Log issues.

Done when:

- Human-in-the-loop mode is validated or rejected.

#### Chapter 106: Pilot Findings Review

Tasks:

1. Cluster feedback.
2. Identify top product gaps.
3. Identify top trust gaps.
4. Identify must-fix bugs.
5. Update roadmap.

Done when:

- Feedback is converted into engineering work.

#### Chapter 107: Fix Trust Issues

Tasks:

1. Improve wording around confidence.
2. Make evidence/checks more visible.
3. Remove overconfident phrases.
4. Add "unknowns" section.
5. Re-test report readability.

Done when:

- Reports are more calibrated and less salesy.

#### Chapter 108: Fix Workflow Issues

Tasks:

1. Improve input fields.
2. Add suggested prompts.
3. Improve session history.
4. Improve export.
5. Re-test with local scenarios.

Done when:

- Common user friction is reduced.

#### Chapter 109: Fix Reasoning Issues

Tasks:

1. Inspect failed pilot traces.
2. Add missing tools or checks.
3. Improve gap detection.
4. Add regressions.
5. Re-run eval.

Done when:

- Pilot failures are no longer unexplained.

#### Chapter 110: Beta 2 Gate

Tasks:

1. Re-run eval.
2. Re-run smoke tests.
3. Re-run security checks.
4. Prepare updated demo.
5. Decide launch readiness.

Done when:

- Product is ready for broader private beta or needs clear fixes.

### Phase 15: Productization

#### Chapter 111: Multi-Tenant Readiness

Tasks:

1. Add organization/project model.
2. Scope sessions and memory by org.
3. Prevent cross-org retrieval.
4. Add tests.
5. Add migration.

Done when:

- Memory isolation is enforced.

#### Chapter 112: Admin Console

Tasks:

1. Add basic user list.
2. Add project settings.
3. Add data source status.
4. Add budget status.
5. Add audit export.

Done when:

- Pilot admin can manage core settings.

#### Chapter 113: Data Source Connectors v1

Tasks:

1. Add connector abstraction.
2. Implement CSV upload connector.
3. Implement Postgres read-only connector.
4. Add connection tests.
5. Add UI for connector health.

Done when:

- Product can use customer-like data without code changes.

#### Chapter 114: Data Ingestion Validation

Tasks:

1. Validate schema.
2. Detect missing columns.
3. Detect suspicious values.
4. Generate ingestion report.
5. Add tests.

Done when:

- Bad pilot data fails early with clear instructions.

#### Chapter 115: Report Export and Sharing

Tasks:

1. Export Markdown.
2. Export PDF or print view.
3. Add stable share link with access control.
4. Add copy-to-ticket format.
5. Add tests.

Done when:

- PolyaBrain output can enter real team workflows.

#### Chapter 116: Notification Hooks

Tasks:

1. Add webhook integration.
2. Add Slack-style payload format.
3. Notify when long run completes.
4. Notify when verification fails.
5. Add tests.

Done when:

- Users do not need to watch every long run.

#### Chapter 117: Pricing and Cost Model

Tasks:

1. Calculate cost per problem-solving session.
2. Break down LLM, search, DB, infra.
3. Define internal unit economics.
4. Add budget projection.
5. Document pricing hypotheses.

Done when:

- You know whether the product can make money.

#### Chapter 118: Reliability Runbook

Tasks:

1. Document service restart.
2. Document failed run recovery.
3. Document provider outage fallback.
4. Document data restore.
5. Document alert response.

Done when:

- The product can be operated by someone other than the builder.

#### Chapter 119: Product Website or Internal Landing Page

Tasks:

1. Write concise product positioning.
2. Add screenshots or demo GIF.
3. Add "request beta access" flow if external.
4. Add security/privacy statement.
5. Add docs links.

Done when:

- The product can be explained to a buyer or stakeholder.

#### Chapter 120: Private Beta Launch Gate

Tasks:

1. Final full eval.
2. Final security checklist.
3. Final cost check.
4. Final UX smoke test.
5. Publish beta release notes.

Done when:

- PolyaBrain Core Platform is in private beta with a validated mixed-domain benchmark suite.

## 8. Chapters 121-180: From Beta to Real Product

The first 120 chapters create a private beta of the PolyaBrain Core Platform with a mixed-domain benchmark suite. Chapters 121-180 make the core platform stronger, validate it on real tasks, and prepare the architecture for optional use-case packs without rewriting the core.

### Chapters 121-130: Real Task Corpus Integration

#### Chapter 121: Real Task Corpus Intake

Tasks:

1. Select a small real or realistic corpus across at least five categories: math, coding contest, debugging, research, and data analysis.
2. Remove secrets, personal data, proprietary identifiers, and any content that cannot be safely processed.
3. Store original task, sanitized task, expected answer, evidence requirements, and human reference notes.
4. Assign each task a category, difficulty, allowed tools, and risk level.
5. Add corpus metadata to `evals/realistic_corpus/README.md`.

Done when:

- A sanitized real-task corpus exists and can be used without leaking sensitive data.

#### Chapter 122: Corpus Schema Normalization

Tasks:

1. Map each corpus item into the canonical `ProblemSession` and `StructuredProblem` formats.
2. Define artifact adapters for code files, tables, logs, documents, and problem statements.
3. Add validation for required fields, missing answers, missing evidence, and unsupported artifact types.
4. Add import script for the corpus.
5. Add tests for valid, invalid, and partially specified corpus items.

Done when:

- Corpus items can be imported into the same system path as normal user sessions.

#### Chapter 123: Ingestion Validation and Quality Report

Tasks:

1. Run ingestion validation on all corpus items.
2. Produce a quality report with missing fields, ambiguous prompts, unsupported artifacts, and source-risk issues.
3. Fix schema mappings and obvious data-quality errors.
4. Mark tasks that require human clarification instead of forcing a fake answer.
5. Save the report to `evals/reports/real_task_ingestion.md`.

Done when:

- Every corpus task is either runnable or explicitly marked as blocked with a reason.

#### Chapter 124: Baseline Runs on Realistic Corpus

Tasks:

1. Run a simple baseline LLM answer on all runnable corpus items.
2. Run PolyaBrain with tools disabled.
3. Run PolyaBrain with tools enabled.
4. Compare correctness, evidence quality, verification quality, and cost across all three modes.
5. Store baseline metrics.

Done when:

- There is a measurable baseline showing where the Polya loop helps and where it fails.

#### Chapter 125: Shadow Problem-Solving Sessions

Tasks:

1. Run one real or realistic task from each major category through the full product UI.
2. Record trace quality, tool use, verification route, user-facing report quality, and failure points.
3. Confirm no unsafe tool action runs without approval.
4. Capture screenshots or screen recordings for review.
5. Log every issue into the backlog.

Done when:

- The private beta can solve or honestly fail real-style tasks end to end.

#### Chapter 126: Human Reference Comparison

Tasks:

1. Compare PolyaBrain's final reports to human reference solutions.
2. Score correctness, missing assumptions, invalid evidence, unnecessary steps, and useful insights.
3. Identify cases where PolyaBrain correctly asks a clarifying question instead of solving.
4. Tag each failure by failing engine: representation, gaps, research, evidence, planning, execution, verification, reflection, or UI.
5. Write comparison notes.

Done when:

- Failures are assigned to concrete system components instead of remaining vague.

#### Chapter 127: Connector and Artifact Fixes

Tasks:

1. Fix broken corpus adapters and ingestion edge cases.
2. Improve file, table, repository, and document handling based on Chapter 126 failures.
3. Add missing source metadata where evidence was weak.
4. Add regression tests for every fixed artifact issue.
5. Re-run the affected subset.

Done when:

- Realistic artifacts enter the system reliably and preserve provenance.

#### Chapter 128: Cross-Category Procedural Memory

Tasks:

1. Add procedural playbooks learned from realistic tasks.
2. Separate general strategies from domain-specific strategies.
3. Add examples: brute-force-then-optimize, reproduce-before-fix, search-official-source-first, compare-against-baseline, ask-before-assuming.
4. Link strategies to categories, preconditions, and verification checks.
5. Test strategy retrieval during planning.

Done when:

- The planner can retrieve reusable strategies across problem categories.

#### Chapter 129: Realistic Corpus Re-Run

Tasks:

1. Re-run the full realistic corpus after fixes.
2. Compare metrics against Chapter 124 baseline.
3. Identify improvements, regressions, and unchanged failures.
4. Add regressions to CI smoke eval where practical.
5. Update the quality dashboard.

Done when:

- Progress is quantified and regressions are visible.

#### Chapter 130: Real-Task Readiness Report

Tasks:

1. Summarize corpus size, category distribution, pass rate, failure modes, cost, latency, and safety issues.
2. Identify which categories are ready for pilot use and which are not.
3. List must-fix items before broader beta.
4. Update the roadmap based on evidence.
5. Publish `docs/real_task_readiness_report.md`.

Done when:

- The team knows exactly how close PolyaBrain is to useful real-world problem solving.

### Chapters 131-140: Accuracy and Reasoning Improvement

#### Chapter 131: Failure Taxonomy Review

Tasks:

1. Review every failed and low-quality run from the realistic corpus.
2. Group failures by engine, category, and root cause.
3. Identify top five systemic problems.
4. Assign each systemic problem to a fix strategy.
5. Create a measurable before/after target.

Done when:

- Accuracy work is focused on the highest-leverage failures.

#### Chapter 132: Knowledge Gap Detection Upgrade

Tasks:

1. Inspect cases where PolyaBrain answered with missing information.
2. Add gap examples for each category.
3. Improve gap ranking and "must ask user" detection.
4. Add tests for underspecified and misleading prompts.
5. Re-run affected eval cases.

Done when:

- PolyaBrain is better at saying "I need more information" at the right time.

#### Chapter 133: Hypothesis Ranking Upgrade

Tasks:

1. Inspect cases where the correct hypothesis was generated but ranked too low.
2. Add ranking features: evidence strength, constraint fit, simplicity, falsifiability, and past strategy success.
3. Tune hypothesis confidence calibration.
4. Add tests for competing hypotheses.
5. Re-run affected eval cases.

Done when:

- Better-supported hypotheses rise above plausible but weak explanations.

#### Chapter 134: Verification Coverage Upgrade

Tasks:

1. Map each benchmark category to required verification checks.
2. Add missing checks for code, math, sources, tables, and plans.
3. Ensure final reports show which checks passed and failed.
4. Add tests for false-positive verification.
5. Re-run affected eval cases.

Done when:

- PolyaBrain verifies process and outcome, not only final text.

#### Chapter 135: Algorithmic Problem-Solving Verifier

Tasks:

1. Add coding-contest verifier pipeline: parse examples, generate tests, run code, compare outputs.
2. Add brute-force oracle support for small input sizes when possible.
3. Add complexity estimate field to plans and final reports.
4. Add edge-case generation for boundaries, empty inputs, duplicates, and maximum constraints.
5. Add benchmark cases for LeetCode/HackerRank-style tasks.

Done when:

- Algorithmic problems can be solved, executed, tested, and rejected when wrong.

#### Chapter 136: Research and Source Quality Upgrade

Tasks:

1. Inspect research tasks with weak or stale evidence.
2. Prefer official documentation, standards, primary papers, and source repositories.
3. Add recency checks where currentness matters.
4. Add contradiction handling between sources.
5. Re-run technical research eval cases.

Done when:

- Research answers are source-grounded and currentness-aware.

#### Chapter 137: Report Clarity Upgrade

Tasks:

1. Review reports with expert users or internal reviewers.
2. Make conclusion, confidence, evidence, assumptions, checks, and open questions easier to scan.
3. Add category-specific report sections only when they clarify the result.
4. Remove overconfident language.
5. Add snapshot tests for report structure.

Done when:

- Reports are useful without requiring the user to inspect raw traces.

#### Chapter 138: Regression Expansion

Tasks:

1. Turn every fixed bug into a regression case.
2. Add category-balanced CI smoke eval.
3. Add nightly full eval configuration.
4. Store historical eval results.
5. Add a dashboard or Markdown trend report.

Done when:

- Quality improvements are protected by repeatable tests.

#### Chapter 139: Full Evaluation Re-Run

Tasks:

1. Run synthetic benchmark suite.
2. Run realistic corpus.
3. Run security and prompt-injection evals.
4. Compare against previous metrics.
5. Identify launch-blocking regressions.

Done when:

- There is a current, trustworthy quality score for the whole product.

#### Chapter 140: Accuracy Improvement Report

Tasks:

1. Publish before/after metrics by category.
2. Document remaining weaknesses and category-specific risks.
3. Identify next accuracy investments.
4. Update acceptance thresholds if evidence suggests they are too low or too high.
5. Share the report with pilot reviewers.

Done when:

- The roadmap is guided by measured reasoning quality.

### Chapters 141-150: Workflow Integrations

#### Chapter 141: Workflow Target Selection

Tasks:

1. Choose the first integration based on user workflow: Slack, Jira, Linear, GitHub, email, or internal ticketing.
2. Define the exact jobs: submit problem, receive report, export trace, notify completion.
3. Identify auth, permissions, rate limits, and audit requirements.
4. Write integration user stories.
5. Confirm what will not be built in v1.

Done when:

- The integration has a narrow, useful scope.

#### Chapter 142: Integration Contract Design

Tasks:

1. Define inbound event schema.
2. Define outbound report schema.
3. Define error, retry, and duplicate handling.
4. Add integration config model.
5. Add tests for contract validation.

Done when:

- The integration can be implemented without guessing payload shapes.

#### Chapter 143: Outbound Notification Implementation

Tasks:

1. Implement notification sender abstraction.
2. Add completion, failure, needs-input, and low-confidence notifications.
3. Add signed webhook support where needed.
4. Add retry and dead-letter handling.
5. Add tests.

Done when:

- Users can be notified when a long run changes state.

#### Chapter 144: Report Export to Workflow Tool

Tasks:

1. Add export format for ticket/comment/document destinations.
2. Include summary, evidence, verification, open questions, and trace link.
3. Preserve access control on trace links.
4. Add manual export button in UI.
5. Add tests.

Done when:

- PolyaBrain output can move into a team's existing work system.

#### Chapter 145: Inbound Problem Creation

Tasks:

1. Create API endpoint for trusted integrations to create sessions.
2. Map inbound title/body/files into problem statement and artifacts.
3. Support category hints without trusting them blindly.
4. Add abuse and payload-size protections.
5. Add tests.

Done when:

- External tools can start PolyaBrain sessions safely.

#### Chapter 146: Integration Auth and Audit

Tasks:

1. Add integration-specific credentials and secret rotation procedure.
2. Log every inbound and outbound integration event.
3. Add permission checks for session creation and report export.
4. Add admin UI for enabling/disabling integration.
5. Add tests.

Done when:

- Integrations are secure, auditable, and revocable.

#### Chapter 147: Staging Integration Tests

Tasks:

1. Deploy integration to staging.
2. Run happy-path workflow.
3. Run duplicate, retry, permission-denied, and malformed-payload tests.
4. Verify logs, metrics, and audit entries.
5. Fix blockers.

Done when:

- Integration behaves correctly under normal and failure conditions.

#### Chapter 148: Pilot Workflow Run

Tasks:

1. Ask a pilot reviewer to submit a real-style problem through the integration.
2. Observe time to submit, understand result, and export/share report.
3. Collect friction points.
4. Compare workflow against UI-only usage.
5. Log improvements.

Done when:

- The integration demonstrably reduces context switching.

#### Chapter 149: Integration Friction Fixes

Tasks:

1. Fix confusing messages, missing links, auth failures, and report formatting issues.
2. Improve notification wording.
3. Add integration-specific troubleshooting messages.
4. Re-test the pilot workflow.
5. Add regressions.

Done when:

- The first workflow integration is usable without hand-holding.

#### Chapter 150: Integration Documentation

Tasks:

1. Write setup guide.
2. Write admin guide.
3. Write user guide with examples.
4. Document limitations and troubleshooting.
5. Add integration to onboarding materials.

Done when:

- A new team can configure and use the integration.

### Chapters 151-160: Enterprise Hardening

#### Chapter 151: SSO/OIDC

Tasks:

1. Add OIDC login option.
2. Map identity provider claims to users and organizations.
3. Support local-dev auth separately.
4. Add logout and session expiry.
5. Add tests.

Done when:

- Enterprise users can authenticate through their identity provider.

#### Chapter 152: RBAC Improvements

Tasks:

1. Define roles: owner, admin, reviewer, user, read-only auditor.
2. Apply permissions to sessions, memory, tools, integrations, and exports.
3. Add permission tests.
4. Add UI visibility rules.
5. Document role behavior.

Done when:

- Users can only see and do what their role permits.

#### Chapter 153: Data Retention and Privacy Controls

Tasks:

1. Define retention settings for sessions, traces, evidence, memory, and uploaded artifacts.
2. Add retention job.
3. Add legal hold or "do not delete" flag if needed.
4. Add redaction path for sensitive content.
5. Add tests.

Done when:

- Stored data has a controlled lifecycle.

#### Chapter 154: Memory Export, Review, and Deletion

Tasks:

1. Add memory browser for semantic, episodic, and procedural entries.
2. Add export by project/org.
3. Add delete/suppress entry flow.
4. Add conflict/manual-review queue.
5. Add audit logging.

Done when:

- Users can inspect and govern what PolyaBrain remembers.

#### Chapter 155: Tenant Isolation and Secrets Review

Tasks:

1. Verify organization-level isolation in database queries and vector retrieval.
2. Add tests for cross-tenant memory leakage.
3. Review secret storage and rotation.
4. Verify integration credentials are tenant-scoped.
5. Fix isolation gaps.

Done when:

- One tenant cannot access another tenant's sessions, memory, tools, or secrets.

#### Chapter 156: Penetration Test Checklist

Tasks:

1. Test auth bypass, broken access control, prompt injection, tool injection, file path traversal, and SSRF-like fetch risks.
2. Test sandbox escape attempts for code execution.
3. Test malicious documents and repository files.
4. Record all findings with severity.
5. Create remediation tickets.

Done when:

- Security weaknesses are known and prioritized.

#### Chapter 157: High-Severity Remediation

Tasks:

1. Fix all critical and high-severity findings from Chapter 156.
2. Add regression tests for each fix.
3. Re-run the security checklist.
4. Document accepted risks.
5. Update runbooks.

Done when:

- No known critical or high-severity issue remains unaddressed.

#### Chapter 158: Security Whitepaper

Tasks:

1. Document architecture, auth, data isolation, prompt boundaries, tool permissions, sandboxing, logging, and retention.
2. Explain what data may be sent to model providers.
3. Document deployment assumptions.
4. Add diagrams.
5. Review for accuracy.

Done when:

- Security posture can be explained to a buyer, reviewer, or future teammate.

#### Chapter 159: Compliance Mapping

Tasks:

1. Map controls to general security expectations: access control, auditability, encryption, retention, data minimization, vendor handling.
2. Add optional mappings for sensitive domains where relevant.
3. Identify gaps that block regulated usage.
4. Create remediation plan.
5. Update product limitations.

Done when:

- Compliance-sensitive users can understand what is and is not ready.

#### Chapter 160: Enterprise Readiness Review

Tasks:

1. Review auth, RBAC, tenant isolation, data retention, audit logs, sandboxing, and integrations.
2. Run smoke tests in staging.
3. Review open risks.
4. Decide whether enterprise pilots are allowed.
5. Publish readiness checklist.

Done when:

- Enterprise readiness is explicit, not assumed.

### Chapters 161-170: Performance and Cost

#### Chapter 161: Token Usage Profiling

Tasks:

1. Profile token usage by engine, category, and model.
2. Identify largest prompts and repeated context.
3. Add token budget alerts to traces.
4. Create optimization backlog.
5. Save baseline cost report.

Done when:

- Token cost is visible and actionable.

#### Chapter 162: Retrieval and Tool Latency Profiling

Tasks:

1. Measure vector search, database, code execution, web research, and file parsing latency.
2. Identify p50, p95, and worst-case latencies.
3. Separate model latency from tool latency.
4. Add metrics dashboards.
5. Create optimization backlog.

Done when:

- Slow paths are known by component.

#### Chapter 163: Caching Layer

Tasks:

1. Add cache for document chunks, embeddings, source summaries, and repeated tool results where safe.
2. Define cache keys and invalidation rules.
3. Avoid caching sensitive tenant data across boundaries.
4. Add cache hit/miss metrics.
5. Add tests.

Done when:

- Repeated work is reduced without breaking correctness or privacy.

#### Chapter 164: LLM Call Reduction

Chapter 13-D implements the first product-critical slice. This later chapter
scales and profiles that mechanism across the mature platform rather than
introducing it for the first time.

Tasks:

1. Replace simple LLM decisions with deterministic logic where reliable.
2. Compress prompts with structured summaries.
3. Avoid sending irrelevant trace history.
4. Batch compatible classification/evaluation calls.
5. Re-run eval to ensure quality does not drop.

Done when:

- Cost decreases without degrading benchmark quality.

#### Chapter 165: Parallel Tool Execution

Tasks:

1. Identify independent plan tasks.
2. Execute safe read-only tasks concurrently.
3. Add concurrency limits per tenant and per tool.
4. Preserve deterministic trace ordering.
5. Add tests for failure and cancellation.

Done when:

- Long multi-tool sessions complete faster without race-condition confusion.

#### Chapter 166: Database and Vector Optimization

Tasks:

1. Analyze slow queries.
2. Add indexes for sessions, events, evidence, memory, and vector filters.
3. Tune chunk sizes and retrieval top-k.
4. Add pagination for heavy endpoints.
5. Re-run load tests.

Done when:

- Storage layer is not the primary bottleneck for beta traffic.

#### Chapter 167: Model Routing

Chapter 13-D establishes capability-kind and budget-aware routing in the early
cognitive runtime. This later chapter adds multi-model quality tiers and
production routing policy.

Tasks:

1. Classify engine calls by required reasoning strength.
2. Route simple extraction/classification to cheaper models where acceptable.
3. Keep high-stakes reasoning and verification on stronger models.
4. Add quality guardrail evals for model-routing changes.
5. Track cost and quality by model.

Done when:

- PolyaBrain uses expensive reasoning only where it earns its keep.

#### Chapter 168: Budget Enforcement

Chapter 13-D establishes hard per-run cognitive budgets. This later chapter
extends enforcement to user, organization, billing-period, and administrative
limits.

Tasks:

1. Add per-session, per-user, per-org, and per-day budget limits.
2. Define graceful degradation when budget is exceeded.
3. Show budget status in admin UI.
4. Add alerts.
5. Add tests.

Done when:

- Runaway cost is technically prevented.

#### Chapter 169: Load Test Target Traffic

Tasks:

1. Define beta traffic target.
2. Run load tests for UI, API, event streaming, tools, and background workers.
3. Test degraded providers and slow tools.
4. Record bottlenecks.
5. Fix launch-blocking performance issues.

Done when:

- The system survives expected beta load with acceptable latency.

#### Chapter 170: Performance and Cost Report

Tasks:

1. Summarize latency, throughput, cost per session, cache savings, and model-routing savings.
2. Compare against Chapter 161 baseline.
3. Document remaining bottlenecks.
4. Update infrastructure sizing.
5. Publish report.

Done when:

- Cost and performance are understood well enough for controlled launch.

### Chapters 171-180: Controlled Launch Preparation

#### Chapter 171: Launch Criteria

Tasks:

1. Define launch scope: audience, categories supported, categories excluded, and usage limits.
2. Define quality, security, cost, and uptime thresholds.
3. Define stop-launch conditions.
4. Create launch checklist.
5. Get explicit go/no-go criteria approved.

Done when:

- Launch has objective gates.

#### Chapter 172: Positioning and Messaging

Tasks:

1. Write product positioning around problem-solving intelligence, not chatbot behavior.
2. Explain how PolyaBrain handles unknowns, tools, verification, and reflection.
3. Define honest limitations.
4. Prepare short and long product descriptions.
5. Review wording for overclaiming.

Done when:

- Users understand what PolyaBrain is and is not.

#### Chapter 173: Demo Problem Suite

Tasks:

1. Prepare demo problems across math, coding contest, debugging, research, data analysis, planning, and ambiguous categories.
2. Ensure each demo has expected evidence and success criteria.
3. Add reset scripts for demo artifacts.
4. Practice demo flow.
5. Prepare backup demos.

Done when:

- The demo shows general problem solving, not one narrow trick.

#### Chapter 174: Case Study Preparation

Tasks:

1. Select one or two successful beta examples.
2. Redact sensitive details.
3. Show problem, Polya loop trace, verification, final answer, and user value.
4. Get permission if external data is involved.
5. Add case study to launch materials.

Done when:

- There is credible evidence that PolyaBrain solves useful problems.

#### Chapter 175: Documentation Finalization

Tasks:

1. Finalize user guide.
2. Finalize admin guide.
3. Finalize API docs.
4. Finalize security and data handling docs.
5. Finalize troubleshooting guide.

Done when:

- A new user can get started and recover from common issues.

#### Chapter 176: Onboarding Flow

Tasks:

1. Build first-run checklist.
2. Add sample problems.
3. Add explanation of traces, confidence, evidence, and verification.
4. Add guidance for giving feedback.
5. Test onboarding with a new reviewer.

Done when:

- A new user can understand the product without a live lecture.

#### Chapter 177: Launch Rehearsal

Tasks:

1. Run through launch checklist in staging.
2. Create accounts, run demos, export reports, test integrations, and review dashboards.
3. Simulate provider outage and failed run.
4. Verify rollback procedure.
5. Fix rehearsal blockers.

Done when:

- The team can launch, operate, and roll back calmly.

#### Chapter 178: Release Branch and Freeze

Tasks:

1. Create release branch.
2. Freeze non-critical feature work.
3. Run full CI, eval, security checks, and smoke tests.
4. Tag release candidate.
5. Prepare release notes.

Done when:

- The launch build is stable and traceable.

#### Chapter 179: Controlled Launch

Tasks:

1. Launch to controlled audience.
2. Monitor errors, cost, latency, and user sessions.
3. Keep support channel active.
4. Log every issue with severity.
5. Make only critical fixes.

Done when:

- Real users can use PolyaBrain under controlled monitoring.

#### Chapter 180: Launch Review and Next 90-Day Roadmap

Tasks:

1. Review launch metrics, user feedback, failures, costs, and security events.
2. Decide which benchmark categories need the most work.
3. Decide whether to build the first specialized use-case pack.
4. Define next 90-day roadmap with measurable outcomes.
5. Archive launch report.

Done when:

- The next phase is based on evidence from real usage.

## 9. Acceptance Metrics

Core platform alpha by Chapter 60:

- All nine logical engines exist.
- At least 30 evaluation cases run automatically.
- At least one full end-to-end case succeeds in each major category: math, research, debugging, data analysis, planning, and ambiguous input.
- At least 20 general reasoning smoke cases run through the same core loop.
- Every answer includes evidence, checks, confidence, and open questions.
- Open-ended creative synthesis cases show divergent candidates, convergent filtering, and verification of the selected path.
- No unsafe write tools exist.

General Problem MVP by Chapter 90:

- 100+ synthetic and curated scenarios across benchmark categories.
- 70%+ correct or usefully verified outcome on solvable cases.
- 90%+ correct clarification/escalation behavior on underspecified cases.
- 90%+ reports include required audit sections.
- 80%+ creative synthesis cases include a useful alternative, analogy, or reframe that is explicitly accepted, rejected, or deferred with evidence.
- Zero critical security issues.
- UI supports input, live trace, evidence, hypotheses, report, and history.
- Domain-specific schemas/tools/playbooks are isolated from core engine code.

Private beta by Chapter 120:

- Staging/cloud deployment stable.
- Auth, audit logging, PII masking, and cost controls enabled.
- At least 3 expert pilot sessions completed.
- Product output judged useful by at least 2 expert reviewers.
- Clear path to real data integration.
- Clear extension contract exists for adding optional domain use-case packs.

Real product by Chapter 180:

- One real or realistic mixed task corpus integrated.
- 80%+ correct or usefully verified outcome on representative validated cases.
- Median problem-solving session completes within practical pilot target.
- Cost per session is known and acceptable.
- Security and operations runbooks exist.
- Workflow export/integration exists.
- At least one optional specialized use-case pack has a design spec and seed evaluation set.

Internal operational metrics to track continuously:

| Metric | Why it matters |
| --- | --- |
| Outcome correctness | Shows whether PolyaBrain solves the task. |
| Verification catch rate | Shows whether the verifier catches false or unsupported answers. |
| Knowledge gap usefulness | Shows whether the system asks/searches for the right missing information. |
| Evidence quality | Shows whether conclusions are grounded in reliable sources. |
| Memory retrieval relevance | Shows whether memory helps instead of polluting context. |
| Clarification rate | Shows how often the system correctly asks instead of guessing. |
| Median and P95 latency | Shows whether the product feels usable. |
| Cost per session | Shows whether the business can work. |
| User usefulness rating | Shows whether expert users would reuse the output. |

## 10. Engineering Rules

1. Never add a new engine without a typed input/output contract.
2. Never allow final answers without verification status.
3. Never call external tools without audit logging.
4. Never send raw sensitive user data to an LLM.
5. Never let the graph loop forever.
6. Never store memory without source and confidence metadata.
7. Never optimize for demo magic over evaluation repeatability.
8. Never add a new use-case pack by changing core engine behavior; extend through tools, schemas, memory, playbooks, and evals.

## 11. What Makes It Cool

The "cool" factor should come from visible intelligence, not decoration:

- The user watches the Polya loop progress live.
- The system admits what it does not know.
- It gathers missing evidence.
- It proposes multiple hypotheses.
- It actively tries to disprove itself.
- It shows why one hypothesis survived.
- It remembers the problem-solving trace and improves next time.
- It exports a professional report an expert user can actually use.

That is the product magic: not a chatbot answer, but an auditable thinking workflow.

## 12. Adding Specialized Use-Case Packs

PolyaBrain should be tested on mixed problems from Chapter 1. Specialized use-case packs are optional product packaging and deeper domain integrations, not the foundation of the intelligence system. Add them only when they reuse the same core loop cleanly.

Good optional use-case packs are:

1. DevOps/SRE incident investigation.
2. Software bug root-cause analysis.
3. Algorithmic problem solving and coding contest assistant.
4. Compliance change impact analysis.
5. Scientific/technical research assistant.
6. Payment fraud detection and fraud operations.
7. Enterprise decision support.
8. Education/tutoring.

Each new use-case pack should reuse the same core engines and add only:

- New data connectors.
- New tools.
- New playbooks.
- New evaluation cases.
- New UI labels where necessary.

## 13. Final Implementation Principle

PolyaBrain is not valuable because it "uses AI." It is valuable if it can repeatedly convert ambiguity into verified action.

The implementation should therefore optimize for:

- explicit problem representation,
- high-quality gaps,
- testable hypotheses,
- reliable tools,
- strict verification,
- honest uncertainty,
- useful memory,
- and expert-grade reports.

Build that first. Scale comes later.
