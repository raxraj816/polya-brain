# Research Reading Guide

The research docs are useful context, not binding implementation instructions.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## How To Use Research Docs

Use research docs to understand:

- Why a Polya-style loop matters.
- Why verification matters.
- Why reflection and memory matter.
- What long-term architecture options exist.
- What benchmark families may be useful later.

Do not use research docs to override MVP implementation decisions.

## MVP Overrides

When research docs mention the following, treat them as future options:

- Kubernetes.
- Microservices per engine.
- Neo4j.
- Pinecone or Milvus.
- Fine-tuning.
- Reinforcement learning.
- Multi-agent debate.
- Full autonomous agents.
- Custom web-scale crawlers.
- Production-grade specialized domain packs.

The MVP starts simpler:

- Modular monolith.
- LangGraph state machine.
- FastAPI backend.
- Postgres with `pgvector`.
- Redis.
- Safe local tools.
- Mixed benchmark suite.

## Current Research Files

- `Concept_to_Code.md`: useful for research, verification, reflection, secure execution, and long-term product ideas.
- `Polya_Principles_to_Practice.md`: useful for domain-agnostic thinking, benchmarks, creative synthesis, and long-term multi-agent concepts.

## Practical Reading Order

1. Read the master plan first.
2. Read active vision docs.
3. Read MVP architecture decisions.
4. Read research docs only when a master-plan task needs deeper background.

## Rule

If a research document and the master plan disagree, follow the master plan.
