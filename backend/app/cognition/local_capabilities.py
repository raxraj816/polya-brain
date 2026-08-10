"""Real deterministic local capabilities for the production cognitive runtime."""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal, DivisionByZero, InvalidOperation

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.graph.state import ExecutionOutput, PolyaState
from app.models.contracts import EvidenceItem, RiskLevel

_ARITHMETIC_PATTERN = re.compile(
    r"^(?:what\s+is\s+)?(?P<left>-?\d+(?:\.\d+)?)\s*"
    r"(?P<operator>[+\-*/])\s*(?P<right>-?\d+(?:\.\d+)?)\s*\??$",
    re.IGNORECASE,
)
_ARITHMETIC_IN_TEXT = re.compile(
    r"(?<![\w.])(?P<left>-?\d+(?:\.\d+)?)\s*"
    r"(?P<operator>[+\-*/×÷])\s*(?P<right>-?\d+(?:\.\d+)?)(?!\d|\.\d)"
)


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal(1)))
    return format(normalized, "f")


def calculate_binary_expression(expression: str) -> tuple[str, str]:
    normalized_expression = expression.replace("×", "*").replace("÷", "/")
    match = _ARITHMETIC_PATTERN.fullmatch(normalized_expression.strip())
    if match is None:
        raise ValueError("calculator accepts one explicit binary arithmetic expression")
    left = Decimal(match.group("left"))
    right = Decimal(match.group("right"))
    operator = match.group("operator")
    try:
        if operator == "+":
            result = left + right
        elif operator == "-":
            result = left - right
        elif operator == "*":
            result = left * right
        else:
            result = left / right
    except (DivisionByZero, InvalidOperation) as exc:
        raise ValueError("calculator expression is undefined") from exc
    canonical = f"{_format_decimal(left)} {operator} {_format_decimal(right)}"
    return canonical, _format_decimal(result)


def _expression_for_action(action: CognitiveActionCandidate, state: PolyaState) -> str:
    if action.action_type is CognitiveActionType.CALCULATE:
        return state["raw_input"]
    task = next((item for item in state["plan"] if item.id == action.target), None)
    if task is None:
        raise ValueError("calculator execution requires a matching plan task")
    candidates = [task.params.get("expression"), task.action, state["raw_input"]]
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        normalized = candidate.replace("×", "*").replace("÷", "/")
        if _ARITHMETIC_PATTERN.fullmatch(normalized.strip()) is not None:
            return normalized
        embedded = _ARITHMETIC_IN_TEXT.search(candidate)
        if embedded is not None:
            operator = embedded.group("operator").replace("×", "*").replace("÷", "/")
            return f"{embedded.group('left')} {operator} {embedded.group('right')}"
    raise ValueError("calculator plan task does not contain a binary arithmetic expression")


def calculator_capability() -> FunctionCapability:
    """Build a no-eval, exact-decimal calculator for acquisition and execution."""
    definition = CapabilityDefinition(
        name="calculator",
        version="decimal_calculator@1.0.0",
        supported_actions={CognitiveActionType.CALCULATE, CognitiveActionType.EXECUTE},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.0,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        expression, result = calculate_binary_expression(_expression_for_action(action, state))
        digest = hashlib.sha256(expression.encode()).hexdigest()[:16]
        claim = f"{expression} = {result}."
        if action.action_type is CognitiveActionType.CALCULATE:
            problem = state["structured_problem"]
            unknowns = list(problem.unknowns) if problem is not None else []
            update = CognitiveStateUpdate(
                knowns_to_add=[claim],
                unknowns_to_resolve=unknowns,
                resolved_gap_targets=[action.target],
            )
        else:
            update = CognitiveStateUpdate(
                execution_outputs_to_add=[
                    ExecutionOutput(
                        task_id=action.target,
                        summary=f"Calculated {claim}",
                        output={"expression": expression, "result": result},
                    )
                ]
            )
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=f"Calculated {claim}",
            evidence=[
                EvidenceItem(
                    source_type="deterministic_calculator",
                    source_uri=f"calculator://{digest}/{action.id}",
                    claim=claim,
                    raw_excerpt=claim,
                    reliability_score=1.0,
                    relevance_score=1.0,
                )
            ],
            proposed_update=update,
        )

    return FunctionCapability(definition, execute)


def human_input_capability() -> FunctionCapability:
    """Pause safely when only the user can supply the missing observation."""
    definition = CapabilityDefinition(
        name="human_input",
        version="human_input@1.0.0",
        supported_actions={CognitiveActionType.CLARIFY, CognitiveActionType.ASK_HUMAN},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.05,
    )

    def execute(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.BLOCKED,
            summary="A user-owned observation is required before continuing.",
            proposed_update=CognitiveStateUpdate(
                questions_to_ask=[f"Please provide the missing information: {action.target}"]
            ),
            failure_kind="human_input_required",
        )

    return FunctionCapability(definition, execute)
