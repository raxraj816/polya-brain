"""Experimental structured output for Chapter 14 constraint discovery."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from app.models.contracts import ContractModel, NonEmptyStr


class ConstraintOrigin(StrEnum):
    """How a constraint entered the current problem state."""

    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    SUCCESS_CRITERION = "success_criterion"


class ConstraintCategory(StrEnum):
    """General constraint families that affect solution validity."""

    TIME_WINDOW = "time_window"
    PRIVACY = "privacy"
    DATA_AVAILABILITY = "data_availability"
    COMPLIANCE = "compliance"
    CAUSALITY = "causality"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    RESOURCE = "resource"
    SAFETY = "safety"
    SUCCESS = "success"
    OTHER = "other"


class DiscoveredConstraint(ContractModel):
    """One inspectable requirement that a valid solution must respect."""

    statement: NonEmptyStr
    category: ConstraintCategory
    origin: ConstraintOrigin
    hard: bool = True
    source: NonEmptyStr
    requires_confirmation: bool = False


class ConstraintDiscoveryResult(ContractModel):
    """Accepted constraints plus missing user-owned requirements."""

    constraints: list[DiscoveredConstraint] = Field(default_factory=list)
    missing_constraints: list[NonEmptyStr] = Field(default_factory=list)
    clarifying_questions: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def missing_constraints_require_questions(self) -> ConstraintDiscoveryResult:
        if bool(self.missing_constraints) != bool(self.clarifying_questions):
            raise ValueError(
                "missing_constraints and clarifying_questions must either both be present or absent"
            )
        return self
