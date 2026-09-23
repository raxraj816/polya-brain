# Chapter 1 Start Here

Use this file as the practical implementation entrypoint.

## Read First

1. `../../PolyaBrain_Product_Implementation_Master_Plan.md`
2. `../00_vision/PolyaBrain_Final_Foundational_Design.md`
3. `../00_vision/Cognitive_Product_Doctrine.md`
4. `Product_Acceleration_Playbook.md`
5. `../01_architecture/MVP_Architecture_Decisions.md`
6. `../01_architecture/Core_Data_Contracts.md`
7. `../02_examples_and_benchmarks/Benchmark_Categories.md`

## Do Not Start With

- Archived fraud-focused reports.
- Archived older plans.
- Long-term research ideas that mention Kubernetes, Neo4j, fine-tuning, RL, or multi-agent debate.

Those are preserved for context, but they are not Chapter 1 implementation instructions.

## Binding Product Lock

```text
PolyaBrain is a product-first, initially cloud-hosted, model-agnostic Cognitive
Runtime that turns difficult objectives into verified outcomes by acquiring
knowledge on demand, using deterministic procedures whenever possible, invoking
bounded model reasoning when necessary, and learning reusable procedures from
verified work.
```

- **Build now:** PolyaBrain Investigator, the verified technical
  problem-solving workbench.
- **Build it through:** the domain-independent PolyaBrain Cognitive Runtime.
- **Deliver initially as:** a managed cloud product and API after local proof,
  with portable sovereign, private, and local boundaries.
- **Treat as replaceable:** LLMs, search, memory, tools, knowledge sources, and
  infrastructure providers.
- **Earn later:** PolyaBrain Intelligence OS through dependent applications,
  developers, and cross-domain proof.

The unit of value is a verified problem outcome, not a chat response. Optimize
for verified useful outcomes per unit of total cost and human attention.

## First Implementation Goal

Build the smallest complete PolyaBrain core loop:

Problem input -> representation -> constraints -> gaps -> evidence/tools -> hypotheses -> plan -> execution -> verification -> reflection -> report.

The first milestone is not a perfect engine. The first milestone is one traceable, verified, end-to-end run.

Before building the full platform shell, run the pre-platform proof harness for
the technical investigation wedge. The harness must produce local file artifacts
for trace, evidence, hypotheses, verification, report, and a direct LLM baseline
comparison. The production runtime CLI entrypoint is:

```bash
./polyabrain investigate "technical problem..."
```

The older template demonstration is available as `./polyabrain proof`; its
artifacts are not production-runtime outcomes. See
`Chapter_13L_Investigator_Runtime_Delivery.md` for current local usage and limits.

## First 10 Chapters

Follow the master plan exactly:

1. Product lock and repository foundation.
2. Architecture decisions and risk register.
3. Local development environment.
4. Database baseline.
5. Core Pydantic models.
6. LangGraph state object.
7. Engine interface contract.
8. Graph skeleton.
9. Event trace system.
10. API shell.

## Engineering Defaults

- Python/FastAPI backend.
- Pydantic v2 contracts.
- LangGraph orchestration.
- Postgres plus `pgvector`.
- Redis for cache and streaming run state.
- Next.js frontend.
- Docker Compose local development.
- Tests from the first engine contract.

## Chapter 1 Success

Chapter 1 is successful when the repository foundation is clear and every
builder can distinguish the initial product, enduring runtime, initial delivery,
eventual OS category, and replaceable model/tool layer without inference or
contradiction.
