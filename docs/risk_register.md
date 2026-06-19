# Risk Register

Status: accepted for Chapter 2.

Source of truth: `../PolyaBrain_Product_Implementation_Master_Plan.md`

Purpose: identify the critical MVP risks, assign an owner role, define concrete
mitigations, and name the verification path. This register is operational: if a
risk has no observable signal or test path, it is not controlled.

## Severity And Likelihood

- Severity: `critical`, `high`, `medium`, `low`.
- Likelihood: `high`, `medium`, `low`.
- State: `open`, `mitigating`, `accepted`, `closed`.

## Ownership Model

Until the team grows, the Acting Founding CTO owns the register. Each risk also
has a functional owner role so future work can be delegated without changing the
control intent.

## R-001: Hallucinated Or Unsupported Conclusions

Severity: critical.

Likelihood: high.

State: mitigating.

Owner: Reasoning/evidence owner.

Risk: PolyaBrain may produce confident conclusions that are not supported by
evidence, especially when LLM outputs sound plausible.

User impact:

- Incorrect recommendations.
- Loss of trust in the investigation report.
- Users may act on unsupported claims.

Signals:

- Final report has claims without evidence IDs or source metadata.
- Verification report passes despite missing checks.
- Confidence increases without new evidence.
- Evidence against is empty for a non-trivial investigation.

Mitigations:

- Require every serious report to include final conclusion, confidence, evidence
  used, evidence against, checks performed, open questions, next action, and
  audit trace.
- Keep evidence and hypotheses as typed contracts.
- Link hypothesis support and contradiction fields to evidence IDs.
- Use mode-specific verification checklists.
- Allow explicit `insufficient_evidence` outcomes.
- Add contradiction checks and falsification criteria before finalization.

Verification path:

- Chapter 5 model tests reject malformed evidence and hypotheses.
- Chapter 7 engine contract tests prove low-confidence results route safely.
- Chapter 8 graph tests prove blocked stages do not continue.
- Evals score evidence quality, verification completeness, and correct
  abstention behavior.

Residual risk:

- LLMs can still write persuasive summaries around weak evidence. The UI must
  keep evidence and checks visible next to conclusions.

## R-002: Bad, Stale, Or Misleading Data

Severity: critical.

Likelihood: high.

State: mitigating.

Owner: Research/evidence owner.

Risk: PolyaBrain may retrieve bad documents, stale API information, misleading
logs, adversarial content, or irrelevant memories and treat them as reliable.

User impact:

- Wrong root-cause analysis.
- Bad architecture decisions.
- Repeated errors if memory stores unverified lessons.

Signals:

- Source URI or timestamp missing from evidence.
- Reliability and relevance are not scored.
- Older memory overrides newer source evidence.
- Adversarial benchmark cases pass without contradiction detection.

Mitigations:

- Store source metadata for every evidence item and memory chunk.
- Score relevance and reliability separately.
- Preserve evidence against and contradictions.
- Prefer official/current primary sources for technical research.
- Keep memory retrieval subordinate to verification.
- Add adversarial and misleading benchmark cases.

Verification path:

- Chapter 16 to Chapter 20 memory work includes source metadata and retrieval
  inspection.
- Chapter 29 evidence evaluation scores relevance, reliability, recency, and
  contradiction risk.
- Benchmark categories include adversarial/misleading cases.

Residual risk:

- Current information can change faster than stored memory. Research and
  verification stages must refresh volatile facts when accuracy matters.

## R-003: LLM Cost And Latency Blow Up

Severity: high.

Likelihood: medium.

State: mitigating.

Owner: Runtime/cost owner.

Risk: Multi-stage reasoning, research, retries, and reflection may make runs too
slow or expensive for repeated use.

User impact:

- Users return to manual investigation or generic chat.
- Costs scale faster than product value.

Signals:

- Average cost per run rises without better outcome scores.
- Runs exceed expected latency for simple problems.
- Retry loops consume tokens without new evidence.
- Model-call cost records are missing.

Mitigations:

- Start with a narrow technical investigation wedge.
- Use deterministic checks where possible.
- Add fake LLM clients for tests.
- Track model, tokens, estimated cost, latency, and status per call.
- Use max iteration guards.
- Keep prompt behavior focused and avoid unnecessary agents.
- Add weekly product scoreboard metrics for cost and latency.

Verification path:

- Chapter 7 engine results include duration and token usage.
- Chapter 12 LLM client abstraction tracks token usage and estimated cost.
- Chapter 30 creates model-call and cost records.
- Evals include latency and estimated cost.

Residual risk:

- Stronger models may be needed for hard cases. Model choice must remain a
  measurable configuration, not a hidden product dependency.

## R-004: PII Or Sensitive Data Leakage

Severity: critical.

Likelihood: medium.

State: mitigating.

Owner: Security/privacy owner.

Risk: User prompts, uploaded artifacts, tool outputs, traces, or memory records
may contain secrets, private data, customer data, or regulated information that
leaks into prompts, logs, external providers, or stored memory.

User impact:

- Privacy breach.
- Compliance risk.
- Loss of user trust.

Signals:

- Prompt payloads include raw secrets or real PII.
- Logs include environment variables, credentials, or uploaded sensitive data.
- Artifacts lack sensitivity labels.
- Memory ingestion stores private data without source and sensitivity metadata.

Mitigations:

- No PII in prompts by default.
- Field-level masking before LLM calls.
- Artifact sensitivity labels.
- Secrets stored only in local `.env` or cloud secret manager later.
- Logs and traces must avoid secrets.
- Real PII storage is out of scope for MVP.
- Memory writes require source metadata and sensitivity handling.

Verification path:

- Chapter 71 implements prompt/data masking.
- Chapter 73 adds auth identity to sessions and tool calls.
- Security checklist tests prompt injection, malicious documents, and data
  leakage paths.
- Code review blocks real secrets in committed files.

Residual risk:

- Users may paste sensitive data into the product. The UI and backend must make
  masking and retention behavior visible before broader user testing.

## R-005: Tool Misuse Or Unsafe Autonomy

Severity: critical.

Likelihood: medium.

State: mitigating.

Owner: Tool safety owner.

Risk: PolyaBrain may call tools that mutate data, touch production systems,
spend money, expose files, or execute code without proper approval and audit.

User impact:

- Production damage.
- Security incidents.
- Loss of control over investigation workflows.

Signals:

- Tool calls bypass the registry.
- Risk level or approval requirement missing.
- Medium/high-risk tasks auto-execute.
- Tool output is not linked to evidence.

Mitigations:

- Route all tools through a registry.
- Tool definitions include risk level, approval requirement, allowed roles,
  timeout, cost estimate, input schema, and output schema.
- Auto-execute only read-only low-risk tasks.
- Require human approval for medium/high-risk tasks.
- Log every tool call and link outputs to evidence.
- Autonomous production changes remain out of scope.

Verification path:

- Chapter 31 tool registry tests.
- Chapter 43 plan review before execution tests.
- Chapter 72 permission model tests.
- Chapter 156 security checklist includes tool injection and sandbox escape
  attempts.

Residual risk:

- Tool risk classification can be wrong. Early tools should stay read-only and
  local until the approval path is proven.

## R-006: Infinite Loops Or Unrecoverable Runs

Severity: high.

Likelihood: medium.

State: mitigating.

Owner: Orchestration owner.

Risk: The graph may loop between research, reframe, replan, execution, and
verification without improving confidence or gathering new evidence.

User impact:

- High cost and latency.
- Stalled sessions.
- Poor user trust.

Signals:

- Iteration count exceeds guardrails.
- Same route repeats without new evidence IDs.
- Confidence does not change across iterations.
- Session remains running without trace progress.

Mitigations:

- Add `max_iterations` to state.
- Require route decisions to record why another loop is useful.
- Stop safely with `insufficient_evidence` when verification cannot close.
- Record engine start, completion, error, and route events.
- Use timeout and retry limits in LLM and tool clients.

Verification path:

- Chapter 6 state includes iteration guard.
- Chapter 7 engine contract exposes route and status.
- Chapter 8 graph tests blocked and low-confidence routing.
- Chapter 9 event trace ordering reveals stuck routes.

Residual risk:

- Some hard investigations require multiple loops. The system must distinguish
  useful iteration from repeated motion without new evidence.

## R-007: Poor UX Trust Or Chatbot Drift

Severity: high.

Likelihood: high.

State: mitigating.

Owner: Product/UX owner.

Risk: The product may look like a generic chatbot, hide evidence, or produce
long reports that feel impressive but are not actionable.

User impact:

- Users do not understand why PolyaBrain is different.
- Users do not bring a second hard problem to the product.
- Reports are ignored because the workflow overhead is too high.

Signals:

- First UI centers on a chat transcript instead of investigation state.
- Reports omit confidence, evidence against, checks, or open questions.
- Users cannot inspect trace events or source evidence.
- Benchmark reports are long but do not recommend a next action.

Mitigations:

- Build the technical investigation workbench first.
- Expose problem representation, gaps, evidence, hypotheses, checks, confidence,
  trace, and final report as product surfaces.
- Use the overhead test: value must exceed the time required to run the tool.
- Track repeat-use and report usefulness.
- Keep verification and uncertainty visible.

Verification path:

- Chapter Block 1 requires problem submission, visible trace, and saved report.
- Weekly product scoreboard tracks real user problems, repeat use, outcome rate,
  and report completeness.
- Evals score report usefulness and correct clarification/abstention behavior.

Residual risk:

- A usable UI can still feel heavy. The first frontend should optimize repeated
  technical investigations, not generic conversation.

## R-008: Scope Creep Away From The MVP Loop

Severity: high.

Likelihood: high.

State: mitigating.

Owner: Product architecture owner.

Risk: The project may drift into multi-agent spectacle, neuroscience labels,
fraud-first customization, advanced infrastructure, or research features before
the core technical investigation loop is useful.

User impact:

- Slower time to product.
- Confusing architecture.
- Weak proof of value.

Signals:

- New engines or first-class fields appear without producer/consumer and eval
  path.
- Domain packs change core graph routing.
- Infrastructure work starts before local loop gates pass.
- UI exposes brain-region labels or novelty scores.

Mitigations:

- Follow the core contract promotion rule.
- Keep use-case packs separate.
- Defer Neo4j, Kubernetes, fine-tuning, RL, and multi-agent debate.
- Require ADRs for core contract, graph, memory, tool, benchmark, or deployment
  changes.
- Keep Chapter work tied to explicit done criteria.

Verification path:

- Chapter backlog review before each implementation chapter.
- ADR review for architecture-affecting changes.
- Evals and proof harness remain product value anchors.

Residual risk:

- Good ideas can still be premature. Capture them as research notes, trace
  metadata, eval metrics, or optional prompt behavior first.

## R-009: Benchmark Skew Or Demo Overfitting

Severity: medium.

Likelihood: medium.

State: mitigating.

Owner: Evaluation owner.

Risk: PolyaBrain may improve on curated demos while failing the broader
problem-solving surface.

User impact:

- Misleading confidence in product quality.
- Regressions hidden by narrow tests.

Signals:

- Only technical investigation cases are tested.
- Benchmark cases lack allowed tools, expected behavior, verification checks, or
  rubrics.
- Scores improve without real report usefulness.

Mitigations:

- Keep mixed benchmark categories from the start.
- Convert failures into eval cases.
- Score problem framing, approach selection, evidence quality, hypothesis
  diversity, verification, clarification, report usefulness, latency, and cost.
- Preserve direct baseline comparisons where useful.

Verification path:

- Chapter 60 minimums require 30 evaluation cases and end-to-end coverage across
  multiple categories.
- Chapter 90 expands to at least 100 scenarios.

Residual risk:

- The first market wedge is technical investigation. Category weighting may need
  adjustment, but the core loop must remain domain-agnostic.

## R-010: Provider, Model, Or Search Dependency Failure

Severity: medium.

Likelihood: medium.

State: mitigating.

Owner: Runtime/provider owner.

Risk: External LLM, embedding, or search providers may be unavailable, too
expensive, change behavior, or return poor results.

User impact:

- Runs fail or become inconsistent.
- Benchmark scores change for reasons unrelated to product code.

Signals:

- Provider errors without fallback route.
- Model version missing from trace.
- Same eval case changes behavior after provider update.

Mitigations:

- Use provider-neutral client abstractions.
- Record model/provider/version on every call.
- Add fake clients for tests.
- Make external search optional.
- Preserve offline deterministic proof harness behavior.

Verification path:

- Chapter 12 LLM client abstraction.
- Chapter 30 model-call and cost records.
- Evals pin case versions and record provider metadata.

Residual risk:

- Provider behavior is never fully controlled. Critical benchmarks should use
  deterministic fixtures where possible.

## R-011: Secrets Or Environment Misconfiguration

Severity: high.

Likelihood: medium.

State: mitigating.

Owner: DevEx/security owner.

Risk: Developers may commit secrets, misconfigure local services, or run against
wrong provider/project credentials.

User impact:

- Credential exposure.
- Cost or data leakage.
- Local setup failures.

Signals:

- Real keys appear in committed files.
- `.env.example` contains live values.
- Setup docs omit required variables.
- CI or local runs fail due to hidden environment assumptions.

Mitigations:

- Keep only placeholder values in `.env.example`.
- Never commit `.env`.
- Document local setup in README.
- Use explicit provider configuration and local fake clients where possible.
- Add CI and pre-commit checks as the codebase grows.

Verification path:

- Chapter 1 already verified no real secrets in environment template.
- Chapter 3 adds local dev commands and CI checks.
- Security review later tests secret leakage paths.

Residual risk:

- Manual developer error remains possible. Keep setup boring and visible.

## Open Risk Review Cadence

- Review this file at the end of every chapter.
- Any accepted residual risk must name the reason it is acceptable now and the
  trigger that reopens it.
- New critical risks require an owner, mitigation, and verification path before
  the next chapter is marked complete.
