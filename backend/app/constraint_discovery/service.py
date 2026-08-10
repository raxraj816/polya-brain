"""Deterministic explicit and implicit constraint discovery."""

from __future__ import annotations

import re

from app.constraint_discovery.contracts import (
    ConstraintCategory,
    ConstraintDiscoveryResult,
    ConstraintOrigin,
    DiscoveredConstraint,
)
from app.graph.state import PolyaState

_CONFIDENCE_PATTERN = re.compile(
    r"\b(?:confidence|certainty)\s*(?:of|>=|at least)?\s*(\d{1,3})%", re.I
)
_LEADING_CONFIDENCE_PATTERN = re.compile(
    r"\b(?:at least|>=)?\s*(\d{1,3})%\s*(?:confidence|certainty)", re.I
)
_RESOURCE_TERMS = ("budget", "deadline", "within ", "maximum", "at most", "no more than")
_DECISION_BOUNDARY_TERMS = (
    "budget",
    "cost",
    "deadline",
    "latency",
    "maximum",
    "minimum",
    "at most",
    "at least",
    "below",
    "above",
    "within",
    "risk",
    "quality",
    "must",
    "cannot",
    "without",
)
_NUMBER_PATTERN = re.compile(r"\d")


def _constraint(
    statement: str,
    category: ConstraintCategory,
    origin: ConstraintOrigin,
    source: str,
) -> DiscoveredConstraint:
    return DiscoveredConstraint(
        statement=statement,
        category=category,
        origin=origin,
        source=source,
    )


def _has_concrete_decision_boundary(problem_text: list[str]) -> bool:
    """Return whether text contains an inspectable preference or hard boundary."""
    for item in problem_text:
        lowered = item.casefold()
        if _NUMBER_PATTERN.search(item) or any(
            term in lowered for term in _DECISION_BOUNDARY_TERMS
        ):
            return True
    return False


def _confidence_threshold(raw: str) -> str | None:
    for pattern in (_CONFIDENCE_PATTERN, _LEADING_CONFIDENCE_PATTERN):
        match = pattern.search(raw)
        if match is not None:
            return match.group(1)
    return None


def discover_constraints(state: PolyaState) -> ConstraintDiscoveryResult:
    """Discover constraints that determine whether an answer can count as solved."""
    problem = state["structured_problem"]
    if problem is None:
        raise ValueError("constraint discovery requires a structured problem")

    raw = state["raw_input"]
    lowered = raw.casefold()
    constraints: list[DiscoveredConstraint] = [
        _constraint(
            item,
            ConstraintCategory.OTHER,
            ConstraintOrigin.EXPLICIT,
            "structured_problem.constraints",
        )
        for item in problem.constraints
    ]
    constraints.extend(
        _constraint(
            f"Success condition: {criterion}",
            ConstraintCategory.SUCCESS,
            ConstraintOrigin.SUCCESS_CRITERION,
            "structured_problem.success_criteria",
        )
        for criterion in problem.success_criteria
    )

    if problem.time_window or any(
        token in lowered for token in ("current", "today", "latest", "before ", "after ")
    ):
        constraints.append(
            _constraint(
                "Use information and observations valid for the stated time window.",
                ConstraintCategory.TIME_WINDOW,
                ConstraintOrigin.IMPLICIT,
                "time-sensitive problem context",
            )
        )
    if any(token in lowered for token in ("private", "confidential", "pii", "personal data")):
        constraints.append(
            _constraint(
                "Do not disclose or send sensitive data to an unapproved capability.",
                ConstraintCategory.PRIVACY,
                ConstraintOrigin.IMPLICIT,
                "privacy-sensitive problem context",
            )
        )
    if problem.required_data_sources or problem.unknowns:
        constraints.append(
            _constraint(
                "Do not claim a verified conclusion until required data is available.",
                ConstraintCategory.DATA_AVAILABILITY,
                ConstraintOrigin.IMPLICIT,
                "required data sources and unresolved unknowns",
            )
        )
    if any(token in lowered for token in ("payment", "cardholder", "pci", "checkout")):
        constraints.append(
            _constraint(
                "Preserve applicable payment-data and PCI controls.",
                ConstraintCategory.COMPLIANCE,
                ConstraintOrigin.IMPLICIT,
                "payment-system context",
            )
        )
    if any(token in lowered for token in ("cause", "caused", "why", "because")):
        constraints.append(
            _constraint(
                "Do not present correlation as causation without a discriminating check.",
                ConstraintCategory.CAUSALITY,
                ConstraintOrigin.IMPLICIT,
                "causal question wording",
            )
        )
    confidence_threshold = _confidence_threshold(raw)
    if confidence_threshold is not None:
        constraints.append(
            _constraint(
                f"Meet the requested confidence threshold of {confidence_threshold}%.",
                ConstraintCategory.CONFIDENCE_THRESHOLD,
                ConstraintOrigin.EXPLICIT,
                "raw problem confidence threshold",
            )
        )
    if any(token in lowered for token in _RESOURCE_TERMS):
        constraints.append(
            _constraint(
                "Respect the stated resource, cost, or deadline boundary.",
                ConstraintCategory.RESOURCE,
                ConstraintOrigin.IMPLICIT,
                "resource-bound problem wording",
            )
        )

    missing: list[str] = []
    questions: list[str] = []
    if not problem.success_criteria:
        missing.append("observable success criterion")
        questions.append("What observable result would make this problem count as solved?")
    decision_like = problem.problem_type in {"planning", "comparison", "clarified_request"}
    has_decision_boundary = any(
        item.category
        in {
            ConstraintCategory.RESOURCE,
            ConstraintCategory.SAFETY,
            ConstraintCategory.CONFIDENCE_THRESHOLD,
            ConstraintCategory.TIME_WINDOW,
        }
        for item in constraints
    ) or _has_concrete_decision_boundary([*problem.constraints, *problem.success_criteria])
    if decision_like and not has_decision_boundary:
        missing.append("decision boundary or tradeoff preference")
        questions.append(
            "Which cost, time, risk, or quality boundary should determine the acceptable option?"
        )

    unique: dict[tuple[str, ConstraintCategory], DiscoveredConstraint] = {}
    for item in constraints:
        unique[(item.statement.casefold(), item.category)] = item
    return ConstraintDiscoveryResult(
        constraints=list(unique.values()),
        missing_constraints=missing,
        clarifying_questions=questions,
    )
