"""Evaluation-only contracts for field-derived executable investigations."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, model_validator

from app.models.contracts import ContractModel, NonEmptyStr


class FieldConcept(ContractModel):
    """One semantic requirement satisfied by any declared phrase."""

    name: NonEmptyStr
    any_of: Annotated[list[NonEmptyStr], Field(min_length=1)]


class FieldArtifact(ContractModel):
    """One frozen file and its context visibility."""

    path: NonEmptyStr
    role: Literal["issue", "buggy_source", "test", "fixed_source"]
    visible_to_conditions: bool
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def resolve(self, root: Path) -> Path:
        """Resolve only a contained regular file."""
        resolved_root = root.resolve(strict=True)
        resolved = (resolved_root / self.path).resolve(strict=True)
        if not resolved.is_file() or not resolved.is_relative_to(resolved_root):
            raise ValueError(f"field artifact escapes its case root: {self.path}")
        return resolved


class FieldCase(ContractModel):
    """One immutable, field-derived debugging task with hidden gold semantics."""

    id: NonEmptyStr
    family: NonEmptyStr
    pair_position: Literal["first", "transfer"]
    project: NonEmptyStr
    public_historical_case: bool = True
    reduced_reproduction: bool = True
    upstream_repository: HttpUrl
    bugsinpy_metadata: HttpUrl
    license: NonEmptyStr
    buggy_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    fixed_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    problem_statement: NonEmptyStr
    artifacts: Annotated[list[FieldArtifact], Field(min_length=4)]
    required_mechanism_concepts: Annotated[list[FieldConcept], Field(min_length=1)]
    required_correction_concepts: Annotated[list[FieldConcept], Field(min_length=1)]
    required_check_concepts: Annotated[list[FieldConcept], Field(min_length=1)]
    forbidden_conclusions: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def artifact_visibility_is_complete(self) -> FieldCase:
        roles = {artifact.role for artifact in self.artifacts}
        required_roles = {"issue", "buggy_source", "test", "fixed_source"}
        if not required_roles <= roles:
            raise ValueError("field case requires issue, buggy, test, and fixed artifacts")
        fixed = [artifact for artifact in self.artifacts if artifact.role == "fixed_source"]
        if any(artifact.visible_to_conditions for artifact in fixed):
            raise ValueError("fixed field artifacts must remain hidden from both conditions")
        visible_roles = {
            artifact.role for artifact in self.artifacts if artifact.visible_to_conditions
        }
        if not {"issue", "buggy_source", "test"} <= visible_roles:
            raise ValueError("issue, buggy source, and test must be visible to both conditions")
        return self

    def visible_artifacts(self) -> list[FieldArtifact]:
        """Return only artifacts eligible for model context."""
        return [artifact for artifact in self.artifacts if artifact.visible_to_conditions]

    def verify_integrity(self, root: Path) -> None:
        """Reject drift in any visible or hidden frozen artifact."""
        for artifact in self.artifacts:
            path = artifact.resolve(root)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != artifact.sha256:
                raise ValueError(f"field artifact hash mismatch: {artifact.path}")


class ReproductionResult(ContractModel):
    """Subprocess evidence for one buggy or fixed reproduction."""

    implementation: Literal["buggy", "fixed"]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: Annotated[float, Field(ge=0.0)]


class FieldPreflight(ContractModel):
    """Executable eligibility proof for one case."""

    case_id: NonEmptyStr
    buggy: ReproductionResult
    fixed: ReproductionResult
    eligible: bool
    rationale: NonEmptyStr


class FieldInvestigationOutput(ContractModel):
    """Direct-condition output contract and normalized review surface."""

    status: Literal["diagnosed", "insufficient_evidence"]
    root_cause: str | None = None
    implicated_artifacts: list[NonEmptyStr] = Field(default_factory=list)
    corrective_action: str | None = None
    verification_steps: list[NonEmptyStr] = Field(default_factory=list)
    evidence_references: list[NonEmptyStr] = Field(default_factory=list)
    execution_attestations: list[NonEmptyStr] = Field(default_factory=list)
    remaining_uncertainty: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def diagnosis_requires_content(self) -> FieldInvestigationOutput:
        if self.status == "diagnosed" and (
            not self.root_cause or not self.corrective_action or not self.verification_steps
        ):
            raise ValueError("diagnosed field output requires cause, correction, and checks")
        if self.status == "insufficient_evidence" and (
            self.root_cause is not None or self.corrective_action is not None
        ):
            raise ValueError("insufficient-evidence output cannot force a diagnosis")
        return self


class FieldConditionScore(ContractModel):
    """Automated semantic and resource score for one condition."""

    condition: Literal["polya", "direct"]
    mechanism_concepts_passed: bool
    correction_concepts_passed: bool
    check_concepts_passed: bool
    evidence_reference_passed: bool
    executable_verification_passed: bool
    forbidden_conclusion_hits: list[NonEmptyStr] = Field(default_factory=list)
    unsupported_forced_conclusion: bool
    passed: bool
    model_calls: Annotated[int, Field(ge=0)]
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]
    latency_ms: Annotated[float, Field(ge=0.0)]
