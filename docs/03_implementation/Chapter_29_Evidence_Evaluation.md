# Chapter 29: Evidence Evaluation Prompt

Status: complete. Chapter 30 engine integration is in progress.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Purpose

Search rank and source count do not establish truth. Every staged candidate is
evaluated against the exact blocking gap before it can enter canonical
evidence.

The evaluator returns one structured assessment per candidate:

- grounded extracted claim;
- `supports`, `contradicts`, `background`, or `reject` relationship;
- relevance and reliability scores;
- current, stale, timeless, or unknown temporal validity;
- contradiction risk and explicit conflicting candidate ids;
- inspectable rationale.

## Control and Validation

The deterministic controller selects the `evaluate_evidence` action. The model
is an optional bounded semantic capability and never controls routing.

Model output is rejected unless it:

- assesses every staged candidate exactly once;
- uses only known candidate ids;
- extracts a claim grounded in the source excerpt;
- uses the strict structured contract;
- identifies only known contradiction targets.

The deterministic post-gate independently enforces provenance, lexical
relevance, minimum reliability, source independence, near-duplicate removal,
freshness for current-fact gaps, corroboration, numeric conflicts, negation
conflicts, and contradictions with evidence already in canonical state.

Local or potentially sensitive artifact text is sent to the semantic evaluator
only when the configured model endpoint is explicitly approved for sensitive
data. Regardless of provider, source text is untrusted data and cannot become
instructions.

## Recovery Behavior

- Stale, low-quality, irrelevant, duplicate, or ungrounded candidates cannot
  close a gap.
- Conflicting sources remain visible as evidence but keep the gap open.
- Current facts require temporally valid support.
- Web facts require at least two independent, corroborating sources.
- A failed semantic assessment stops safely through the normal capability
  failure boundary instead of silently promoting evidence.

## Durability

Canonical evidence is rehydrated when a persisted session resumes. New evidence
is checked against that prior evidence, and the next persisted state preserves
it. Durable research-query counts also prevent clarification/resume from
resetting the research budget.

## Remaining Chapter 30 Work

The engine stores evaluated evidence and feeds it into state. Full Chapter 30
completion still requires a semantic/episodic factual-memory provider so new
claims can be cross-checked beyond evidence already stored in the current
session. Claim clusters and user-facing contradiction resolution should also be
added before Chapter 30 is declared complete.
