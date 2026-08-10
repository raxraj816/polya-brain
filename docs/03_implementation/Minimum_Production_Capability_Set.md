# Minimum Production Capability Set

Status: in progress as part of the Chapter 13-C product-value gate.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Implemented

The persisted cognitive runtime now registers controller-governed capabilities
for:

- knowledge-gap detection;
- diverse falsifiable hypotheses;
- bounded planning and replanning;
- low-risk analytic execution;
- verification against evidence, outputs, and every success criterion;
- reflection only after accepted verification;
- exact local binary arithmetic;
- durable human-input pauses;
- an available-data-source registry;
- bounded production web search through a provider-neutral Brave adapter;
- explicit promotion of search candidates through a separate source-quality
  evaluation action;
- explicit, allow-root-contained local text-artifact inspection with file-size,
  type, secret-file, and prompt-injection boundaries;
- structured claim extraction and evidence relationship classification;
- deterministic relevance, reliability, freshness, independence,
  near-duplicate, corroboration, and contradiction post-gates;
- optional schema-bound semantic evidence assessment that cannot control the
  run or handle sensitive artifact text without explicit endpoint approval;
- durable evidence rehydration across clarification/resume.
- deterministic read-only CSV/JSON measurement with row/size/root boundaries,
  exact Decimal summaries, median, p95, missing counts, and categorical
  frequencies;
- digest-pinned, ephemeral Docker Python execution with no network or host
  mounts, read-only root, non-root identity, dropped capabilities, and hard
  CPU/memory/PID/time/output limits;
- structured assertion results that become execution evidence for independent
  verification;
- grouped table summaries and authorizer-protected read-only SQL over an
  in-memory table copy with step and result limits;
- explicit, exact scenario trajectories and threshold-crossing simulation;
- bounded controlled numeric experiment evaluation with effect, uncertainty,
  design assertions, and explicit statistical limitations.
- governed semantic recall with source, reliability, freshness, domain, and
  minimum-similarity gates;
- verified episodic case retrieval and durable verified procedural strategy
  transfer, including failed-strategy rates;
- new-evidence contradiction checks against admitted semantic memory.

Model capabilities return experimental structured proposals. They do not choose
the next action or mutate state directly. Responses are JSON extracted, contract
validated, and given at most one bounded repair attempt. Provider exceptions and
exhausted repair fail closed. The controller rejects an identical failed action
on unchanged state rather than consuming the remaining cycle budget.

Fully specified arithmetic uses a deterministic procedure pack. It detects the
numeric gap, calls an exact Decimal calculator, creates a falsifiable candidate,
plans a second calculation, executes it, verifies the result with matching
observations and an inverse arithmetic identity, reflects, and stops. It does
not call a model for steps with a reliable algorithm.

## Durable Product Output

The session transaction persists the latest canonical:

- structured problem and constraints;
- gaps and fill status;
- evidence with source metadata;
- hypotheses and falsification checks;
- plan tasks and their cognitive task ids;
- verification checks, failures, contradictions, and route;
- reflection as a full audit event.

`GET /api/v1/sessions/{session_id}/report` returns the final conclusion,
confidence level, verification status, evidence used, evidence against, checks,
failed checks, contradictions, open questions, recommended next action,
reflection, and audit trace path.

## Verification

- Full unit suite: 261 passed, 23 skipped.
- Real Postgres suite: 23 passed.
- Ruff, formatting, and mypy pass across 93 application source files.
- Six pre-platform proofs, ten Chapter 11 examples, and ten Chapter 13-C
  structural categories pass.
- Eleven offline outcome-harness contract checks pass, including a complete
  same-fake-model replay of both comparison conditions and condition-blind
  review-key separation.
- Rebuilt Docker API run `451c792e-6d74-4729-9205-d64bd6bea2f9` returned
  `23 * 7 = 161.`, passing verification, persisted artifacts, reflection, and a
  complete report.

## Remaining Gate

This is not yet a claim of general outcome superiority. Basic deterministic
table measurement, grouped querying, safe Python execution, scenario
simulation, and controlled numeric experiment evaluation are implemented. Local
text-artifact inspection is implemented; richer document extraction remains.
Web search is transport-tested but not live-provider tested
because this workspace has no configured search credential. The fair
six-category comparison harness now uses the same model, tools, observations,
pre-structured inputs, call budget, output-token limit, and alternating
execution order for PolyaBrain and the direct baseline. Its live attempt hit
HTTP 429 before one comparable case completed; that provider limit is a
benchmark blocker, not a product win or loss.
