"""Typed verifier synthesis and deterministic execution for Chapter 13-E.

The factory is deliberately experimental.  It compiles only procedures whose
semantics are known and allowlisted; arbitrary natural-language criteria remain
explicitly semantic instead of being turned into generated executable code.
"""

from __future__ import annotations

import hashlib
import json
import math
from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field, JsonValue, model_validator

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CapabilityKind,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.cognition.source_patch_report import source_patch_conclusion
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import (
    ContractModel,
    NonEmptyStr,
    ReasoningMode,
    Reflection,
    RiskLevel,
    Score,
    VerificationReport,
)

VERIFIER_SUITE_EVENT = "verifier_suite_synthesized"
VERIFIER_RESULT_EVENT = "verifier_suite_executed"
VERIFIER_DECLARATION_EVENT = "verification_declarations_validated"
VERIFIER_FACTORY_VERSION = "verifier-factory@0.1.1"


class VerifierKind(StrEnum):
    """Supported verification substrates."""

    EXACT_EVIDENCE = "exact_evidence"
    STRUCTURED_ASSERTION = "structured_assertion"
    SEMANTIC_REVIEW = "semantic_review"


class VerifierOperation(StrEnum):
    """Allowlisted operations; no expression evaluation is permitted."""

    CLAIM_SUPPORTED_BY_EXCERPT = "claim_supported_by_excerpt"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    ALL_TRUE = "all_true"
    NO_ERROR = "no_error"
    SEMANTIC_CHECK = "semantic_check"


class VerifierLifecycle(StrEnum):
    """Lifecycle of a verifier specification or its execution result."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class VerifierIndependence(StrEnum):
    """How independent the check is from candidate generation."""

    SOURCE_ARTIFACT = "source_artifact"
    TOOL_OUTPUT = "tool_output"
    MODEL_REVIEW = "model_review"


class VerifierInputSource(StrEnum):
    """Canonical state collection from which an input is bound."""

    EVIDENCE = "evidence"
    EXECUTION_OUTPUT = "execution_output"


class VerifierInputBinding(ContractModel):
    """A constrained pointer into canonical state."""

    name: NonEmptyStr
    source: VerifierInputSource
    selector: NonEmptyStr
    independent_of_candidate: bool = True


class VerifierSpecification(ContractModel):
    """One criterion-bound, inspectable verification program."""

    id: NonEmptyStr
    criterion_index: Annotated[int, Field(ge=0)]
    objective: NonEmptyStr
    kind: VerifierKind
    operation: VerifierOperation
    inputs: list[VerifierInputBinding] = Field(min_length=1)
    expected: JsonValue = None
    evidence_requirements: list[NonEmptyStr] = Field(default_factory=list)
    independence: VerifierIndependence
    applicability: list[NonEmptyStr] = Field(default_factory=list)
    timeout_seconds: Annotated[float, Field(gt=0.0, le=30.0)] = 2.0
    estimated_cost: Score = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    lifecycle: VerifierLifecycle = VerifierLifecycle.VALIDATED
    executable: bool = True

    @model_validator(mode="after")
    def executable_checks_require_independent_inputs(self) -> VerifierSpecification:
        """Prevent an answer from being accepted solely because it asserts itself."""
        if self.executable and not any(item.independent_of_candidate for item in self.inputs):
            raise ValueError("executable verifier requires an independent input")
        if self.kind is VerifierKind.SEMANTIC_REVIEW:
            if self.executable or self.operation is not VerifierOperation.SEMANTIC_CHECK:
                raise ValueError("semantic review must remain a non-executable proposal")
            if self.lifecycle is not VerifierLifecycle.PROPOSED:
                raise ValueError("semantic review starts in proposed lifecycle")
        elif not self.executable or self.lifecycle is not VerifierLifecycle.VALIDATED:
            raise ValueError("deterministic verifier must be executable and validated")
        return self


class VerifierSuite(ContractModel):
    """A complete attempt to cover every declared success criterion."""

    version: NonEmptyStr = VERIFIER_FACTORY_VERSION
    criterion_count: Annotated[int, Field(ge=1)]
    specifications: list[VerifierSpecification] = Field(min_length=1)
    warnings: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def specifications_must_reference_declared_criteria(self) -> VerifierSuite:
        if any(item.criterion_index >= self.criterion_count for item in self.specifications):
            raise ValueError("verifier specification references an unknown criterion")
        return self


class VerifierResult(ContractModel):
    """Result of executing one specification."""

    specification_id: NonEmptyStr
    criterion_index: Annotated[int, Field(ge=0)]
    status: VerifierLifecycle
    detail: NonEmptyStr
    observed: JsonValue = None
    evidence_refs: list[NonEmptyStr] = Field(default_factory=list)
    normalized_cost: Score = 0.0

    @model_validator(mode="after")
    def result_requires_terminal_status(self) -> VerifierResult:
        if self.status not in {
            VerifierLifecycle.PASSED,
            VerifierLifecycle.FAILED,
            VerifierLifecycle.INCONCLUSIVE,
        }:
            raise ValueError("verifier result requires a terminal lifecycle status")
        return self


class VerifierSuiteResult(ContractModel):
    """Aggregated suite result and canonical compatibility report."""

    suite: VerifierSuite
    results: list[VerifierResult]
    passed: bool
    criterion_coverage: Score
    report: VerificationReport


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().split()).rstrip(".")


def _structured_declarations(state: PolyaState) -> dict[int, tuple[str, dict[str, Any]]]:
    """Read allowlisted declarations from plan metadata, never executable text."""
    declarations: dict[int, tuple[str, dict[str, Any]]] = {}
    for task in state["plan"]:
        raw = task.params.get("verification")
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            if not isinstance(item, dict):
                continue
            criterion_index = item.get("criterion_index")
            if (
                isinstance(criterion_index, int)
                and not isinstance(criterion_index, bool)
                and criterion_index not in declarations
            ):
                declarations[criterion_index] = (task.id, item)
    return declarations


def _declaration_fingerprint(state: PolyaState) -> str:
    problem = state["structured_problem"]
    declarations = _structured_declarations(state)
    payload = {
        "criteria": problem.success_criteria if problem is not None else [],
        "declarations": [
            {
                "task_id": task_id,
                "criterion_index": index,
                "operation": item.get("operation"),
                "actual_path": item.get("actual_path"),
                "expected": item.get("expected"),
            }
            for index, (task_id, item) in sorted(declarations.items())
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def verification_declarations_validated_event(state: PolyaState) -> StateEvent:
    """Bind trusted task construction to the exact declarative verifier inputs."""
    problem = state["structured_problem"]
    if problem is None or not problem.success_criteria:
        raise ValueError("verification declaration validation requires success criteria")
    declarations = _structured_declarations(state)
    if len(declarations) != len(problem.success_criteria):
        raise ValueError("every success criterion requires one verification declaration")
    for index, criterion in enumerate(problem.success_criteria):
        declaration = declarations.get(index)
        if declaration is None or _structured_specification(index, criterion, *declaration) is None:
            raise ValueError("verification declaration uses an unsupported operation or binding")
    return StateEvent(
        engine_name="task_specification",
        event_type=VERIFIER_DECLARATION_EVENT,
        reasoning_mode=ReasoningMode.VERIFY,
        summary="Validated declarative verifier bindings against every success criterion.",
        metadata={
            "fingerprint": _declaration_fingerprint(state),
            "criterion_count": len(problem.success_criteria),
            "producer": "trusted_task_specification",
        },
    )


def _structured_declarations_are_validated(state: PolyaState) -> bool:
    problem = state["structured_problem"]
    if problem is None:
        return False
    fingerprint = _declaration_fingerprint(state)
    return any(
        event.event_type == VERIFIER_DECLARATION_EVENT
        and event.engine_name == "task_specification"
        and event.metadata.get("producer") == "trusted_task_specification"
        and event.metadata.get("criterion_count") == len(problem.success_criteria)
        and event.metadata.get("fingerprint") == fingerprint
        for event in state["events"]
    )


def _structured_specification(
    criterion_index: int,
    criterion: str,
    task_id: str,
    declaration: dict[str, Any],
) -> VerifierSpecification | None:
    raw_operation = declaration.get("operation")
    actual_path = declaration.get("actual_path")
    if not isinstance(raw_operation, str) or not isinstance(actual_path, str):
        return None
    try:
        operation = VerifierOperation(raw_operation)
    except ValueError:
        return None
    if operation in {
        VerifierOperation.CLAIM_SUPPORTED_BY_EXCERPT,
        VerifierOperation.SEMANTIC_CHECK,
    }:
        return None
    return VerifierSpecification(
        id=f"criterion-{criterion_index + 1}-structured",
        criterion_index=criterion_index,
        objective=criterion,
        kind=VerifierKind.STRUCTURED_ASSERTION,
        operation=operation,
        inputs=[
            VerifierInputBinding(
                name="actual",
                source=VerifierInputSource.EXECUTION_OUTPUT,
                selector=f"{task_id}:{actual_path}",
            )
        ],
        expected=declaration.get("expected"),
        evidence_requirements=["A successful execution output from the declared plan task."],
        independence=VerifierIndependence.TOOL_OUTPUT,
        applicability=[f"Plan task {task_id} emits field {actual_path}."],
    )


class VerifierFactory:
    """Compile known verification procedures and expose unknown ones honestly."""

    version = VERIFIER_FACTORY_VERSION

    def synthesize(self, state: PolyaState) -> VerifierSuite:
        problem = state["structured_problem"]
        if problem is None or not problem.success_criteria:
            raise ValueError("verifier synthesis requires declared success criteria")
        declarations = _structured_declarations(state)
        declarations_validated = _structured_declarations_are_validated(state)
        specifications: list[VerifierSpecification] = []
        warnings: list[str] = []
        for index, criterion in enumerate(problem.success_criteria):
            if problem.problem_type == "explicit_artifact_lookup" and state["evidence"]:
                specifications.append(
                    VerifierSpecification(
                        id=f"criterion-{index + 1}-artifact",
                        criterion_index=index,
                        objective=criterion,
                        kind=VerifierKind.EXACT_EVIDENCE,
                        operation=VerifierOperation.CLAIM_SUPPORTED_BY_EXCERPT,
                        inputs=[
                            VerifierInputBinding(
                                name="artifact_evidence",
                                source=VerifierInputSource.EVIDENCE,
                                selector="0",
                            )
                        ],
                        evidence_requirements=[
                            "The claim occurs in the source-visible excerpt.",
                            "The evidence has an explicit source URI.",
                            "The candidate conclusion matches the admitted claim.",
                        ],
                        independence=VerifierIndependence.SOURCE_ARTIFACT,
                        applicability=[
                            "The task is an exact explicit-artifact lookup.",
                            "Exactly one conclusion-bearing artifact fact is admitted.",
                        ],
                    )
                )
                continue
            declaration = declarations.get(index) if declarations_validated else None
            structured = (
                _structured_specification(index, criterion, *declaration)
                if declaration is not None
                else None
            )
            if structured is not None:
                specifications.append(structured)
                continue
            if index in declarations and not declarations_validated:
                warnings.append(
                    f"Criterion {index + 1} has an untrusted or stale verifier declaration."
                )
            warnings.append(
                f"Criterion {index + 1} has no known deterministic verifier; semantic review is required."
            )
            specifications.append(
                VerifierSpecification(
                    id=f"criterion-{index + 1}-semantic",
                    criterion_index=index,
                    objective=criterion,
                    kind=VerifierKind.SEMANTIC_REVIEW,
                    operation=VerifierOperation.SEMANTIC_CHECK,
                    inputs=[
                        VerifierInputBinding(
                            name="current_state",
                            source=VerifierInputSource.EVIDENCE,
                            selector="all",
                            independent_of_candidate=False,
                        )
                    ],
                    evidence_requirements=["A bounded independent semantic checker."],
                    independence=VerifierIndependence.MODEL_REVIEW,
                    applicability=["No allowlisted deterministic verifier is known."],
                    lifecycle=VerifierLifecycle.PROPOSED,
                    executable=False,
                )
            )
        return VerifierSuite(
            criterion_count=len(problem.success_criteria),
            specifications=specifications,
            warnings=warnings,
        )

    def can_execute_completely(self, state: PolyaState) -> bool:
        """Return true only when every criterion has an executable specification."""
        try:
            suite = self.synthesize(state)
        except ValueError:
            return False
        covered = {item.criterion_index for item in suite.specifications if item.executable}
        complete = len(covered) == suite.criterion_count and all(
            item.executable for item in suite.specifications
        )
        if not complete:
            return False
        if all(item.kind is VerifierKind.EXACT_EVIDENCE for item in suite.specifications):
            eligible = [
                item
                for item in state["evidence"]
                if item.source_uri is not None
                and item.raw_excerpt is not None
                and (item.reliability_score or 0.0) >= 0.75
                and (item.relevance_score or 0.0) >= 0.2
            ]
            return len(eligible) == 1 and len(state["hypotheses"]) == 1
        return True


def _resolve_path(value: Any, path: str) -> tuple[bool, Any]:
    """Resolve a dot/index path without attributes, calls, or expressions."""
    current = value
    if not path:
        return True, current
    for segment in path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
            continue
        if isinstance(current, list) and segment.isdigit():
            index = int(segment)
            if 0 <= index < len(current):
                current = current[index]
                continue
        return False, None
    return True, current


def _execution_output(state: PolyaState, task_id: str) -> ExecutionOutput | None:
    return next((item for item in state["execution_outputs"] if item.task_id == task_id), None)


def _structured_assertion(
    operation: VerifierOperation,
    actual: Any,
    expected: JsonValue,
) -> tuple[bool, str]:
    try:
        if operation is VerifierOperation.EQUALS:
            return actual == expected, "Compared the structured value for exact equality."
        if operation is VerifierOperation.NOT_EQUALS:
            return actual != expected, "Compared the structured value for inequality."
        if operation is VerifierOperation.GREATER_THAN_OR_EQUAL:
            passed = (
                isinstance(actual, (int, float))
                and not isinstance(actual, bool)
                and isinstance(expected, (int, float))
                and not isinstance(expected, bool)
                and math.isfinite(float(actual))
                and math.isfinite(float(expected))
                and actual >= expected
            )
            return passed, "Checked the numeric lower bound."
        if operation is VerifierOperation.LESS_THAN_OR_EQUAL:
            passed = (
                isinstance(actual, (int, float))
                and not isinstance(actual, bool)
                and isinstance(expected, (int, float))
                and not isinstance(expected, bool)
                and math.isfinite(float(actual))
                and math.isfinite(float(expected))
                and actual <= expected
            )
            return passed, "Checked the numeric upper bound."
        if operation is VerifierOperation.CONTAINS:
            if isinstance(actual, str) and isinstance(expected, str):
                return expected in actual, "Checked exact substring containment."
            if isinstance(actual, list):
                return expected in actual, "Checked exact list membership."
            return False, "Containment requires a string or list observation."
        if operation is VerifierOperation.ALL_TRUE:
            return (
                isinstance(actual, list) and bool(actual) and all(item is True for item in actual),
                "Checked that every non-empty list element is exactly true.",
            )
        if operation is VerifierOperation.NO_ERROR:
            return actual in {None, ""}, "Checked that the execution error field is empty."
    except TypeError, ValueError:
        return False, "The structured assertion received incompatible values."
    return False, "The operation is not executable by the structured verifier."


class DeterministicVerifierExecutor:
    """Execute validated specs against canonical evidence and tool output."""

    def execute(self, suite: VerifierSuite, state: PolyaState) -> VerifierSuiteResult:
        results = [self._execute_specification(item, state) for item in suite.specifications]
        passed_indices = {
            result.criterion_index
            for result in results
            if result.status is VerifierLifecycle.PASSED
        }
        coverage = len(passed_indices) / suite.criterion_count
        passed = (
            coverage == 1.0
            and len(results) == len(suite.specifications)
            and all(item.status is VerifierLifecycle.PASSED for item in results)
        )
        checks = [f"{item.specification_id}: {item.detail}" for item in results]
        failures = [
            f"{item.specification_id}: {item.detail}"
            for item in results
            if item.status is not VerifierLifecycle.PASSED
        ]
        report = VerificationReport(
            passed=passed,
            checks_run=checks,
            failed_checks=failures,
            confidence_delta=0.2 if passed else -0.35,
            recommended_route=("finalize" if passed else "acquire_or_replan"),
        )
        return VerifierSuiteResult(
            suite=suite,
            results=results,
            passed=passed,
            criterion_coverage=coverage,
            report=report,
        )

    def _execute_specification(
        self,
        specification: VerifierSpecification,
        state: PolyaState,
    ) -> VerifierResult:
        if not specification.executable:
            return VerifierResult(
                specification_id=specification.id,
                criterion_index=specification.criterion_index,
                status=VerifierLifecycle.INCONCLUSIVE,
                detail="No allowlisted deterministic procedure exists for this criterion.",
            )
        if specification.kind is VerifierKind.EXACT_EVIDENCE:
            return self._execute_exact_evidence(specification, state)
        if specification.kind is VerifierKind.STRUCTURED_ASSERTION:
            return self._execute_structured(specification, state)
        return VerifierResult(
            specification_id=specification.id,
            criterion_index=specification.criterion_index,
            status=VerifierLifecycle.INCONCLUSIVE,
            detail="The validated verifier kind has no executor.",
        )

    def _execute_exact_evidence(
        self,
        specification: VerifierSpecification,
        state: PolyaState,
    ) -> VerifierResult:
        eligible = [
            item
            for item in state["evidence"]
            if item.source_uri is not None
            and item.raw_excerpt is not None
            and (item.reliability_score or 0.0) >= 0.75
            and (item.relevance_score or 0.0) >= 0.2
        ]
        hypothesis = state["hypotheses"][0].statement if len(state["hypotheses"]) == 1 else None
        passed = bool(
            len(eligible) == 1
            and hypothesis is not None
            and eligible[0].claim in (eligible[0].raw_excerpt or "")
            and _normalized_text(hypothesis) == _normalized_text(eligible[0].claim)
        )
        source_uri = eligible[0].source_uri if len(eligible) == 1 else None
        evidence_refs = [source_uri] if source_uri is not None else []
        observed: JsonValue = {
            "eligible_evidence_count": len(eligible),
            "claim_in_excerpt": bool(
                len(eligible) == 1 and eligible[0].claim in (eligible[0].raw_excerpt or "")
            ),
            "candidate_matches_claim": bool(
                len(eligible) == 1
                and hypothesis is not None
                and _normalized_text(hypothesis) == _normalized_text(eligible[0].claim)
            ),
        }
        return VerifierResult(
            specification_id=specification.id,
            criterion_index=specification.criterion_index,
            status=VerifierLifecycle.PASSED if passed else VerifierLifecycle.FAILED,
            detail=(
                "Matched one admitted claim to its source excerpt, provenance, and candidate."
                if passed
                else "The exact-evidence independence or claim/excerpt/candidate invariant failed."
            ),
            observed=observed,
            evidence_refs=evidence_refs,
        )

    def _execute_structured(
        self,
        specification: VerifierSpecification,
        state: PolyaState,
    ) -> VerifierResult:
        selector = specification.inputs[0].selector
        task_id, separator, path = selector.partition(":")
        output = _execution_output(state, task_id)
        if not separator or output is None or output.error is not None:
            return VerifierResult(
                specification_id=specification.id,
                criterion_index=specification.criterion_index,
                status=VerifierLifecycle.FAILED,
                detail="The declared independent execution output is missing or failed.",
                observed={"task_id": task_id, "error": output.error if output else "missing"},
            )
        found, actual = _resolve_path(output.output, path)
        if not found:
            return VerifierResult(
                specification_id=specification.id,
                criterion_index=specification.criterion_index,
                status=VerifierLifecycle.FAILED,
                detail=f"Structured output path {path!r} does not exist.",
                observed={"task_id": task_id, "path": path},
            )
        passed, detail = _structured_assertion(
            specification.operation,
            actual,
            specification.expected,
        )
        return VerifierResult(
            specification_id=specification.id,
            criterion_index=specification.criterion_index,
            status=VerifierLifecycle.PASSED if passed else VerifierLifecycle.FAILED,
            detail=detail
            if passed
            else f"{detail} The observed value did not satisfy the invariant.",
            observed={"actual": actual, "expected": specification.expected},
            evidence_refs=[f"execution://{task_id}/{path}"],
        )


_FACTORY = VerifierFactory()


def deterministic_verification_available(state: PolyaState) -> bool:
    """Controller-safe probe for complete deterministic coverage."""
    return _FACTORY.can_execute_completely(state)


def verifier_factory_capability() -> FunctionCapability:
    """Expose synthesis and execution through the governed capability registry."""
    definition = CapabilityDefinition(
        name="verifier_factory",
        version=VERIFIER_FACTORY_VERSION,
        supported_actions={CognitiveActionType.VERIFY},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.01,
        kind=CapabilityKind.DETERMINISTIC,
    )
    executor = DeterministicVerifierExecutor()

    def execute(action: CognitiveActionCandidate, state: PolyaState) -> CognitiveObservation:
        suite = _FACTORY.synthesize(state)
        result = executor.execute(suite, state)
        synthesis_event = StateEvent(
            engine_name=definition.name,
            event_type=VERIFIER_SUITE_EVENT,
            reasoning_mode=ReasoningMode.VERIFY,
            summary=f"Synthesized {len(suite.specifications)} criterion-bound verifier(s).",
            metadata=suite.model_dump(mode="json"),
        )
        result_event = StateEvent(
            engine_name=definition.name,
            event_type=VERIFIER_RESULT_EVENT,
            reasoning_mode=ReasoningMode.VERIFY,
            summary=(
                "The executable verifier suite passed."
                if result.passed
                else "The executable verifier suite failed or remained inconclusive."
            ),
            metadata=result.model_dump(mode="json"),
        )
        hypothesis = state["hypotheses"][0].statement if len(state["hypotheses"]) == 1 else None
        problem = state["structured_problem"]
        if (
            result.passed
            and problem is not None
            and problem.problem_type == "source_patch_investigation"
            and len(state["plan"]) == 1
            and state["plan"][0].tool_name == "source_patch_sandbox"
        ):
            hypothesis = source_patch_conclusion(state["plan"][0].params)
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=result_event.summary,
            payload={
                "procedure": "deterministic",
                "model_calls": 0,
                "verifiers": len(result.results),
            },
            proposed_update=CognitiveStateUpdate(
                verification=result.report,
                final_answer=hypothesis if result.passed else None,
                reflection=(
                    Reflection(
                        outcome_summary="Accepted the candidate after criterion-bound verification.",
                        what_worked=[
                            "Compiled declared criteria into independent deterministic checks."
                        ],
                        reusable_lessons=[
                            "Reuse the verifier shape only when its applicability remains true."
                        ],
                        strategy_notes=["criterion_bound_deterministic_verification"],
                    )
                    if result.passed
                    else None
                ),
                trace_events_to_add=[synthesis_event, result_event],
            ),
        )

    return FunctionCapability(definition, execute)
