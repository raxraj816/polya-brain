"""Structured model outputs and the verification certificate for verified coding.

These are trace-level contracts. The certificate is projected into existing
PolyaState fields; it is not a new core data contract.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.contracts import ContractModel
from app.verified_coding.harness import DifferentialResult, Entrypoint, Example, Regression

CODE_LIMIT = 12_000


class Proposal(BaseModel):
    """Lean solver output; the same strict schema as the matched lean baseline."""

    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=20_000)
    tests: list[str] = Field(min_length=1, max_length=20)
    explanation: str = Field(min_length=1)


class ModelOutput(BaseModel):
    """Tolerant parse boundary for model JSON: unknown keys and nulls are dropped."""

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _drop_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {key: value for key, value in data.items() if value is not None}
        return data


class OracleEntrypoint(ModelOutput):
    name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    class_name: str | None = Field(
        default=None, max_length=120, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$"
    )

    def harness(self) -> Entrypoint:
        return Entrypoint(name=self.name, class_name=self.class_name or None)


class OracleExample(ModelOutput):
    call: str = Field(min_length=1, max_length=2_000)
    expected: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="before")
    @classmethod
    def _stringify(cls, data: Any) -> Any:
        if isinstance(data, dict) and "expected" in data and not isinstance(data["expected"], str):
            data = {**data, "expected": repr(data["expected"])}
        return data

    def harness(self) -> Example:
        return Example(call=self.call.strip(), expected=self.expected.strip())


class OraclePackage(ModelOutput):
    """Independent verification material written without seeing any candidate."""

    entrypoint: OracleEntrypoint
    reference_code: str = Field(min_length=1, max_length=CODE_LIMIT)
    generator_code: str = Field(min_length=1, max_length=CODE_LIMIT)
    examples: list[OracleExample] = Field(default_factory=list, max_length=20)
    scale_code: str = Field(default="", max_length=CODE_LIMIT)
    same_code: str = Field(default="", max_length=CODE_LIMIT)
    assumptions: list[str] = Field(default_factory=list, max_length=12)


class Verdict(StrEnum):
    CANDIDATE_WRONG = "candidate_wrong"
    REFERENCE_WRONG = "reference_wrong"
    BOTH_WRONG = "both_wrong"
    BOTH_ACCEPTABLE = "both_acceptable"
    AMBIGUOUS = "ambiguous"


class Relaxation(StrEnum):
    NONE = ""
    NUMERIC_TYPE = "numeric_type"
    UNORDERED = "unordered"
    MUTATION_ALLOWED = "mutation_allowed"


class Adjudication(ModelOutput):
    """A ruling on one concrete disagreement, grounded in quoted problem text."""

    verdict: Verdict
    expected: str = Field(default="", max_length=4_000)
    governing_requirement: str = Field(default="", max_length=600)
    explanation: str = Field(default="", max_length=1_500)
    repaired_candidate_code: str = Field(default="", max_length=20_000)
    repaired_reference_code: str = Field(default="", max_length=CODE_LIMIT)
    relaxation: Relaxation = Relaxation.NONE
    question: str = Field(default="", max_length=600)


class CertificateStatus(StrEnum):
    VERIFIED = "verified"
    REPAIRED = "repaired_and_verified"
    DISPUTED = "disputed"
    AMBIGUOUS = "ambiguous_specification"
    UNVERIFIED = "unverified"
    NO_CANDIDATE = "no_candidate"


class Finding(ContractModel):
    """One concrete defect found and how it was resolved."""

    round: int
    source: str  # stated_example | differential | regression | scale | mutation
    args: str
    candidate_output: str
    reference_output: str
    verdict: str
    expected: str = ""
    governing_requirement: str = ""
    explanation: str = ""
    resolved: bool = False


class ModelCallRecord(ContractModel):
    role: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    duration_ms: float = 0.0
    outcome: str = "ok"


class SandboxRunRecord(ContractModel):
    purpose: str
    runtime_ms: float = 0.0
    timed_out: bool = False
    exit_code: int = 0


class Certificate(ContractModel):
    """What was checked, what was found, and what remains unproven."""

    status: CertificateStatus
    entrypoint: str = ""
    own_tests_passed: bool = False
    own_test_count: int = 0
    examples_sourced: int = 0
    examples_dropped: int = 0
    cases_compared: int = 0
    sizes_covered: list[int] = Field(default_factory=list)
    scale_seconds: list[float] = Field(default_factory=list)
    scale_timeouts: int = 0
    findings: list[Finding] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_question: str = ""
    limitations: list[str] = Field(default_factory=list)
    final_differential: DifferentialResult | None = None
    regressions: list[Regression] = Field(default_factory=list)
