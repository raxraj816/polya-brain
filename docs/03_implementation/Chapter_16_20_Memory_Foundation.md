# Chapters 16-20: Governed Memory Foundation

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

## Product Behavior

PolyaBrain now has three distinct long-term memory systems:

- Semantic memory stores sourced knowledge chunks with domain, reliability,
  freshness, tags, admission status, embedding provenance, and pgvector search.
- Episodic memory stores only completed runs with passing verification, a final
  answer, and reflection. Prior cases are suggestions for transfer, not facts.
- Procedural memory records action/capability outcomes only from completed,
  verified, reflected runs. Failed actions in an ultimately verified run lower
  the strategy's observed success rate. Replaying the same session is
  idempotent.

The controller can consult semantic memory before acquiring new information and
can prefer a procedure supported by at least one verified run. It must still
verify whether recalled knowledge or strategy transfers to the present case.

## Admission and Retrieval Rules

| Memory | Admission rule | Retrieval guard | Permitted use |
|---|---|---|---|
| Semantic | Evaluated source or explicit curated seed | source, reliability, freshness, domain/filter, and minimum similarity | Candidate evidence requiring current-case verification |
| Episodic | Completed + verification passed + reflection + final answer | structural similarity and optional problem/domain filters | Analogical case context with transfer limitations |
| Procedural | Seeded playbook or outcome observed inside a verified run | problem/gap match; controller preference requires verified success and at least 0.5 success rate | Candidate next action, never automatic proof |

Stale, weak, unadmitted, and irrelevant semantic chunks are excluded. Retrieval
is bounded to three semantic items and three episodes in reasoning context. New
research evidence is cross-checked against admitted semantic memory; an
unresolved contradiction prevents the knowledge gap from being marked solved.

## Local Embeddings

The local development provider is deterministic 1,536-dimensional feature
hashing. It needs no network, model training, or credential and makes database
and retrieval behavior reproducible. It is a replaceable provider boundary, not
a claim that feature hashing is the final production semantic model.

## Seed Knowledge and Procedures

Five source-visible knowledge documents cover mathematical reasoning, software
debugging, technical research, data analysis, and general problem-solving
playbooks. `make memory-seed` ingests them idempotently and `make memory-proof`
checks 20 queries across those categories.

Seven human-authored procedural playbooks are seeded with zero verified
successes. This is deliberate: they are inspectable starting hypotheses and do
not influence controller preference until a real verified outcome supports
them.

## Developer Inspection

- `GET /api/v1/memory/semantic`
- `GET /api/v1/memory/episodes`
- `GET /api/v1/memory/procedures`
- `GET /api/v1/memory/context`

Every semantic response includes its source and quality fields. Procedure
responses expose successes, failures, success rate, and contributing sessions.

## Verification

- Real Postgres/pgvector similarity retrieval excludes stale, weak, and
  irrelevant chunks.
- Unverified runs create neither episodes nor learned procedures.
- Verified learning is idempotent and records both successful and failed action
  outcomes.
- Similar episode retrieval is exercised across math, debugging, research,
  planning, and data analysis fixtures.
- The 20-query seed-corpus proof passes.
- Memory API routes are present in the generated OpenAPI schema.
