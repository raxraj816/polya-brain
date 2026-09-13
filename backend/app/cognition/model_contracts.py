"""Experimental structured outputs for model-backed cognitive capabilities."""

from __future__ import annotations

from pydantic import Field, JsonValue, model_validator

from app.graph.state import ExecutionOutput
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


class DeliberationCapabilityOutput(ContractModel):
    """Fused semantic proposal for candidates, checks, and analytic outputs."""

    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=5)
    tasks: list[PlanTask] = Field(min_length=1, max_length=6)
    execution_outputs: list[ExecutionOutput] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def plan_and_outputs_must_be_bounded_and_aligned(
        self,
    ) -> DeliberationCapabilityOutput:
        task_ids = [task.id for task in self.tasks]
        output_ids = [output.task_id for output in self.execution_outputs]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("deliberation task ids must be unique")
        if len(output_ids) != len(set(output_ids)):
            raise ValueError("deliberation output task ids must be unique")
        if set(task_ids) != set(output_ids):
            raise ValueError("every deliberation task requires one inspectable output")
        return self


class ConclusionCheckOutput(ContractModel):
    """Independent verification plus reflection in one bounded response."""

    report: VerificationReport
    final_answer: NonEmptyStr | None = None
    reflection: Reflection | None = None

    @model_validator(mode="after")
    def terminal_artifacts_must_match_verification(self) -> ConclusionCheckOutput:
        if self.report.passed and (self.final_answer is None or self.reflection is None):
            raise ValueError("passing conclusion check requires answer and reflection")
        if not self.report.passed and (
            self.final_answer is not None or self.reflection is not None
        ):
            raise ValueError("failed conclusion check cannot finalize or reflect")
        return self
