# Problem Understanding Prompt Changelog

Prompt behavior is versioned in code so benchmark and trace results can identify
the exact instruction contract that produced them.

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
