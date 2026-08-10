"""Experimental structured outputs for model-backed cognitive capabilities."""

from __future__ import annotations

from pydantic import Field, JsonValue, model_validator

from app.models.contracts import (
    ContractModel,
    Hypothesis,
    KnowledgeGap,
    NonEmptyStr,
    PlanTask,
    Reflection,
    VerificationReport,
)


class GapDetectionOutput(ContractModel):
    """Knowledge missing between the current state and a verified outcome."""

    gaps: list[KnowledgeGap] = Field(default_factory=list)
    rationale: NonEmptyStr


class HypothesisGenerationOutput(ContractModel):
    """Diverse, falsifiable candidate explanations or solution paths."""

    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=5)


class PlanGenerationOutput(ContractModel):
    """Bounded tasks that can produce inspectable observations."""

    tasks: list[PlanTask] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def task_ids_must_be_unique(self) -> PlanGenerationOutput:
        ids = [task.id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("plan task ids must be unique")
        return self


class AnalysisExecutionOutput(ContractModel):
    """Inspectable output from one bounded analysis task."""

    summary: NonEmptyStr
    output: JsonValue


class VerificationCapabilityOutput(ContractModel):
    """A conclusion that is accepted only when declared checks pass."""

    report: VerificationReport
    final_answer: NonEmptyStr | None = None

    @model_validator(mode="after")
    def answer_must_match_verification(self) -> VerificationCapabilityOutput:
        if self.report.passed and self.final_answer is None:
            raise ValueError("passing verification requires a final answer")
        if not self.report.passed and self.final_answer is not None:
            raise ValueError("failed verification cannot provide a final answer")
        return self


class ReflectionCapabilityOutput(ContractModel):
    """Lessons extracted only after the kernel has accepted verification."""

    reflection: Reflection
