# MVP Architecture Decisions

This document clarifies what to build first. It does not replace the master plan.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## MVP Shape

Build **PolyaBrain Investigator** through the **PolyaBrain Cognitive Runtime** as
a modular monolith. This is the implementation shape of the first product, not
a decision to build a broad platform before proving user value:

- One Python/FastAPI backend.
- One LangGraph state machine.
- One Next.js frontend.
- One Postgres database with `pgvector`.
- Redis for cache, streaming run state, and rate limits.
- Docker Compose for local development.
- Optional external LLM provider.
- Optional external search provider.

The code should be modular by engine, but deployment should stay simple until the end-to-end loop is useful.

After the local product proof, the initial delivery target is a managed cloud
product and API. Runtime, capability, persistence, and provider boundaries must
remain portable to Indian or other sovereign cloud, enterprise private cloud,
and local execution. No model vendor or cloud provider owns the cognitive loop.

“PolyaBrain Intelligence OS” describes the eventual governed capability and
application platform. It is not MVP positioning and may be claimed only after
dependent applications, developers, and cross-domain proof exist.

## Build Now

- A domain-independent cognitive controller that selects state-dependent
  actions; models and external systems remain replaceable capabilities.
- A trace-derived temporary task model and hard per-run resource ledger kept in
  the experimental cognitive layer rather than duplicated in core state.
- Impasse-driven knowledge acquisition: retrieve or observe only when a
  verification-blocking gap exists, and select among memory, artifacts, APIs,
  web, calculation, measurement, simulation, experiment, code, and human input.
- Deterministic cognition for known procedures and fused semantic calls for
  compatible stages; nine logical engine responsibilities never imply nine
  model calls.
- Verified procedural consolidation whose transfer must be rechecked on the
  current task.
- An experimental cognitive-action model and capability registry kept outside
  core contracts until cross-domain evaluation proves promotion.
- Typed engine interfaces.
- Stateful Polya loop.
- Problem representation.
- Problem reframe pass using trace details rather than new core fields.
- Approach selection using existing product modes and problem types, inferred when the user does not provide a mode.
- Constraint discovery.
- Knowledge gap detection.
- Research and evidence evaluation.
- Divergent hypothesis generation, convergent filtering, and planning.
- Knowledge-rich analogical transfer from memory when structural similarity may help.
- Bounded reframe/incubation pass after evidence gathering, with verification required for any changed claim.
- Safe tool execution.
- Verification checklists by mode and replanning.
- Stage-gated routing so weak outputs ask, recover, reframe, gather evidence, or stop safely instead of flowing forward.
- Reflection and logical semantic, episodic, and procedural memory.
- Evaluation harness across mixed problem categories.
- User-visible trace, reasoning mode, evidence, hypotheses, final report, confidence, and open questions.

## Defer Until After MVP Proof

- Neo4j.
- Pinecone, Milvus, or other separate vector databases.
- Kubernetes.
- Separate microservices per engine.
- Fine-tuning.
- Reinforcement learning.
- Multi-agent debate.
- Autonomous production changes.
- Real PII storage.
- A broad capability marketplace or Intelligence OS positioning.

## Memory Decision

Use three logical memory types in one physical store first:

- Semantic memory: `knowledge_chunks` plus `pgvector`.
- Episodic memory: sessions, reasoning events, evidence, and outcomes.
- Procedural memory: strategies, strategy scores, applicability rules, and tool patterns.

Move to a graph database only when measured retrieval or traversal bottlenecks justify it.

## Engine Decision

The MVP implementation uses nine logical modules:

1. Problem Representation Engine.
2. Constraint Discovery Engine.
3. Knowledge Gap Detector.
4. Research and Acquisition Engine.
5. Evidence Evaluation Engine.
6. Hypothesis and Reasoning Engine.
7. Execution Engine.
8. Verification Engine.
9. Reflection and Memory Engine.

Each engine needs typed input/output, tests, prompts, and telemetry.

An engine is a logical responsibility, not a required provider invocation.
Several compatible responsibilities may share one schema-validated semantic
call, while a known deterministic procedure may satisfy an engine with zero
model calls. The audit trace must disclose which occurred.

The engines do not own the run independently. The cognitive controller owns
selection of the next action from canonical state. Engine, model, memory, and
tool results enter as observations and cannot directly finalize, verify, or
write durable learned knowledge without the corresponding kernel gates.

Creative problem-solving behavior belongs inside these engines, not in a separate "creativity engine." The Reasoning Engine owns divergent generation and convergent filtering. Memory retrieval owns analogical candidates. Verification owns falsification and contradiction checks. Reflection owns strategy learning from which hypotheses, reframes, and analogies helped or failed.

## Product Boundary

PolyaBrain Investigator is the initial user-facing product. The PolyaBrain
Cognitive Runtime is its domain-independent intelligence core. The managed cloud
service is the initial delivery model. Language models, tools, knowledge sources,
and infrastructure providers are replaceable capabilities rather than product
identity.

Payment fraud, coding contests, DevOps incidents, compliance, research, tutoring, and enterprise decision support are validation or packaging surfaces, not separate core architectures.

The architecture wins only when it improves verified outcomes per unit of total
cost and user effort. General-purpose intelligence and Intelligence OS are
measured future claims, not properties conferred by modular architecture.

## Source-Of-Truth Rule

If this document or any architecture/research document disagrees with the master plan, follow the master plan.

## Chapter 73 identity boundary

Use OIDC through Authlib and revocable hashed opaque browser sessions for the
private beta. The API owns authentication/authorization; the frontend proxy and
screen are additional controls. Session ownership and private memory namespaces
are enforced in request dependencies and repository queries. Operator-local data
is not automatically shared. No database RLS claim is made. See
[Chapter 73](../03_implementation/Chapter_73_Authentication_And_Isolation.md) for
configuration, protocol tests, namespace migration, and remaining deployment gates.

## Chapter 13-P: explicit online acquisition

The shared CLI/API runtime can select Brave or OpenRouter server search through
`SEARCH_PROVIDER`. OpenRouter uses the configured model/account and one Exa search
step. Original citation excerpts are untrusted candidates; generated answer text
is discarded. The external capability reserves both model-request and external
budgets and records reported usage/unknown failure usage. This adds no foundation
model training, local corpus requirement or new canonical state field. It still
depends on external pretrained models and does not establish compute independence.
The controller now has experimental bounded recovery for an overbroad public gap:
one scope review preserves the user's success criteria and reports deferred unknowns;
a deterministic public-page reader can retrieve missing passages without another
search-model request. Sources remain candidates until evaluated. Reads use public
DNS validation, pinned connections and TLS hostname verification, no redirects or
proxies, and fixed response/time/passage bounds. The same total external budget,
privacy boundary and offline switch apply. See Chapter 13-P for live failures and
repaired development cases; fresh efficiency/transfer comparisons remain required.

## Chapter 13-P: Verification-driven public research

A failed conclusion checker can request one bounded public-research round through
experimental typed output, bound to its failed-check indices. The controller's
existing gap/acquisition/evaluation loop handles the request; the execution
planner does not gain research tools. Once gaps close, fresh bounded analysis
precedes a new independent check. Keep previous tasks, outputs and verdicts as
history; distinguish the revision with new task IDs. Public sources cannot satisfy
private-state or observed-execution requirements. Existing offline, privacy and
resource limits apply without resets. Failure or budget exhaustion remains a
failure, including when public sources are unavailable.

PolyaBrain remains the product identity. Investigator is the initial verified
workflow; it does not constrain the runtime's long-term problem domains. The UI
must not imply present human equivalence or physical embodiment.

A live DART replay exposed an incorrectly passed time-uncertainty unit change.
Apply a deterministic necessary consistency check to model-proposed final answers
using raw admitted excerpts; reject a conflicting explicit time uncertainty and
retain the rejected candidate. This adds no model call and is intentionally narrow,
with unresolved semantic and measurement-definition checks still owned by the
independent checker.

The persisted adapter and raw runtime share the CLI's default of 24 controller
cycles. The previous API default of 12 truncated a live discovery sequence before
verification. This changes only loop steps: model/external calls, tokens and time
retain their existing hard budgets. Explicit lower cycle limits remain effective.

## Chapter 13-P: Research the residual question

Persist supported-question progress after scope review even without a deferral.
Keep remaining questions batched to avoid one search per question and retain the
original goal and criteria. Carry only navigation guidance across the recorded
parent/residual lineage; do not transfer a source-coverage verdict.

The existing evidence evaluation may recommend discovery or reading a particular
already-admitted source. Deterministic admission and page-read eligibility checks
own dispatch. This avoids spending a read on a source about already answered
questions merely because its publisher is authoritative. Targeted follow-up queries
lead with the remaining question. Explicit reads retain whole-user lexical coverage and prioritize named residual
sections within the same passage limits. These mechanisms add no model calls and no budget increase. A model's
estimate of likely document coverage can still be wrong; final verification and
failure reporting remain mandatory.

The fused checker remains responsible for verifying substantive findings and
composing the terminal answer in one call. It must not demand a terminal answer
before it runs. This clarifies existing stage ownership without adding a synthesis
call or weakening requirements for facts, analysis, citations or observed execution.

### Chapter 13-P: candidate edit transfer

Reuse a prior verified edit as a hypothesis inside the existing explicit
source/check workflow. Do not retrieve an earlier final answer or skip current
execution. Existing procedural metadata and owner-scoped queries hold compact
versioned lessons; no new database table, embedding index, core contract field
or learned ranking score is required. One unambiguous exact fragment can avoid
another proposal-model call, while both baseline and patched source still run
against the current independent check. Failed transfer remains a failed check.

This first mechanism deliberately stops at exact-fragment reuse. It supplies an
end-to-end learning measurement before attempting richer structural compilation.
Stored history and reports still consume storage; the compact lesson size is not
the product's total storage footprint. Model-call savings on supplied-check tasks
do not establish general intelligence or superiority over other products.

### Chapter 13-P: recover from a rejected memory edit

A measured failed transfer now routes to the existing source-patch proposer once,
rather than to the generic planner that asked for execution evidence despite an
available sandbox. The replacement targets the original admitted source. Retire
only the failed active plan task after validating trace metadata at the kernel
boundary; retain its full plan, observed output and historical failed verification.
A unique replacement task ID prevents old execution/verifier bindings from passing
the new repair. No permission, criterion or resource budget is reset.

The same route now accepts a measured failed first model edit. Recovery eligibility
binds complete, failed original/candidate executions to the current admitted
source/check and candidate digests, plus trusted proposal/execution events. A
vacuous check, timeout, truncated/missing execution or mismatched snapshot stops
without another proposal. Source-patch investigations with ineligible failures
also stop instead of sending a generic planner around these restrictions. A
second failed edit cannot start another recovery; execution and verifier gates
remain mandatory and only the current verified replacement can become a lesson.

The current candidate owns final reporting and learning after its independent
checks pass. A duplicate or second failed proposal, vacuous original check, missing
model or exhausted allowance cannot become success. Two known protocol failures
now recover in one model request each; this closes a narrow recovery defect, not
the broader unseen-task or competitive-value gates.

### Chapter 13-P: expression-level transfer

Frozen renamed-variable cases showed that exact memory still spent one model
request per transfer. Add a bounded syntax adapter over existing verified edit
fragments, after exact matching misses. It can move an expression repair from a
return statement into an assignment and consistently rename its variables.
It adds no model call, persisted contract or dependency. Unsupported or ambiguous
patterns use the ordinary route. Verification and bounded failed-transfer recovery
remain unchanged. Three development families now reuse with zero requests; their
incompatible rules reject the reused edit and recover with one request each.
This is a limited structural generalization, not arbitrary procedural learning.

### Chapter 13-P: coding verification and recovery boundary

Reject missing, ambiguous, unsuccessful, truncated or empty sandbox checks before
calling the conclusion model. This deterministic preflight can reject execution;
it cannot certify an algorithm. Successful execution still requires independent
semantic review of requirements, correctness and complexity. Analytic metadata
containing an invariant or complexity claim is not a verifier.

A replacement Python plan uses optional `params.supersedes_task_id` to name one
earlier sandbox task. It must retain all original assertions and pass fresh
execution. Task names never retire failures; unrelated tasks remain required.
Changed oracles need separate justification and are not supported by this
automatic path. Preserve all failed observations for audit. Before accepting a
coding answer, compare its Python blocks with active executed implementations.
This identity check is necessary provenance, not proof of correctness. These
checks use existing plan metadata and reports; no core contract is promoted.

### Chapter 13-P: preserve framing context during schema repair

The matched calendar pilot exposed a repair-boundary failure: an omitted required
`unknown` list was repaired into the answer the runtime should compute, then
routed to the user as a missing fact. Schema repair now retains the original
system framing rules, configured capabilities and serialized user input. Invalid
output stays untrusted user-role data. Empty required lists are allowed explicitly;
actual missing facts still require clarification. This is a prompt/context repair,
not a parser default that silently treats missing unknowns as solved.

Sandbox-enabled fused proposals receive 6,000 output tokens by default because
the previous 3,200 cap truncated a complete implementation/test proposal. Explicit
overrides and the total run budget still bind; the non-coding default is unchanged.
The subsequent live rerun uses the same frozen case and independent checks.

### Chapter 13-P: bounded terminal review

The recovery planner now uses the same remaining-budget principle: reserve an
integer number of full-output provider attempts, enforce that allowance across
retries/schema repairs/routes, and reject an invocation that cannot afford one
attempt. Unknown remote usage remains charged as reserved output, and privacy
and checkpoint admission still apply.

Generated test expectations are screened before proposal admission. Preserve
explicit user examples and existing checks; prefer executable simple references
for additional cases. `generated_check_sources@0.1.0` rejects direct call/literal
equality or identity assertions that lack token-equivalent user provenance or an
unchanged admitted check. The initial response and its bounded repair both use
this policy. When nested schema validation fails, the gateway independently
collects detectable test-origin errors for the same bounded repair request; it
does not spend another attempt to reveal a previously hidden diagnostic.
No literal is silently rewritten. The screen is deliberately narrow:
it cannot prove dynamic reference semantics or detect every alias-hidden guess.
Final review must inspect reference independence, specification fidelity and
actual assertions. The sandbox's `python_checks@0.2.0` harness rejects single
expressions evaluating to False while preserving statements and helper calls.

Coding delivery now has an optional deterministic assembly step after semantic
review. `docker_python_sandbox@0.4.0` retains exact code, test-list and result hashes
in its execution event. The reviewer sees the full canonical implementation and
test results, but can use issued SHA-256 references rather than copying code into
its answer. `tested_code_delivery@0.1.0` validates those bindings and complete,
unique references before attachment. Final code-identity checks remain in force.
Old execution records without bindings retain the full-code response path.
Neither references nor passing finite tests bypass correctness/complexity review.

The conclusion checker can reserve fewer provider attempts when the trace's
remaining resources cannot fit its full retry/fallback policy. Its optional
function-adapter reservation is consumed by controller admission and checkpoint
rechecking; execution derives the same bound and independently rejects exhaustion.
One allowance covers all retries, schema repair and configured fallback routes.
Every admitted attempt reserves a full per-request output allowance; provider
exceptions with unreported tokens retain that reservation in the usage ledger.
Provider-reported usage stays separate from this conservative charge. Adapter
retries are disabled at the actual dispatch boundary. Review instructions and
code-identity acceptance are unchanged. Other capabilities keep static admission;
this does not claim a comprehensive pre-request input-token or monetary meter.

The v5 pilot also exposed a preventable contract-repair request: an unexecuted
algorithm was labeled `selected` without evidence. The deliberator prompt now
spells out the existing hypothesis validator requirements and keeps unexecuted
algorithm proposals as candidates. Predicted test success and desired complexity
belong in proposed checks or analysis, not evidence. The validator remains strict;
this prompt change is evaluated by a fresh frozen-case rerun, not assumed effective.

### Chapter 13-P: compact capability requests

`cognitive_capability@0.9.0` elides only default null/empty collection fields from
typed state objects. Scalar statuses, risk, priority, flags, zero values, arbitrary
JSON tool inputs/outputs, code, assertions, provenance and failed checks remain
explicit. Canonical state and stored artifacts are unchanged. Output schemas
omit presentation titles while retaining property names, descriptions, defaults,
required fields and validation bounds. Repair prompts reuse the original schema
once rather than repeating it.

With no admitted evidence, fused deliberation and hypothesis-generation schemas
allow candidate/deferred/rejected statuses only. The gateway enforces this on
initial and repair responses, including extra-field pruning; invented support
strings cannot unlock selection, verification or falsification. With evidence,
the original contract remains available. This does not establish that every
cited evidence string is valid; existing evidence and terminal review still apply.


`cognitive_capability@0.10.0` adds bounded structural edits for parseable invalid
responses. It retains the complete original capability context and schema, asks
only for explicit changed fields, applies edits to a copy, and reruns the original
validation. Malformed original JSON keeps full-response repair. The protocol
cannot create parent paths, insert/delete list elements, replace the root or use
overlapping paths. It does not change canonical state or waive recovery rules.
Existing observation traces retain bounded repair identity metadata through the
semantic broker; no new persistent field or migration is introduced.
