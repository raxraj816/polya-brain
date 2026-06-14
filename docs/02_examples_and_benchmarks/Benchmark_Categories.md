# Benchmark Categories

This document defines the active mixed-domain benchmark surface for PolyaBrain.

Source of truth: `../../PolyaBrain_Product_Implementation_Master_Plan.md`

## Purpose

PolyaBrain must be tested as a general problem-solving system from Chapter 1. Benchmarks must prove the same core loop works across different problem types without hardcoding the core platform to one domain.

Each benchmark case should include:

- Problem statement.
- Category.
- Difficulty.
- Allowed tools.
- Expected behavior.
- Ground truth or reference answer.
- Expected clarifying questions, when relevant.
- Expected verification checks.
- Scoring rubric.

## Categories

1. Mathematical reasoning: word problems, optimization, algebra, probability, and constraints.
2. Logic and puzzle solving: deduction, contradiction detection, and grid-style reasoning.
3. Technical research: current APIs, libraries, papers, standards, and evolving technology questions.
4. Software debugging: codebase investigation, failing tests, root-cause analysis, and patch planning.
5. Algorithmic problem solving and coding contests: LeetCode, HackerRank, Codeforces, and Advent of Code-style problems.
6. Data analysis: CSV/table interpretation, anomaly explanation, comparison, and segmentation.
7. Planning and strategy: project planning, tradeoff analysis, and implementation sequencing.
8. Scientific/engineering reasoning: hypothesis generation, experiment design, and evidence evaluation.
9. Ambiguous or underspecified problems: cases where the correct behavior is to ask clarifying questions.
10. Adversarial or misleading problems: cases with false assumptions, bad evidence, or contradictions.
11. Open-ended creative synthesis: generate several possible approaches and verify feasibility.

## Scoring Dimensions

- Outcome correctness.
- Constraint handling.
- Knowledge gap quality.
- Evidence quality.
- Tool selection quality.
- Verification completeness.
- Correct clarification or abstention behavior.
- Report usefulness.
- Latency.
- Estimated cost.

## Chapter 60 Minimum

- At least 30 evaluation cases run automatically.
- At least one full end-to-end case succeeds in math, research, debugging, data analysis, planning, and ambiguous input.
- At least 20 general reasoning smoke cases run through the same core loop.
- Every answer includes evidence, checks, confidence, and open questions.

## Chapter 90 Minimum

- At least 100 synthetic and curated scenarios across benchmark categories.
- At least 70% correct or usefully verified outcome on solvable cases.
- At least 90% correct clarification or escalation behavior on underspecified cases.
- At least 90% reports include required audit sections.

## Guardrail

Do not optimize only for impressive demos. Benchmark repeatability is a product requirement.
