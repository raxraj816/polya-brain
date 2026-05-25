# Additional Polya Loop Examples

These examples complement `Problem_Solving_Examples.md` and cover benchmark categories needed for implementation.

## Algorithmic Problem Solving

Problem: Given an array of integers and a target, return indices of two numbers that sum to the target.

Expected Polya loop:

- Understand: parse input/output format, constraints, duplicate behavior, and required complexity.
- Knowledge gaps: ask or infer whether exactly one answer exists and whether indices are zero-based.
- Plan: compare brute force and hash-map strategy.
- Execute: implement hash-map solution.
- Verify: run sample tests, edge cases, and a brute-force cross-check on random small arrays.
- Reflect: store the heuristic that hash maps convert pair-sum lookup from quadratic to linear time.

## Data Analysis

Problem: A table shows weekly signups, activation rate, marketing spend, and error rate. Explain why activated users dropped.

Expected Polya loop:

- Understand: identify target metric, time window, available columns, and possible confounders.
- Knowledge gaps: ask for baseline period if missing.
- Plan: compare segments and check correlation with spend and errors.
- Execute: compute deltas, ratios, and segment-level changes.
- Verify: ensure totals reconcile and do not infer causation without evidence.
- Reflect: store a reusable anomaly-analysis strategy.

## Ambiguous Problem

Problem: "Can you improve our onboarding?"

Expected Polya loop:

- Understand: detect that the objective is underspecified.
- Knowledge gaps: ask what product, audience, current funnel, success metric, constraints, and available data exist.
- Plan: do not produce a final recommendation until minimum context exists.
- Verify: confirm proposed next steps answer the user's actual goal.
- Reflect: store the clarification pattern for vague product-improvement requests.

## Adversarial Or Misleading Problem

Problem: "Our conversion rate fell because the new homepage is bad. Prove it."

Expected Polya loop:

- Understand: detect biased framing and unproven causal claim.
- Knowledge gaps: ask for timeline, traffic mix, experiment data, acquisition changes, outages, and seasonality.
- Plan: test multiple hypotheses instead of accepting the user's premise.
- Execute: compare pre/post metrics and alternative explanations.
- Verify: report evidence for and against the homepage hypothesis.
- Reflect: store a strategy for resisting leading assumptions.

## Scientific Or Engineering Reasoning

Problem: A prototype battery overheats during fast charging. Propose likely causes and tests.

Expected Polya loop:

- Understand: identify observed failure, operating conditions, constraints, and safety limits.
- Knowledge gaps: request temperature curves, charge rate, cell chemistry, pack design, cooling design, and failure logs.
- Plan: generate hypotheses such as internal resistance, cooling insufficiency, sensor error, or control algorithm issue.
- Execute: design safe measurements and simulations.
- Verify: map each test to the hypothesis it can confirm or reject.
- Reflect: store the experiment-design pattern.

## Planning And Strategy

Problem: Plan the first 30 days of implementation for a complex AI system.

Expected Polya loop:

- Understand: identify desired outcome, team size, constraints, and non-goals.
- Knowledge gaps: clarify available engineers, budget, and infrastructure.
- Plan: sequence foundation, contracts, tests, and first end-to-end slice before polish.
- Execute: produce a dependency-aware task plan.
- Verify: check for missing prerequisites and measurable exit criteria.
- Reflect: store the planning heuristic that a thin vertical slice should appear early.

## Creative Synthesis

Problem: Generate three product ideas that use the PolyaBrain core loop for education.

Expected Polya loop:

- Understand: identify target audience and learning context.
- Knowledge gaps: ask whether the goal is K-12, college, professional, or self-learning.
- Plan: generate multiple distinct ideas and evaluation criteria.
- Execute: describe each idea with workflow, user value, and feasibility.
- Verify: compare ideas against constraints and implementation cost.
- Reflect: store reusable ideation and feasibility-scoring patterns.
