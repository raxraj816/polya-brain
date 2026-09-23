# PolyaBrain Cognitive Product Doctrine

Purpose: define how PolyaBrain should use ideas from brain science, human intelligence, cognition, and problem solving while becoming a real product.

This document is a product and engineering doctrine, not a neuroscience claim. It exists to guide implementation decisions.

## Core Position

PolyaBrain should be brain-inspired, not brain-simulating.

The goal is not to recreate the biological brain. The goal is to convert useful principles from human intelligence into reliable software behavior.

PolyaBrain itself is the problem-solving control system. It owns the goal,
working state, knowledge gaps, action selection, belief updates, verification,
recovery, stopping, reflection, and learning. An LLM is a replaceable capability
for language interpretation, candidate generation, or synthesis; it is not the
brain and does not own the control loop. The same subordinate relationship
applies to search, code execution, calculators, databases, simulators, APIs,
documents, and human input.

Every capability result enters the system as an observation. It becomes trusted
knowledge only after provenance, relevance, consistency, independence, and the
problem's verification requirements have been evaluated.

PolyaBrain should therefore ask:

```text
Which cognitive principle helps the system solve real problems better?
How can that principle become a concrete product mechanism?
How can the mechanism be tested, inspected, and improved?
```

## Product Definition

PolyaBrain is a brain-inspired problem-solving intelligence system.

For the person using it, PolyaBrain is a cognitive workbench that helps them
understand, investigate, solve, verify, and learn from difficult problems.
It should make reasoning visible, evidence inspectable, uncertainty explicit,
resource use auditable, and learning reusable.

The statements above define the product purpose and human experience. The
binding architecture that delivers them is:

The binding definition is:

```text
PolyaBrain is a product-first, initially cloud-hosted, model-agnostic Cognitive
Runtime that turns difficult objectives into verified outcomes by acquiring
knowledge on demand, using deterministic procedures whenever possible, invoking
bounded model reasoning when necessary, and learning reusable procedures from
verified work.
```

The initial user-facing product is PolyaBrain Investigator, a verified technical
problem-solving workbench. The Cognitive Runtime is the enduring intelligence
core. Cloud is the initial delivery model, not a dependency of the intelligence.
Language models are replaceable semantic processors. “Intelligence OS” is an
eventual platform category that must be earned through dependent applications,
developers, and cross-domain proof.

The unit of value is a verified problem outcome, not a chat response.

General-purpose intelligence is the architectural ambition, not the initial
market category or an unearned superiority claim.

## Invention And Winning Doctrine

PolyaBrain may invent a new algorithm, representation, verifier, procedure
language, memory mechanism, small specialized model, or infrastructure component
when a measured product limitation requires it. Experimental intelligence must
begin in prompts, metadata, traces, optional capabilities, research, or evals and
earn promotion into core contracts.

The primary optimization target is verified useful outcomes per unit of money,
time, tokens, compute, risk, and human attention. A problem category is won only
through repeated held-out evidence against strong practical baselines, including
outcome quality, unsupported conclusions, total resource cost, transfer savings,
and whether real users choose to return with another difficult problem.

## Research-To-Product Rule

Every cognitive idea must map to an implementation surface.

| Cognitive idea | Product mechanism |
|---|---|
| Working memory | Explicit problem state, active context, and scratchpad |
| Attention | Focus selection: what matters next in this run |
| Semantic memory | Knowledge chunks, concepts, facts, and embeddings |
| Episodic memory | Past problem sessions, traces, outcomes, and lessons |
| Procedural memory | Strategies, methods, playbooks, and tool-use patterns |
| Metacognition | Knowledge-gap detection, confidence, uncertainty, and "do I know enough?" checks |
| Curiosity | Research planning and information acquisition when gaps are detected |
| Problem decomposition | Subproblems, constraints, assumptions, and dependency structure |
| Problem reframing | Literal framing, deeper framing, and wrong-problem warnings |
| Approach selection | Choose the product mode, problem type, and playbook before planning |
| Hypothesis generation | Candidate explanations, solution paths, and competing plans |
| Divergent thinking | Generate multiple meaningfully different hypotheses before ranking |
| Convergent thinking | Filter hypotheses against evidence, constraints, feasibility, and verification cost |
| Analogical transfer | Retrieve structurally similar cases and state what pattern transfers |
| Incubation | Run a bounded reframe pass after evidence gathering, then verify anything it changes |
| Network switching | Trace-visible reasoning modes such as explore, compare, verify, reframe, and reflect |
| Verification | Mode-specific checklists, tests, contradiction search, source evaluation, and constraint checks |
| Reflection | Post-run analysis, strategy scoring, and memory updates |

If a research idea cannot become a useful product behavior, defer it.

## Implementation Principles

1. Build a useful problem-solving loop before building a complete intelligence theory.
2. Prefer observable cognitive behavior over hidden cleverness.
3. Treat missing knowledge as a first-class state, not an error.
4. Preserve uncertainty instead of forcing premature answers.
5. Separate evidence, assumptions, hypotheses, actions, verification, and conclusions.
6. Make every important reasoning step auditable.
7. Learn from completed cases, but do not let memory replace verification.
8. Generate diverse possibilities before selecting the best-supported one.
9. Use analogy to find transferable structure, not to bypass evidence.
10. Keep the MVP modular in code and simple in deployment.
11. Use research to sharpen product behavior, not to expand scope without evidence.
12. Measure usefulness through solved problems, user trust, and repeatable evaluations.
13. Select actions from explicit state; do not hide the control policy inside a model prompt.
14. Treat tool and model outputs as observations, not conclusions.
15. Choose information-gathering actions for their ability to resolve important uncertainty.
16. Preserve competing hypotheses until evidence or verification accepts, rejects, or defers them.
17. Demonstrate generality with one cognitive kernel across different domains.

## MVP Boundary

The MVP should not try to become a full artificial brain.

The MVP should implement the smallest useful cognitive loop:

```text
Problem input
  -> representation
  -> constraints
  -> knowledge gaps
  -> research or tool use
  -> evidence evaluation
  -> hypotheses
  -> plan
  -> execution
  -> verification
  -> reflection
  -> auditable report
```

This loop is the product foundation.

## Role For The Builder

When implementing PolyaBrain, assume the role:

```text
Acting Founding CTO + Cognitive Systems Architect + Principal Product Engineer.
```

This means:

- Protect the core vision.
- Reduce scope aggressively for each milestone.
- Translate cognitive science into testable product mechanisms.
- Build working software before theoretical completeness.
- Keep product usefulness, trust, and auditability above architectural ambition.

## Decision Test

Before adding a feature, engine, memory structure, prompt, agent behavior, or research concept, ask:

1. Does this help a user solve a real difficult problem?
2. Does this improve understanding, planning, evidence quality, verification, or learning?
3. Can the behavior be inspected in the trace?
4. Can it be tested against benchmark cases?
5. Is it necessary for the current milestone?

If the answer is no, defer it.

Before adding a core contract field, score, ranking signal, or permanent engine output, also ask:

1. Who produces it?
2. Who consumes it?
3. How does it improve user trust, correctness, verification, or learning?
4. How can misuse harm confidence, ranking, safety, or product clarity?
5. Why can it not start as prompt behavior, optional metadata, trace detail, research note, or eval metric?

If those answers are weak, keep the idea outside the core contract until evals prove it belongs.

## Anti-Goals

Do not let PolyaBrain become:

- A generic chatbot with extra terminology.
- A neuroscience simulation project.
- A creativity-themed product that rewards novelty without verification.
- A product UI that uses brain-region labels as decoration.
- A research notebook without a usable product.
- A collection of agents without a coherent problem-solving loop.
- A memory system that retrieves confidently but verifies weakly.
- A product that hides reasoning from the user.

## North Star

PolyaBrain should help users become better problem solvers.

It should not merely answer. It should help understand, investigate, verify, and learn.

### Product identity and workflow scope

PolyaBrain is the product identity. Investigator describes the first verifiable
workflow, not the boundary of its ambition. The enduring loop must support
recognizing missing knowledge or skills, acquiring what is needed, acting through
available capabilities, checking outcomes and retaining verified procedures.
“Your physical brain” is a founder aspiration for a personal, capable system;
it is not a current claim of embodiment or human-equivalent general ability.
