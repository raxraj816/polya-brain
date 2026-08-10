# Chapter 14 Constraint Discovery Engine

Status: complete on `feature/chapter-12b-13-openrouter-representation`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Product Behavior

Constraint discovery is now a required controller action after a valid problem
representation and before knowledge acquisition, hypothesis generation, or
planning. It identifies what must remain true for a result to count as solved.

The deterministic engine records:

- explicit constraints already present in the structured problem;
- every declared success criterion;
- time-window validity;
- privacy and sensitive-data handling;
- required-data availability;
- payment and PCI controls;
- causal-claim requirements;
- requested confidence thresholds;
- resource, cost, and deadline boundaries.

If the problem has no observable success criterion, or a planning/comparison
problem lacks a concrete cost, time, risk, quality, or measurable boundary, the
engine returns `needs_input`. It does not promote a partially constrained
problem to downstream cognition.

## State, Trace, And Persistence

Accepted constraint statements are merged into `StructuredProblem.constraints`
without duplicates. The cognitive adapter returns the updated structured
problem through a typed observation, and the persisted session path upserts the
same canonical state into `structured_problems.constraints`.

Each discovered constraint emits `constraint_discovered` with its category,
origin, source, and hardness. Missing boundaries emit `constraint_gap`; the
normal clarification flow persists and streams the question.

## Constraints Change Action Selection

Capability declarations now state whether the capability is approved for
sensitive data. When an accepted privacy constraint is present, the controller
rejects an otherwise useful capability that lacks that approval. The behavioral
test proves that an unapproved web search is rejected and an approved local
inspector is selected instead.

This is deployment policy metadata, not a claim that a tool is inherently safe.
Capabilities remain unapproved by default and must be registered explicitly.

## Success-Criteria Guard

The cognitive kernel will not accept a verifier's `passed=true` claim when the
report contains fewer checks than the structured problem has explicit success
criteria. It downgrades the report to failed, records
`success_criteria_verification_failed`, decreases confidence, and withholds the
proposed final answer.

This is a structural minimum. Semantic criterion-to-check matching remains a
later verification-engine responsibility; the current guard prevents obvious
under-coverage without promoting a new core contract prematurely.

## Verification

- Focused constraint, controller, and kernel tests pass.
- Full unit suite: 211 passed, 18 skipped.
- Formatting, Ruff, and mypy pass across 68 source files.
- Real Postgres suite: 18 passed; database smoke passed.
- Six pre-platform proofs, ten Chapter 11 examples, and all ten Chapter 13-C
  cognitive-control cases pass.
- A rebuilt Docker API smoke completed create -> clarification -> response ->
  representation -> constraint discovery -> truthful insufficient-evidence
  stop. The canonical row contains success, time-window, privacy, and PCI
  constraints, and the persisted trace records the controller decision plus
  per-constraint events.

## Known Boundary

Constraint discovery is intentionally deterministic and conservative. It does
not yet understand every domain-specific regulation or tradeoff, and the
persisted runtime still lacks the minimum production acquisition, reasoning,
execution, and verification capabilities. The next gate is to add those
capabilities and compare full verified outcomes against the same model with the
same tools.
