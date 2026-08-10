# General Cognitive Kernel

Status: active architecture boundary for Chapter 13-C.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Product Boundary

PolyaBrain is a domain-independent problem-solving control system. Models,
search, memory, code, calculators, databases, simulators, documents, APIs, and
human input are capabilities chosen by the kernel. No capability owns the run.

The first technical-investigation workflow is an executable proof surface. It
must not place incident-specific concepts or routes in the cognitive kernel.

## Cognitive Cycle

```text
observe -> orient -> identify obstacle -> generate actions -> select action
        -> execute capability -> interpret observation -> update state
        -> verify -> continue | backtrack | reframe | ask | stop
        -> reflect and learn
```

The cycle is state-dependent. A fixed sequence of prompts is not an
implementation of this architecture.

## Universal Action Families

### Understanding

- interpret
- clarify
- reframe
- decompose
- identify assumptions
- identify constraints
- detect contradictions

### Knowledge acquisition

- recall
- retrieve memory
- search
- ask a human
- inspect a source
- observe
- measure

### Reasoning

- infer
- calculate
- estimate
- compare
- generate hypotheses
- reason by analogy
- reason from first principles

### Experiment and execution

- simulate
- experiment
- reproduce
- execute
- monitor

### Control and learning

- plan
- verify
- retry
- backtrack
- replan
- defer
- stop
- reflect

This taxonomy begins as an experimental internal model. Action values graduate
to core contracts only after cross-domain evaluations establish stable
producers, consumers, and verification paths.

## Action Candidate

Each candidate must make the proposed control decision inspectable:

- action type
- target goal, obstacle, gap, or hypothesis
- purpose
- expected observation
- hypotheses or alternatives it could distinguish
- expected usefulness or information gain
- estimated cost
- risk
- required capability
- success condition
- failure condition

Action scores are comparative decision aids, not truth or confidence scores.
The controller must remain able to reject every candidate and stop safely.

## Capability Boundary

A capability definition declares:

- stable name and version
- supported action types
- input and output schemas
- risk and approval requirements
- timeout and cost estimates
- executor
- result verifier where available

Capabilities return observations. They do not directly mark hypotheses as
verified, write semantic memory, or finalize a session.

The persisted runtime exposes the Chapter 13 Problem Representation Engine as
the `interpret` capability and Chapter 14 as `discover_constraints`.
`CognitiveRuntime` creates initial state from raw input, the controller selects
capabilities, and the kernel applies only validated observations or pauses for
clarification. The minimum production suite includes gap detection, hypothesis,
planning, analytic execution, verification, reflection, exact local arithmetic,
and human input. Accepted state artifacts are persisted and exposed through the
session report API. Search, local artifact inspection, measurement, simulation,
and experiment remain later production capability gates.

## Controller Responsibilities

The controller:

1. Reads the canonical `PolyaState`.
2. Identifies the current obstacle to progress.
3. Generates candidates using deterministic policy, procedural memory, and
   optional model proposals.
4. Rejects candidates that violate constraints, permissions, risk limits, or
   available capabilities.
5. Selects a bounded next action using expected usefulness, cost, and risk.
6. Records selected and rejected candidates in sanitized trace metadata.
7. Executes only through the capability registry.
8. Passes the resulting observation to evidence/state update logic.
9. Requires verification before accepting a solution.
10. Stops on budget exhaustion, repeated non-progress, unsafe actions, or
    insufficient evidence.

## Initial Deterministic Policy

The Chapter 13-C proof uses explicit rules before any learned controller:

```text
ambiguous goal or required user-owned value -> clarify
missing external fact -> search or inspect an authoritative source
missing derived value -> calculate
multiple live explanations -> run a discriminating observation or experiment
failed action -> inspect failure, choose an alternative, or backtrack
candidate conclusion -> verify independently
verified outcome -> reflect
no safe useful action -> stop with insufficient evidence
```

Optional model proposals may expand the candidate set. They are schema-checked
and compete with deterministic candidates under the same policy.

## Cross-Domain Generality Gate

The same controller must be evaluated on interactive cases from mathematics,
logic, technical research, software debugging, data analysis, planning,
scientific reasoning, ambiguous input, adversarial input, and creative
synthesis. Domain packs may provide tools and verification procedures, but may
not choose graph routes directly.

Each case should require an action that cannot be replaced by recalling a
memorized answer. The comparison baseline receives the same model, artifacts,
tools, and budgets.

## Failure Modes And Guardrails

- **Prompt pipeline masquerading as cognition:** decision ownership and routing
  remain outside model prompts.
- **Decorative tool use:** every action targets an explicit obstacle and states
  the expected observation.
- **Tool output treated as truth:** observations require provenance and
  verification before belief updates.
- **Score theater:** scores only rank candidates and are evaluated against
  action-choice outcomes.
- **Domain leakage:** core controller tests fail if a domain pack changes its
  routing directly.
- **Infinite investigation:** iteration, cost, time, and repeated-action budgets
  force recovery or safe stop.
- **Memory poisoning:** only validated outcomes can update durable semantic or
  procedural memory.
- **False generality:** evaluation reports results separately by category and
  records unsupported categories explicitly.

## Promotion Gate

Experimental cognitive-action models may become core contracts only after they
show:

1. A stable producer and consumer.
2. Cross-domain usefulness.
3. Deterministic validation.
4. A measured effect on action quality or solved outcomes.
5. Known misuse and failure behavior.
6. A reason trace metadata is no longer sufficient.
