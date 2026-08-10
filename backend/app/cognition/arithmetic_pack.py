"""Deterministic cognitive procedures for fully specified binary arithmetic."""

from __future__ import annotations

from decimal import Decimal

from app.cognition.local_capabilities import calculate_binary_expression
from app.cognition.model_contracts import (
    GapDetectionOutput,
    HypothesisGenerationOutput,
    PlanGenerationOutput,
    ReflectionCapabilityOutput,
    VerificationCapabilityOutput,
)
from app.graph.state import PolyaState
from app.models.contracts import (
    Hypothesis,
    HypothesisOrigin,
    KnowledgeGap,
    PlanTask,
    PriorityLevel,
    Reflection,
    RiskLevel,
    VerificationReport,
)


def is_simple_arithmetic(state: PolyaState) -> bool:
    problem = state["structured_problem"]
    return problem is not None and problem.problem_type == "simple_arithmetic"


def arithmetic_gap_output(state: PolyaState) -> GapDetectionOutput:
    problem = state["structured_problem"]
    if problem is None:
        raise ValueError("arithmetic gap detection requires a structured problem")
    gaps = []
    if problem.unknowns:
        gaps.append(
            KnowledgeGap(
                description=problem.unknowns[0],
                gap_type="numeric_computation",
                priority=PriorityLevel.CRITICAL,
                why_needed="The exact value is required before the result can be verified.",
                suggested_source="calculator",
            )
        )
    return GapDetectionOutput(
        gaps=gaps,
        rationale=(
            "The binary expression has one exact derived value."
            if gaps
            else "The exact derived value is already recorded."
        ),
    )


def arithmetic_hypothesis_output(state: PolyaState) -> HypothesisGenerationOutput:
    expression, result = calculate_binary_expression(state["raw_input"])
    claim = f"{expression} = {result}."
    if not any(item.claim == claim for item in state["evidence"]):
        raise ValueError("arithmetic hypothesis requires calculator evidence")
    return HypothesisGenerationOutput(
        hypotheses=[
            Hypothesis(
                statement=claim,
                mechanism="Apply the stated operator using exact decimal arithmetic.",
                origin=HypothesisOrigin.DIRECT_REASONING,
                expected_signals=[f"A repeated calculation returns {result}."],
                evidence_for=[item.source_uri or item.claim for item in state["evidence"]],
                verification_checks=[f"Recalculate {expression}."],
                falsification_criteria=[f"A valid exact calculation differs from {result}."],
            )
        ]
    )


def arithmetic_plan_output(state: PolyaState) -> PlanGenerationOutput:
    expression, result = calculate_binary_expression(state["raw_input"])
    return PlanGenerationOutput(
        tasks=[
            PlanTask(
                id="independent-recalculation",
                action=f"Recalculate {expression} and compare the exact result.",
                tool_name="calculator",
                params={"expression": expression},
                expected_output=result,
                risk_level=RiskLevel.LOW,
            )
        ]
    )


def arithmetic_verification_output(state: PolyaState) -> VerificationCapabilityOutput:
    problem = state["structured_problem"]
    if problem is None:
        raise ValueError("arithmetic verification requires a structured problem")
    expression, expected = calculate_binary_expression(state["raw_input"])
    observed_results = [
        output.output.get("result")
        for output in state["execution_outputs"]
        if isinstance(output.output, dict)
    ]
    calculator_claim = f"{expression} = {expected}."
    evidence_matches = any(item.claim == calculator_claim for item in state["evidence"])
    execution_matches = expected in observed_results
    left_text, operator, right_text = expression.split()
    left = Decimal(left_text)
    right = Decimal(right_text)
    result = Decimal(expected)
    if operator == "+":
        inverse_identity_matches = result - right == left
    elif operator == "-":
        inverse_identity_matches = result + right == left
    elif operator == "*" and right != 0:
        inverse_identity_matches = result / right == left
    elif operator == "*":
        inverse_identity_matches = result == 0 and (left == 0 or right == 0)
    else:
        inverse_identity_matches = result * right == left
    passed = evidence_matches and execution_matches and inverse_identity_matches
    checks = [
        f"Checked criterion {index + 1}: {criterion} against calculator evidence, "
        "the planned recalculation, and the inverse arithmetic identity."
        for index, criterion in enumerate(problem.success_criteria)
    ] or ["Compared exact calculator evidence with the planned recalculation."]
    failures = []
    if not evidence_matches:
        failures.append("No exact calculator evidence supports the candidate result.")
    if not execution_matches:
        failures.append("The planned recalculation did not reproduce the candidate result.")
    if not inverse_identity_matches:
        failures.append("The candidate result failed the inverse arithmetic identity check.")
    return VerificationCapabilityOutput(
        report=VerificationReport(
            passed=passed,
            checks_run=checks,
            failed_checks=failures,
            confidence_delta=0.2 if passed else -0.5,
            recommended_route="finalize" if passed else "replan",
        ),
        final_answer=calculator_claim if passed else None,
    )


def arithmetic_reflection_output(state: PolyaState) -> ReflectionCapabilityOutput:
    expression, result = calculate_binary_expression(state["raw_input"])
    return ReflectionCapabilityOutput(
        reflection=Reflection(
            outcome_summary=f"Calculated and verified that {expression} = {result}.",
            what_worked=["Used an exact local calculator and repeated the calculation."],
            reusable_lessons=[
                "Use deterministic procedures instead of a language model for exact arithmetic."
            ],
            strategy_notes=["calculate_then_recalculate"],
        )
    )
