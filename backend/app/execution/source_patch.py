"""Governed in-memory source patch execution against an admitted Python check."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pydantic import JsonValue, model_validator

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.cognition.verification_factory import verification_declarations_validated_event
from app.execution.sandbox import DockerPythonSandbox
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import ContractModel, EvidenceItem, NonEmptyStr, ReasoningMode, RiskLevel

SOURCE_PATCH_SANDBOX_VERSION = "source_patch_sandbox@0.3.0"
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_QUALIFIED_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


class SourcePatchTask(ContractModel):
    """Validated plan parameters accepted by the source-patch sandbox."""

    source_uri: NonEmptyStr
    check_uri: NonEmptyStr
    old_text: NonEmptyStr
    new_text: NonEmptyStr
    diagnosis: NonEmptyStr
    verification: list[dict[str, JsonValue]]

    @model_validator(mode="after")
    def task_must_change_one_bounded_fragment(self) -> SourcePatchTask:
        if self.old_text == self.new_text:
            raise ValueError("source patch task must change text")
        if max(len(self.old_text), len(self.new_text)) > 800:
            raise ValueError("source patch fragment exceeds the bounded edit size")
        return self


def _contained_file(uri: str, roots: tuple[Path, ...]) -> Path:
    parsed = urlsplit(uri)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"} or parsed.query:
        raise ValueError("source patch artifacts require local file provenance")
    path = Path(unquote(parsed.path)).resolve(strict=True)
    if not path.is_file() or path.suffix.casefold() != ".py":
        raise ValueError("source patch artifacts must be existing Python files")
    if not any(path.is_relative_to(root) for root in roots):
        raise ValueError("source patch artifact is outside the allowlisted roots")
    if path.stat().st_size > 100_000:
        raise ValueError("source patch artifact exceeds the size boundary")
    return path


def _sandbox_program(source: str, check: str) -> str:
    return f"""import sys
from types import ModuleType

__pb_source = {source!r}
__pb_check_source = {check!r}
implementation = ModuleType("polyabrain_patched_implementation")
implementation.__file__ = "/tmp/buggy_impl.py"
sys.modules[implementation.__name__] = implementation
exec(compile(__pb_source, implementation.__file__, "exec"), implementation.__dict__)
check = ModuleType("polyabrain_independent_check")
check.__file__ = "/tmp/check.py"
sys.modules[check.__name__] = check
exec(compile(__pb_check_source, check.__file__, "exec"), check.__dict__)
"""


def _base_uri(uri: str) -> str:
    return uri.split("#", maxsplit=1)[0]


def _admitted_snapshot_hash(uri: str, content: str, evidence: list[EvidenceItem]) -> str:
    """Bind execution to complete admitted text, including inspector line identity.

    A path is provenance, not an immutable snapshot. Never execute unseen lines
    or a file modified since admission just because its path still matches.
    """
    admitted = [
        item
        for item in evidence
        if item.source_uri is not None and _base_uri(item.source_uri) == _base_uri(uri)
    ]
    if not admitted:
        raise ValueError("source patch snapshot was not admitted")
    content_lines = content.splitlines()
    for item in admitted:
        if not item.raw_excerpt:
            raise ValueError("source patch requires a complete admitted excerpt")
        excerpt_lines = item.raw_excerpt.splitlines()
        fragment = urlsplit(item.source_uri or "").fragment
        if fragment:
            if fragment != f"L1-L{len(content_lines)}":
                raise ValueError("source patch cannot execute a partially admitted file")
            expected_lines = [f"{index}: {line}" for index, line in enumerate(content_lines, 1)]
        else:
            expected_lines = content_lines
        if excerpt_lines != expected_lines:
            raise ValueError("source patch file differs from its admitted snapshot")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _diagnosis_grounded(params: SourcePatchTask) -> bool:
    def semantic_terms(text: str) -> set[str]:
        return {
            item.casefold()
            for expression in (_IDENTIFIER, _QUALIFIED_IDENTIFIER)
            for item in expression.findall(text)
        }

    old_terms = semantic_terms(params.old_text)
    new_terms = semantic_terms(params.new_text)
    diagnosis_terms = semantic_terms(params.diagnosis)
    edit_context_terms = old_terms | new_terms
    return len(edit_context_terms & diagnosis_terms) >= 2


def source_patch_sandbox_capability(
    sandbox: DockerPythonSandbox,
    allowed_roots: list[Path],
) -> FunctionCapability:
    """Apply one exact edit only inside the existing isolated Python sandbox."""
    roots = tuple(dict.fromkeys(root.resolve(strict=True) for root in allowed_roots))
    if not roots or any(not root.is_dir() for root in roots):
        raise ValueError("source patch sandbox requires allowlisted directories")
    definition = CapabilityDefinition(
        name="source_patch_sandbox",
        version=SOURCE_PATCH_SANDBOX_VERSION,
        supported_actions={CognitiveActionType.EXECUTE},
        risk_level=RiskLevel.MEDIUM,
        approved_for_sensitive_data=False,
        timeout_seconds=2 * (sandbox.limits.timeout_seconds + 3),
        estimated_cost=0.16,
    )

    def execute(action: CognitiveActionCandidate, state: PolyaState) -> CognitiveObservation:
        task = next((item for item in state["plan"] if item.id == action.target), None)
        if task is None or task.tool_name != definition.name:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary="The source-patch task is missing or assigned to another capability.",
                failure_kind="source_patch_task_invalid",
            )
        try:
            params = SourcePatchTask.model_validate(task.params)
            source_path = _contained_file(params.source_uri, roots)
            check_path = _contained_file(params.check_uri, roots)
            if source_path == check_path or source_path.parent != check_path.parent:
                raise ValueError("source and check must be distinct files in one case directory")
            source = source_path.read_text(encoding="utf-8")
            check = check_path.read_text(encoding="utf-8")
            source_hash = _admitted_snapshot_hash(params.source_uri, source, state["evidence"])
            check_hash = _admitted_snapshot_hash(params.check_uri, check, state["evidence"])
            source_admitted = True
            if source.count(params.old_text) != 1:
                raise ValueError("source patch old text must occur exactly once")
            patched = source.replace(params.old_text, params.new_text, 1)
            edit_applied = patched != source and params.new_text in patched
            diagnosis_grounded = _diagnosis_grounded(params)
            baseline = sandbox.execute(
                _sandbox_program(source, check),
                ["check.verify(implementation)"],
            )
            result = sandbox.execute(
                _sandbox_program(patched, check),
                ["check.verify(implementation)"],
            )
        except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as exc:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary=f"Source-patch verification failed at a governed boundary ({type(exc).__name__}).",
                failure_kind="source_patch_boundary_failure",
            )
        baseline_failed = bool(
            baseline.exit_code != 0
            and not baseline.timed_out
            and not baseline.output_truncated
            and baseline.tests_run == 1
            and len(baseline.test_results) == 1
            and not baseline.test_results[0].passed
        )
        patch_verified = bool(
            baseline_failed
            and result.exit_code == 0
            and not result.timed_out
            and not result.output_truncated
            and result.tests_run == 1
            and len(result.test_results) == 1
            and result.test_results[0].passed
        )
        summary = (
            "The admitted regression check failed on the original source and passed on the candidate edit."
            if patch_verified
            else "The candidate edit did not establish a failing-original / passing-patched regression check."
        )
        correction_verified = edit_applied and patch_verified
        check_admitted_and_passed = source_admitted and patch_verified
        output = ExecutionOutput(
            task_id=task.id,
            summary=summary,
            output={
                "patch_verified": patch_verified,
                "baseline_failed": baseline_failed,
                "baseline": baseline.model_dump(mode="json"),
                "patched": result.model_dump(mode="json"),
                "verification_scope": "supplied_regression_check",
                "diagnosis_grounded": diagnosis_grounded,
                "source_admitted": source_admitted,
                "edit_applied": edit_applied,
                "correction_verified": correction_verified,
                "check_admitted_and_passed": check_admitted_and_passed,
                "replacement_count": 1,
                "tests_run": result.tests_run,
                "exit_code": result.exit_code,
                "source_uri": params.source_uri,
                "check_uri": params.check_uri,
                "source_snapshot_sha256": source_hash,
                "check_snapshot_sha256": check_hash,
                "patched_source_sha256": hashlib.sha256(patched.encode("utf-8")).hexdigest(),
                "sandbox_network": "none",
                "sandbox_root_filesystem": "read_only",
            },
            error=None if patch_verified else "The admitted regression check did not pass.",
        )
        events = [
            StateEvent(
                engine_name=definition.name,
                event_type="source_patch_sandbox_completed",
                reasoning_mode=ReasoningMode.EXECUTE,
                summary=summary,
                metadata={
                    "patch_verified": patch_verified,
                    "baseline_failed": baseline_failed,
                    "baseline_exit_code": baseline.exit_code,
                    "baseline_tests_run": baseline.tests_run,
                    "diagnosis_grounded": diagnosis_grounded,
                    "source_admitted": source_admitted,
                    "edit_applied": edit_applied,
                    "correction_verified": correction_verified,
                    "check_admitted_and_passed": check_admitted_and_passed,
                    "exit_code": result.exit_code,
                    "tests_run": result.tests_run,
                    "runtime_ms": baseline.runtime_ms + result.runtime_ms,
                    "network": "none",
                    "root_filesystem": "read_only",
                    "host_mounts": 0,
                    "source_snapshot_sha256": source_hash,
                    "check_snapshot_sha256": check_hash,
                },
            )
        ]
        if patch_verified:
            events.append(verification_declarations_validated_event(state))
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=summary,
            payload={
                "procedure": "deterministic_sandbox",
                "model_calls": 0,
                "patch_verified": patch_verified,
                "runtime_ms": baseline.runtime_ms + result.runtime_ms,
            },
            evidence=[
                EvidenceItem(
                    source_type="isolated_source_patch_execution",
                    source_uri=f"sandbox://{action.id}",
                    claim=summary,
                    raw_excerpt=(
                        f"exit_code={result.exit_code}; tests_run={result.tests_run}; "
                        f"patch_verified={patch_verified}"
                    ),
                    reliability_score=1.0,
                    relevance_score=1.0,
                )
            ],
            proposed_update=CognitiveStateUpdate(
                execution_outputs_to_add=[output],
                trace_events_to_add=events,
            ),
        )

    return FunctionCapability(definition, execute)
