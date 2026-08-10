# ADR 0001: PolyaBrain Owns The General Cognitive Control Loop

Status: Accepted

## Context

The existing modular engine architecture contains the state needed for a Pólya
loop, but a fixed sequence of engines can accidentally make an LLM prompt chain
the real controller. The product vision requires PolyaBrain to decide what to do
next and to use models and tools only as capabilities.

## Decision

Add a domain-independent cognitive controller over canonical `PolyaState`.

The controller generates, validates, ranks, and selects cognitive actions from
the current goal, gaps, hypotheses, evidence, constraints, failure history,
budgets, and declared capabilities. Capabilities return typed observations and
proposed state updates. They cannot directly verify a conclusion, finalize a
run, or write durable learned knowledge.

The cognitive-action taxonomy remains experimental until cross-domain evals
satisfy the core contract promotion rule.

## Consequences

- The same controller can be tested with different tools and domain packs.
- Model providers remain replaceable.
- Action decisions and rejected alternatives become auditable.
- Additional controller and capability failure modes require bounded recovery,
  cost, risk, approval, and non-progress guards.
- Fixed graph stages remain useful implementation modules but are subordinate to
  controller routing.

## Rejected Alternatives

- Let each engine advance to the next fixed stage.
- Let an LLM choose and execute arbitrary tools directly.
- Promote a permanent action score or large action schema before evaluation.
- Create domain-specific controllers inside use-case packs.

## Verification

- Cross-domain action-choice tests.
- Failed-action recovery tests.
- Capability availability, approval, and exception tests.
- Completed status only after verification and reflection.
- Offline structural proof across active benchmark categories.
- Required live comparison with a tool-enabled direct-model baseline.
