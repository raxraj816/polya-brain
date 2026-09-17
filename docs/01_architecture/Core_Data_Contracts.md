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
