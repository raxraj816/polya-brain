# Problem Understanding Prompt Changelog

Prompt behavior is versioned in code so benchmark and trace results can identify
the exact instruction contract that produced them.

## `problem_understanding@1.5.1` - Chapter 13-P

- Retain all ten validated examples. Omit only example values that reconstruct
  exactly from contract defaults; compact JSON separators in input and schema.
- Preserve all rules, schema constraints, source content, and output limits.
  Pair with representation 1.4.0 and repair prompt 1.1.0 for versioned identity.
- An unreleased 1.5.0 experiment included only three boundary examples. Reject it:
  four live fixture modes changed and three fixtures added clarification stops.
- Ten same-model compatibility calls preserved expected mode, clarification,
  explicit override, and warning behavior with 32,594 input tokens versus 36,835
  previously. These are visible prompt fixtures, not independent quality proof.

## `cognitive_capability@0.5.0` - Chapter 13-P

- Compact JSON whitespace in initial and repair schemas/payloads while preserving
  every decoded value. No evidence or verification stage is removed.
- Whole-run savings are not guaranteed: output lengths and recovery paths vary.

## `problem_understanding@1.3.0` - Chapter 13-P

- Preserve whether the requested deliverable is a proposal or an implemented
  outcome. Future test plans are not silently promoted to required execution now.
- Deliberation and conclusion-check prompts require actual analytic findings and
  factual coverage while keeping unsupported execution claims forbidden.

## `problem_understanding@1.2.0` - Chapter 13-P

- Omit temperature from default structured calls and repairs. Models that do not
  support sampling temperature can now satisfy strict provider parameter routing.
- Preserve explicitly configured sampling values at the provider boundary.
- Pair with `cognitive_capability@0.4.0` and `semantic-route-broker@0.2.0` so prior
  route-performance records are not silently reused across the request change.

## `problem_understanding@1.1.0` - Chapter 13-P

- Keep initial framing concise and avoid solving the investigation during framing.
- Use a 3,000-token response allowance under the shared runtime budget.
- Preserve user-supplied quoted artifact references alongside model-produced sources.
- Restrict deterministic fact lookup to one artifact and ignore its path when
  classifying lookup intent; multi-file synthesis uses semantic framing.
- These repairs follow failed production CLI dogfood runs. They do not establish
  a product-value or competitive win.

## `problem_understanding@1.0.0` - 2026-08-09

- Added strict JSON-schema output generated from `ProblemUnderstandingOutput`.
- Added explicit Polya fields for given information, unknowns, constraints, the
  goal, and success criteria.
- Added literal, deeper, and wrong-problem framing.
- Added existing-mode inference, user override preservation, confidence,
  rationale, and clarification routing.
- Added ten validated examples spanning all Chapter 11 categories.
- Added anti-fabrication, minimal-state, and no-chain-of-thought instructions.

## `problem_understanding_repair@1.0.0` - 2026-08-09

- Added JSON-only repair against the same strict output schema.
- Marked invalid model output as untrusted data.
- Limited repair to syntax and schema correction without adding facts.
- Paired the prompt with a bounded parser retry policy and sanitized failures.

## `fused_deliberator@0.6.0` / `fused_conclusion_checker@0.5.0` - Chapter 13-P

- Supply deterministic dependency source facts as bounded context for relevant
  constraint investigations. Preserve current requirements, actual installed
  parent links, alternative listed fix versions, and distinct counting units.
- Require a verbatim source-fact block before a passing answer can be retained.
  Failed coverage prevents a verified reflection, while model usage is retained.
- Keep semantic falsification separate: copied facts do not prove that surrounding
  prose is correct. The temporary prior experiment used deliberator 0.5.0,
  checker 0.4.0, and source facts 0.1.0 (constraints only); it repaired two errors
  but still passed an incorrect advisory count. Its failed run is preserved.

## `source_quality_evaluator@0.3.0` - Chapter 13-P

- Numeric contradiction/corroboration now requires a matching anchored subject;
  overlapping digits from different package versions do not establish one.
- Bare JSON fields and records with multiple numeric qualifiers remain outside
  the heuristic's proof scope. Semantic evaluation still needs to distinguish
  entity, property, units and context.

## `problem_understanding@1.4.0` - Chapter 13-P

- Distinguish facts blocking the requested answer from missing environment choices
  that the user explicitly permits a conditional proposal to carry as conditions.
- Keep those acknowledged missing choices in given/constraints and require future
  checks. Continue investigating unknown facts in supplied artifacts.
- Preserve clarification for ambiguous objectives and execution evidence for an
  implemented/tested or unconditional outcome. Pair with representation 1.3.0.

## `fused_conclusion_checker@0.6.0` - Chapter 13-P

- Preserve remaining nonblocking questions in optional report metadata after a
  conditional proposal passes its stated criteria. Keep questions consistent with
  the final answer and distinct from claims of execution or verified facts.
- The runtime binds those questions to the exact answer in a trace event consumed
  by both report paths. Canonical gaps and completion behavior are unchanged.
