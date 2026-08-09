# Chapter 11: Prompt And Parser Design

Status: complete on `feature/chapter-11-prompt-parser`.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Purpose

Chapter 11 creates a versioned, provider-neutral boundary that turns raw problem
input into validated problem understanding. It proves the prompt, schema,
parser, bounded repair path, and canonical contract mapping before Chapter 13
places that behavior inside a graph engine.

This chapter does not add a new core contract. Experimental framing and mode
selection fields remain at the prompt boundary; only the existing Chapter 5
`StructuredProblem` fields are promoted into graph-ready product data.

## Implemented Boundary

- Versioned problem-understanding and repair prompts.
- Strict JSON schema generated from a Pydantic v2 output model.
- Explicit Polya fields: `given`, `unknown`, `constraints`, `goal`, and
  `success_criteria`.
- Literal framing, deeper framing, and an optional wrong-problem warning.
- Selection among the existing `investigate`, `compare`, `review`, and
  `explore` modes.
- User mode-override preservation, selection rationale, confidence, and
  clarification routing below the `0.65` confidence threshold.
- Input formatting from the minimum required `PolyaState` fields, excluding
  session identifiers and trace content.
- Deterministic local JSON repairs for Markdown fences, surrounding prose, and
  trailing commas.
- At most two configurable LLM repair attempts, with one attempt by default.
- Sanitized parser and client failures that do not echo raw model responses.
- Usage, response identifier, repair-count, and local-repair audit metadata.
- Mapping into the existing Chapter 5 `StructuredProblem` contract.

## Data Flow

```text
PolyaState + optional user hints
  -> versioned JSON-mode request
  -> provider-neutral LLM client
  -> local JSON normalization
  -> strict Pydantic validation
  -> bounded LLM repair when needed
  -> ProblemUnderstandingOutput
  -> existing StructuredProblem contract
```

Every invalid path either returns a validated object, requests clarification
through structured fields, or stops with a typed malformed-response error.
Weak output does not silently continue.

## Output Contract

The prompt-layer result contains:

- `literal_framing`
- `deeper_framing`
- `wrong_problem_warning`
- `goal`
- `problem_type`
- `domain`
- `selected_mode`
- `mode_confidence`
- `mode_selection_reason`
- `needs_clarification`
- `clarifying_questions`
- `given`
- `unknown`
- `constraints`
- `success_criteria`
- `affected_entities`
- `time_window`
- `required_data_sources`

The contract rejects additional fields. Low-confidence mode selection requires
clarification, clarification requires focused questions, and every valid result
requires at least one testable success criterion.

## Prompt And Repair Guardrails

- The model must return one JSON object with no Markdown or chain-of-thought.
- Explicit user facts and inferred or missing facts remain separate.
- The prompt must not fabricate evidence, measurements, entities, dates, or
  sources.
- A supplied mode is a user override and must be preserved.
- The repair prompt treats the invalid response as untrusted data and may only
  correct syntax or schema violations.
- Repair is bounded; exhaustion stops safely rather than forwarding malformed
  output.

## Local Examples

The prompt and proof script cover exactly the ten required categories:

1. Math.
2. Logic.
3. Software debugging.
4. Technical research.
5. Data analysis.
6. Planning.
7. Scientific reasoning.
8. Ambiguous input.
9. Low-confidence mode selection.
10. Wrong-problem framing.

Run the executable chapter gate with:

```bash
make chapter11-proof
```

The verifier sends every local example through the fake LLM client, parser,
contract validation, mode-override check, and `StructuredProblem` mapping. The
default test suite additionally exercises local repairs, bounded LLM repair,
repair exhaustion, secret-safe errors, usage aggregation, and unsupported JSON
mode.

## Deferred Work

- Chapter 12-B implements the first production provider adapter.
- Chapter 13 wraps this boundary in the Problem Representation Engine, emits
  graph trace events, updates `structured_problem`, and persists validated
  canonical output.
- Chapter 15 owns the user-facing clarifying-question loop.

These deferrals keep Chapter 11 independently testable without network access,
database writes, or premature changes to core contracts.
