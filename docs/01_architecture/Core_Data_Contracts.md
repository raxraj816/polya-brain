# Core Data Contracts

This is a quick implementation reference extracted from the master plan.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Problem Session

- `id`
- `user_id`
- `raw_input`
- `domain`
- `mode`
- `status`
- `created_at`
- `run_started_at`
- `completed_at`
- `final_answer`
- `confidence`
- `verification_status`

## Structured Problem

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

## Knowledge Gap

- `description`
- `gap_type`
- `priority`
- `why_needed`
- `suggested_source`
- `filled`
- `evidence_ids`

## Evidence Item

- `source_type`
- `source_uri`
- `claim`
- `raw_excerpt`
- `reliability_score`
- `relevance_score`
- `supports_hypothesis_ids`
- `contradicts_hypothesis_ids`

## Hypothesis

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

`origin` should distinguish direct reasoning, memory-derived analogy, user-supplied hypothesis, and reframe/incubation output. `selection_rationale` records why a hypothesis survived convergent filtering over plausible alternatives. Hypothesis diversity is evaluated at the run level, not stored as a core per-hypothesis score.

## Plan Task

- `id`
- `action`
- `tool_name`
- `params`
- `depends_on`
- `expected_output`
- `risk_level`

## Reasoning Event

- `id`
- `session_id`
- `engine_name`
- `event_type`
- `reasoning_mode`
- `summary`
- `metadata`
- `created_at`

`reasoning_mode` should use stable values such as `explore`, `compare`, `reframe`, `execute`, `verify`, and `reflect` so the user-visible trace can show how PolyaBrain moved from possibilities to conclusions.

## Verification Report

- `passed`
- `checks_run`
- `failed_checks`
- `contradictions`
- `confidence_delta`
- `recommended_route`

## Tool Definition

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

## Tool Call

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

## Artifact

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

## Evaluation Case

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

## User, Organization, And Project

User:

- `id`
- `email`
- `display_name`
- `role`
- `organization_id`
- `created_at`

Organization/project:

- `id`
- `name`
- `settings`
- `budget_limits`
- `retention_policy`
- `enabled_tools`
- `created_at`

## Feedback

The current local workbench implements a bounded persistence subset in
`human_feedback`: `id`, `session_id`, `feedback_type`, `correction` (optional
user-authored comment/corrected answer, at most 10,000 characters), and
`created_at`. A user produces this record; per-session feedback and history
feedback filters consume it for manual review. Tests verify it cannot overwrite
a report or become verified memory. This is application data, not a new cognitive
ranking signal. Identity, rating, and review-status transitions below remain
planned; all current entries await manual review. Feedback is sanitized before
storage and must still be treated as untrusted input.

Planned full contract:

- `id`
- `session_id`
- `user_id`
- `rating`
- `feedback_type`
- `comment`
- `corrected_answer`
- `created_at`
- `review_status`

## Connector

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

## Model Call And Cost Record

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

## Implementation Rule

Define these first as Pydantic models. Database schemas can follow the same contracts, with migrations added only after the model fields are stable.


## Local source/check input artifacts

The browser source/check workflow stores one `source_check_input` application
artifact containing the exact selected source and check snapshots, their SHA-256
hashes, and explicit execution/provider consent. Its producer is the user request;
its consumer is the session runner, which validates the record again and admits
it into a private temporary directory for the existing source-patch runtime.
It is not a new cognitive state field or ranking signal. The API rejects changed
hashes, missing consent, oversized/empty files, and known secret-like content
instead of silently rewriting executable snapshots. Canonical evidence retains
complete admitted excerpts; temporary execution files are removed after the run.
The local database retains user-selected input until its database retention is
managed. Public multi-tenant storage and retention controls remain pending.

Evidence `raw_excerpt` preserves its leading/trailing whitespace so executable
snapshots remain byte-faithful through validation and persistence. Empty or
whitespace-only excerpts remain invalid; normal claim/identifier trimming is
unchanged. Source/check tests include leading and trailing blank lines.


## Mode context propagation

The persisted session mode and optional domain are consumed by the representation
composer. The validated `approach_selected` trace event supplies mode/checklist
prompt context to downstream model capabilities. Existing core state models are
unchanged. Representation identity includes the mode/domain hint, and model
capability identity includes the shared prompt policy version. Optional UI
context remains clearly labeled user input in `raw_input`, rather than an inferred
fact or additional first-class ranking field.

## Chapter 73 persistence ownership

Existing `ProblemSession.user_id` is produced exclusively from a validated OIDC
principal in authenticated API requests; child records inherit the session owner.
`AuthSession` stores only a token digest, opaque issuer/subject-derived user ID,
creation and absolute expiry. `owner_id` on semantic, episodic, and procedural
memory is produced by the trusted repository context and consumed by every
retrieval, deduplication and learning update. These are security persistence
fields, not reasoning scores or user-supplied core problem fields. Cross-user
negative API/memory tests verify the boundary. Local legacy records remain in
`__local__`; no default shared memory is promoted. See Chapter 73 delivery notes.

## Chapter 77 admission persistence

`RunAdmission` is an operational record produced atomically with an authenticated
run/resume claim, before provider dispatch. It stores owner/session, start/finish,
outcome, and a snapshot of resource ceilings. Quota checks and the user's usage
view consume it; it is not a cognitive ranking signal or a currency ledger.
Unknown in-flight work retains its slot. Concurrent database and recovery tests
verify admission and release behavior. Details: Chapter 77 durable run allowances.


## Chapter 13-P provider options and deliverable scope

The existing `LLMRequestOptions.temperature` is optional (`None` by default).
Runtime prompt builders produce the unset value, and the provider adapter omits
it from the request; explicit numeric overrides remain bounded and are forwarded.
This permits strict JSON routing to models that reject temperature without
weakening required-parameter or data-policy controls. Adapter tests cover both
omission and explicit values. No new cognitive state or ranking field is added.

Requested deliverable scope remains in `raw_input`, framing constraints and
success criteria. Proposal verification checks factual completeness, evidence,
conditional feasibility and future checks. Implemented-outcome verification still
requires observed implementation and execution. Analytic outputs must contain
findings; disclaimers alone do not fulfill the requested analysis.

### Experimental dependency source facts

`dependency_source_facts@0.2.0` is an internal pure procedure, not a new canonical
engine, score, or state contract. It produces bounded prompt context and the
`dependency_source_fact_coverage_checked` trace event from complete admitted
JSON/TOML evidence. The fused deliberator consumes its comparisons; the conclusion
checker consumes both comparisons and a necessary verbatim coverage check. A
failed check replaces a proposed pass and removes its answer/reflection before
state mutation. Provider usage remains recorded even when its answer is rejected.

Supported source shapes are a pip-audit-style `dependencies` list or the recorded
`affected_packages` extract, a PEP 621 project manifest, and an optional installed
package-to-version/requirements mapping. Comparisons preserve declared extras and
markers without evaluating them on the runtime host. Listed fixes are compared
individually, including alternate release branches and prereleases. Advisory
records, distinct IDs and connected ID/alias groups are separate quantities;
alias grouping is a statement about supplied links, not external identity proof.

This first procedure intentionally requires a compact verbatim source-fact block.
It can falsely reject a correct paraphrase, and it cannot detect every prose
contradiction merely because the block is present. Semantic review still applies.
Malformed/partial recognized bundles cannot pass the source-fact check; unfamiliar
source formats do not acquire a deterministic verification claim. Regression tests
use different package names and cover conflicts, missing lines, markers, alternate
fixes, missing facts, counts, and suppression of failed reflections. Any broader
contract promotion requires fresh outcome evidence; this hand-built procedure is
not evidence of autonomous procedure learning.

The source evaluator's version 0.3.0 also narrows numeric conflict/corroboration:
matching digits cannot supply entity identity, bare JSON fields have no parent
context, and multi-number records require richer interpretation. Existing trace
fields retain their shape. No conflict detected means only that this bounded
heuristic found none; it is not a semantic consistency attestation.

Framing 1.4.0 keeps explicitly accepted proposal conditions in existing
`given`/`constraints` and success criteria. `unknown` continues to drive blocking
acquisition. This is prompt behavior within existing fields, not a new certainty
score or permission to assume environment choices. Execution and unconditional
compatibility claims retain their required observation boundary.

### Residual questions in a completed report

The conclusion capability's optional `report_metadata` starts as experimental
presentation metadata. Its producer is the final checker; its consumers are the
CLI report and persisted session report. It carries at most eight nonempty
questions (500 characters each) in the existing trace surface. The runtime binds
that event to a hash of the final answer, so a later answer cannot silently reuse
old conditions. Invalid or unknown-version metadata is ignored on report reads;
invalid model output is rejected at the model boundary. No canonical gap field,
completion rule, confidence score, or database migration is added.

Passing a conditional proposal does not settle its environmental or feasibility
questions. These questions appear in the existing `open_questions` report field
alongside unfilled gaps, without turning them into blocking gaps. An empty latest
metadata event clears earlier questions. Legacy runs without metadata retain their
original recorded uncertainty; the reader does not invent questions from prose.
Unit and persisted-report tests cover limits, stale answer binding, deduplication,
completed outcomes with questions, and failed outcomes without reused metadata.

### Historical verification after recovery

When a material update invalidates current verification, the kernel emits
`verification_invalidated` with version `verification_history@0.1.0`, the action
identifier and the previous validated `VerificationReport`. This event is audit
metadata, not a new first-class verification contract. Its consumers are the CLI
and persisted report builders. It prevents a recovery stop from erasing the user's
view of earlier failed checks.

Only the latest known-version event can supply historical failure diagnostics,
and only when current verification is absent. The display prefixes every check
and contradiction with "Earlier attempt, before recovery". Invalidated passing
reports and malformed metadata cannot supply fallback checks. Current verification
always wins. Historical content does not change confidence, completion, the final
answer, or learning eligibility. Regression tests cover kernel invalidation,
report precedence, malformed/pass history, and Postgres readback. Legacy runs that
never recorded the event cannot recover lost diagnostics from this mechanism.

### Planner clarification boundary

Experimental `PlanGenerationOutput` now requires exactly one nonempty branch:
up to six existing `PlanTask` objects or up to three clarification questions.
The planner produces this output; its capability adapter consumes questions as an
existing `blocked` observation with `human_input_required`, preserving usage and
the current failed verification. The kernel and durable session adapter already
support this disposition. Questions must ask for evidence the available tools
cannot obtain, not reinterpret a conditional proposal as a demand for execution.
Empty or mixed branches fail output validation. This adds no canonical state
field, engine, score, or permission. Tests cover the plan branch, bounded/mixed
questions, kernel stop, retained diagnostics/resources, and session disposition.

### Online acquisition metadata and recovery

`SearchResponse.metadata` carries provider usage and excerpt-coverage metadata.
OpenRouter server-search candidates come only from URL citation annotations;
model-generated answer text is discarded. The capability records one provider
request (potentially two inference turns), reported search uses, aggregate tokens
and optional reported cost. Failure telemetry marks unknown remote usage explicitly.
An external capability may reserve both model and external calls; deterministic,
human and memory capabilities cannot reserve model calls. These are experimental
capability/acquisition contracts, with no new canonical state field.

Search queries retain declared source requirements. Questions sharing declared
public sources form one gap whose text retains every constituent requirement;
semantic evaluation must support the whole target before closure. Source-grounding
failures reject individual candidates and appear in evaluation metadata, preserving
valid candidates and completed model usage. Distinct pages from one host may enter
evidence, but that host counts only once toward corroboration. Explicit official
source accounts can require one authoritative source; requested independent checks
still require multiple sources. Neither source counting nor lexical grounding is
proof of factual correctness; final conclusion checking remains required.

Human questions for externally acquirable gaps are deferred only after a same-gap
automated action passes capability, privacy, prior-failure and budget gates. Explicit
user-owned clarification is unaffected. Tests include unavailable providers,
exhausted budgets, privacy restrictions, failed searches, rejected access pages,
unsupported extracted claims, query limits and source independence counts.

`EvidenceEvaluationOutput.next_query` is optional and limited to 300 characters.
The evaluator produces it only for unresolved public evidence needs; the query
builder reads the latest evaluation for the same target gap and preserves declared
sources plus the existing 400-character/50-word dispatch limit. Evaluation rationale
and suggested query remain inspectable trace metadata. This adds no model call or
canonical state field. Tests cover omission, oversized output, same-gap isolation
and replayed trace bounds. Source text cannot directly select a runtime action.


### Bounded scope recovery and direct public page reads

`gap_detection_completed.public_question_groups` retains the exact constituent
questions behind an experimental grouped public gap. After unsuccessful public
evaluation with admitted evidence, `scope_reviewer` can propose one bounded reframe
per run. Its experimental output classifies every question index exactly once as
still needed, supported, or nonblocking. Supporting facts require a matching
verbatim excerpt; nonblocking decisions select an index into verbatim user-input
spans, whose original text is retained as provenance. Invalid coverage rejects the
review. Invalid provenance keeps the affected question still needed and records the
rejected proposal without erasing valid classifications for other questions.

The capability produces `CognitiveStateUpdate.superseded_gap_targets`; the kernel
consumes it to remove a replaced gap without falsely marking it filled. This typed
experimental command is necessary because resolved-gap updates have different
semantics. `knowledge_scope_reviewed@0.1.0` archives the original gap, classifications,
rejected proposals and exact scope quotes. Replacement gaps retain required facts;
nonblocking uncertainties become current structured-problem constraints and are
exposed in both report builders. Goals, success criteria and known facts are
preserved. Material updates invalidate earlier verification. Exact provenance
checks do not prove a model's semantic judgment; final verification still checks
the original deliverable. No new canonical state field, database migration or
confidence score is introduced.

`public_page_reader@0.1.1` uses the existing SEARCH action to read one previously
admitted public HTTPS source after an unsuccessful evaluation. At most two distinct
URLs may be attempted per run, inside the existing external-call and candidate
budgets. It stages `EvidenceCandidate.source_type=web_page`; the existing evaluator
applies the same semantic, authority, grounding and independence gates as search
results. The read itself never resolves a gap or adds evidence.

`public_page_read_attempted` records attempted URLs and targets even on expected
failure. Acquisition metadata records response/text hashes, decoded bytes, selected
text offsets, truncation and coverage. Reads validate all DNS answers as public,
pin the connection address, preserve TLS SNI/certificate hostname and HTTP Host,
disable proxies/redirects, and enforce 20 seconds and 2 MB of decoded text/HTML.
A deterministic selector returns at most 9,000 characters from nonoverlapping
passages, preserving document order. No whole-page corpus is persisted. Reused URLs
with new excerpts may add evidence, but never additional independent-source credit.
Offline composition omits this capability; private tasks cannot dispatch it.
After a page evaluation leaves the gap unsupported, the controller returns to
search before another page read can be selected. A newer search batch can enable
another read if budget remains. This prevents measurement pages from consuming
the remaining calls when the missing fact requires finding a different source.

`verification_research@0.1.0` keeps recovery in experimental output and trace
contracts. `ConclusionCheckOutput.public_research_needs` contains at most two
questions (500 characters each), each referencing an existing failed-check index;
a passing verdict cannot contain them. `verification_research_requested` records
the failed report and the corresponding unfilled public-reference gaps. The adapter
admits one research round per run. Acquisition uses existing gates and budgets;
no request itself creates evidence. Material recovery invalidates current
verification while preserving its history. `verification_research_analyzed`
identifies fresh analytic task IDs and prior task IDs; the adapter ensures distinct
IDs and keeps both sets of outputs. The independent checker must use revised
analysis and admitted evidence. No canonical field or database migration is added.
Whether a question truly concerns public knowledge remains a model judgment,
subject to privacy/tool gates; this is not proof of safe semantic classification.

`time_uncertainty_consistency@0.1.0` is a deterministic necessary check on a
proposed passing answer. It parses explicit central-value/uncertainty pairs in
seconds, minutes or hours and converts each quantity independently to seconds.
When an admitted raw excerpt has the same central magnitude, a conflicting error
magnitude rejects the answer and reflection. The trace retains the rejected answer
and mismatch; generated evidence claims cannot corroborate their own unit errors.
Unparsed expressions, non-time dimensions and unmatched central values remain
outside this check. A no-conflict result is not a general measurement attestation.

`knowledge_scope_review@0.2.0` applies source-validated supported dispositions even
when nothing is deferred. It archives the original group, retains supported
questions as filled gaps with evidence references, and batches still-needed
questions into one unfilled residual gap. `residual_target` and
`public_question_groups` trace its lineage. Scope and coverage changes are recorded
separately; the unchanged success criteria still require final verification.

`source_quality_evaluator@0.4.1` optionally emits `ResearchContinuation`, containing
an admitted `source_uri` to read or null to discover a different source, plus a
bounded reason. The adapter rejects nominations outside existing/newly admitted
public evidence and records the rejection without discarding valid evidence.
`public_page_reader@0.2.2` intersects the nomination with its eligible, untried
public URLs; null or ineligible choices return to discovery. An explicit read combines original-user lexical coverage with explicitly named
residual sections; publisher identifiers are excluded from the added hints. Missing hints preserve legacy behavior. Regrouped gaps may
inherit parent query/read guidance, never parent coverage or verification verdicts.
All existing privacy, DNS, source admission and resource gates remain in force.

Generated assessment claims render U+0000 as the visible literal `\u0000` before
admission; source excerpts remain unchanged. The existing trace text sanitizer
uses the same representation so PostgreSQL JSONB can persist summaries and nested
assessment text. This is not secret redaction or inference of a minus/plus-minus
symbol. Raw null characters are not round-trip source provenance. Regression
coverage includes actual database trace and accepted-evidence readback.

The fused conclusion checker (`0.7.2`) owns final-answer composition after checking
substantive findings and references. Prewritten final prose is not a prerequisite;
missing requested analysis, facts or actual execution still reject completion.
Numbered-heading coverage bonuses exclude unnumbered front matter. Passage
coverage remains bounded and cannot establish complete semantic coverage.

### Candidate repair memory experiment

`RepairLesson` is experimental procedural metadata, not a canonical knowledge
claim. Its producer requires a verified/reflected explicit source-check run, a
failing-original/passing-candidate observation, exact source/check hashes and the
hash of the actual patched source. It retains one bounded old/new text pair,
source-session provenance, sandbox version and an integrity digest. The digest
detects accidental mutation; it is not an authenticity signature.

The owner-scoped memory repository stores the lesson in existing procedural
steps with zero verified-procedure successes: one successful edit does not
promote a deployable procedure. Identical versioned edit pairs are deduplicated,
retaining the first provenance. Recall loads at most twenty recent candidates;
exactly one distinct edit may match exactly once in the current admitted source.
Stale, mutated, missing or ambiguous proposals fall back to the ordinary model
route. `source_patch_memory_proposed` identifies the lesson and current artifacts.
It never supplies evidence or resolves a verification criterion.

The proposed edit uses the existing plan/sandbox/verifier path. Source/check
snapshots, consent, budgets and owner isolation remain current-case requirements.
`source_patch_sandbox@0.3.2` rejects modified verifier expectations and records its
fixed four bindings for failed checks too. A failed candidate therefore reaches
the deterministic verifier rather than depending on a model to reject it.
No variable renaming, arbitrary procedure induction or broad semantic equivalence
is established. API source/check sessions use persisted memory; the ordinary CLI
has no automatic repair-memory store in this increment.

Numeric edits can satisfy the same two-term lexical diagnosis check with exact Python
numeric literals, including at sentence endings. Digits within identifiers and
prefixes of other decimal literals do not count. This is relevance checking, not
causal verification; execution against the admitted check remains mandatory.

### Bounded repair recovery metadata

`source_patch_recovery@0.1.0` uses `source_patch_recovery_proposed` trace metadata
for one supersession after a recalled edit fails deterministic verification. The
source-patch adapter produces the complete retired and replacement tasks; the
kernel independently validates the producer, failed state, exact unchanged
source/check/verifier bindings, new task ID and genuinely different candidate
source. Other state changes or injected verdicts invalidate the supersession.
It removes only the retired active task, retains execution/hypothesis history,
and archives failed verification through the existing invalidation mechanism.

The existing proposer (`source_patch_investigator@0.3.0`, context `0.3.0`) receives
the rejected edit and failed checks only during recovery. It cannot edit the
check or publish a verdict. Fresh sandbox execution must revalidate all four
criteria. The verifier (`verifier-factory@0.1.1`) composes the source/check answer
from the verified current task, so multiple historical hypotheses do not suppress
the final answer or cause the wrong edit to become a lesson. No new core field or
database migration is introduced. Supersession is experimental adapter metadata,
not general authority to remove plan tasks.
