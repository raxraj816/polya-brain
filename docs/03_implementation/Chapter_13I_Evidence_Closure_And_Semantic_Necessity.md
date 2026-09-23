# Chapter 13-I: Evidence Closure and Semantic Necessity

Status: complete in the current working tree for the first exact-attestation
mechanism.

## Problem

The stable six-category Chapter 13-C run showed equal correctness but 2.19x
Polya token use. Every tool observation already stated the supported answer;
Polya nevertheless called a deliberator and a conclusion checker to restate it.
That violates the product doctrine to use deterministic cognition whenever the
procedure is known.

## Experimental Boundary

A registered deterministic tool may emit a trace-only attestation binding its
version, one exact evidence claim, provenance, every covered success criterion,
and the checks it performed. An allowlisted deterministic closure procedure may
reuse that result only after independently rechecking every binding against the
current state.

The attestation is not semantic magic. It is valid only when the producer owns
the full deterministic procedure. Search results, arbitrary documents, memory,
model output, and partially covered criteria continue through ordinary evidence
evaluation and semantic reasoning.

## Safety Invariants

- No task IDs, expected answer terms, or domain-specific benchmark solutions.
- Exact producer capability and version allowlist.
- Exact claim hash, excerpt identity, and source provenance.
- Exact success-criterion coverage; partial coverage fails closed.
- One admitted claim only in the first mechanism; ambiguity routes elsewhere.
- Present-case verification recomputes all bindings before any final answer.
- Zero model calls are a measured result, never an assumed label.

## Implemented

- A typed trace-only attestation binds producer capability/version, source
  type/URI, exact claim hash, current success criteria, and checks performed.
- Product composition supplies the exact trusted capability/version/source-type
  allowlist. Merely setting high evidence scores cannot create trust.
- The closure procedure requires exactly one admitted claim, exact
  claim/excerpt identity, maximum reliability and relevance, source provenance,
  and ordered equality with every current success criterion.
- Hypothesis construction creates a replayable plan and execution record. The
  verify pass independently rechecks the attestation and replay output before
  setting verification, final answer, and reflection.
- The controller ranks deterministic closure before semantic deliberation but
  retains the deliberator and conclusion checker as fallbacks. A failed closure
  attempt cannot repeat unchanged and does not block semantic recovery.
- The direct comparison receives the same attestation fields. Polya's advantage
  comes from executing the typed contract, not withholding information.

## Verification

Focused tests cover complete zero-call closure plus forged producer version,
changed claim, partial criterion coverage, multiple evidence claims, missing
provenance, untrusted source type, tampered replay output, semantic fallback,
and absence of an attestation.

Repeated same-model/same-tool live artifact:
`evals/chapter_13c/live_outcome_runs/2026-08-22/134337-16a8dce2/summary.json`

| Metric | Polya | Direct |
|---|---:|---:|
| Verified outcomes | 18/18 | 17/18 |
| Model tokens | 0 | 47,656 |
| Mean latency | 3.38 ms | 5,158 ms |
| Recovery trials passed | 3/3 | 3/3 |
| Unsupported forced conclusions | 0 | 0 |

The predeclared general Chapter 13-C gate remains false because the pass-rate
advantage is 5.56 points, below its 10-point threshold. This result supports a
narrow quality-adjusted compute win only for fully attested deterministic tool
results.

Full repository verification: 338 passed, 23 skipped (361 collected). Ruff
passes repository-wide, formatting passes across 156 affected Python files,
and strict mypy passes over 102 application source files.

## Bounded Claim

This mechanism proves that Polya can avoid semantic computation after a known
typed procedure while adding integrity, provenance, trust, and coverage replay.
It does not validate arbitrary search results or documents, infer semantic
coverage, or establish general problem-solving superiority. Broader evidence
still requires acquisition, semantic reasoning, and independent verification.
