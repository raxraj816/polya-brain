"""Prompt-layer contracts for Chapter 11 problem understanding."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, JsonValue, model_validator

from app.llm import LLMTokenUsage
from app.models.contracts import ContractModel, NonEmptyStr, ProductMode, Score, StructuredProblem

MODE_CLARIFICATION_THRESHOLD = 0.65
BoundedParserRetryCount = Annotated[int, Field(ge=0, le=2)]
PositiveInt = Annotated[int, Field(gt=0)]


class PromptExampleCategory(StrEnum):
    """Required Chapter 11 prompt-example categories."""

    MATH = "math"
    LOGIC = "logic"
    SOFTWARE_DEBUGGING = "software_debugging"
    TECHNICAL_RESEARCH = "technical_research"
    DATA_ANALYSIS = "data_analysis"
    PLANNING = "planning"
    SCIENTIFIC_REASONING = "scientific_reasoning"
    AMBIGUOUS_INPUT = "ambiguous_input"
    LOW_CONFIDENCE_MODE = "low_confidence_mode_selection"
    WRONG_PROBLEM_FRAMING = "wrong_problem_framing"


class ProblemUnderstandingOutput(ContractModel):
    """Strict LLM output before promotion into the canonical problem contract."""

    literal_framing: NonEmptyStr
    deeper_framing: NonEmptyStr
    wrong_problem_warning: NonEmptyStr | None = None
    goal: NonEmptyStr
    problem_type: NonEmptyStr
    domain: NonEmptyStr | None = None
    selected_mode: ProductMode
    mode_confidence: Score
    mode_selection_reason: NonEmptyStr
    needs_clarification: bool = False
    clarifying_questions: list[NonEmptyStr] = Field(default_factory=list)
    given: list[NonEmptyStr]
    unknown: list[NonEmptyStr]
    constraints: list[NonEmptyStr]
    success_criteria: list[NonEmptyStr]
    affected_entities: list[NonEmptyStr] = Field(default_factory=list)
    time_window: dict[str, JsonValue] = Field(default_factory=dict)
    required_data_sources: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def clarification_state_must_be_coherent(self) -> Self:
        """Ensure uncertain framing routes to questions instead of fake certainty."""
        if self.mode_confidence < MODE_CLARIFICATION_THRESHOLD and not self.needs_clarification:
            raise ValueError(
                "mode confidence below clarification threshold requires needs_clarification"
            )
        if self.needs_clarification and not self.clarifying_questions:
            raise ValueError("needs_clarification requires at least one clarifying question")
        if not self.needs_clarification and self.clarifying_questions:
            raise ValueError("clarifying questions require needs_clarification")
        if not self.success_criteria:
            raise ValueError("problem understanding requires at least one success criterion")
        return self

    def to_structured_problem(self) -> StructuredProblem:
        """Map validated prompt output into the Chapter 5 canonical contract."""
        return StructuredProblem(
            core_question=self.goal,
            problem_type=self.problem_type,
            domain=self.domain,
            knowns=self.given,
            unknowns=self.unknown,
            constraints=self.constraints,
            success_criteria=self.success_criteria,
            affected_entities=self.affected_entities,
            time_window=self.time_window,
            required_data_sources=self.required_data_sources,
        )


class ProblemUnderstandingExample(ContractModel):
    """One inspectable local few-shot example and its validated output."""

    category: PromptExampleCategory
    raw_input: NonEmptyStr
    mode_hint: ProductMode | None = None
    domain_hint: NonEmptyStr | None = None
    output: ProblemUnderstandingOutput


class ParserRetryPolicy(ContractModel):
    """Bounded LLM repair policy for malformed structured responses."""

    max_llm_repair_attempts: BoundedParserRetryCount = 1


class ProblemUnderstandingParseResult(ContractModel):
    """Validated output plus deterministic local repair audit details."""

    output: ProblemUnderstandingOutput
    local_repair_steps: list[NonEmptyStr] = Field(default_factory=list)


class ProblemUnderstandingRunResult(ContractModel):
    """End-to-end prompt/parser result consumed by the future Chapter 13 engine."""

    output: ProblemUnderstandingOutput
    structured_problem: StructuredProblem
    prompt_version: NonEmptyStr
    provider: NonEmptyStr
    model: NonEmptyStr
    llm_call_count: Annotated[int, Field(ge=0)]
    llm_repair_attempts: Annotated[int, Field(ge=0)] = 0
    local_repair_steps: list[NonEmptyStr] = Field(default_factory=list)
    response_ids: list[NonEmptyStr] = Field(default_factory=list)
    usage: LLMTokenUsage = Field(default_factory=LLMTokenUsage)
