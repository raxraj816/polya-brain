"""End-to-end tests for the experimental one-call source-patch loop."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.cognition import (
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveKernel,
    CognitiveModelGateway,
    CognitiveRunStatus,
    apply_cognitive_observation,
    source_patch_investigator_capability,
    verifier_factory_capability,
)
from app.execution import DockerPythonSandbox, source_patch_sandbox_capability
from app.execution.source_patch import SourcePatchTask, _diagnosis_grounded
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.models.contracts import EvidenceItem, ReasoningMode, StructuredProblem


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return (
        subprocess.run(
            ["docker", "image", "inspect", "python:3.14-alpine"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def _ready_state(source: Path, check: Path) -> PolyaState:
    state = create_initial_state("Investigate the explicit Python failure.", session_id="patch")
    state["structured_problem"] = StructuredProblem(
        core_question="Why does the path writer fail and what exact edit fixes it?",
        problem_type="field_derived_technical_investigation",
        knowns=["The supplied check fails with NameError."],
        constraints=["Use only admitted source and check artifacts."],
        success_criteria=[
            "Identify the concrete failure mechanism.",
            "Name the implicated artifact or function.",
            "Recommend the smallest semantically correct correction.",
            "Specify an executable regression check without fabricating its execution.",
        ],
    )
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_local_artifact",
            source_uri=source.as_uri(),
            claim="The closure opens output_path although the parameter is output.",
            raw_excerpt=source.read_text(encoding="utf-8"),
            reliability_score=0.9,
            relevance_score=1.0,
        ),
        EvidenceItem(
            source_type="evaluated_local_artifact",
            source_uri=check.as_uri(),
            claim="The check writes through a Path and asserts the exact content.",
            raw_excerpt=check.read_text(encoding="utf-8"),
            reliability_score=0.9,
            relevance_score=1.0,
        ),
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints completed.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="task_gap_detector",
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="No acquisition gap remains.",
            metadata={"status": "ok", "gap_count": 0},
        ),
    ]
    return state


def _proposal_response(source: Path, check: Path) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="same-fake-model",
        text=json.dumps(
            {
                "diagnosis": (
                    "get_write_function captures output, but the inner writer references "
                    "undefined output_path and raises NameError."
                ),
                "implicated_source_uri": source.as_uri(),
                "old_text": "output_path",
                "new_text": "output",
                "correction_rationale": (
                    "The exact edit makes the closure use its enclosing path argument."
                ),
                "regression_check_uri": check.as_uri(),
                "regression_check_summary": (
                    "Run verify with a Path, write trace-line, and assert the file content."
                ),
                "remaining_uncertainty": [],
            }
        ),
        finish_reason="stop",
        usage=LLMTokenUsage(input_tokens=100, output_tokens=60),
    )


def _proposal_response_with(
    source: Path,
    check: Path,
    **updates: str,
) -> LLMResponse:
    payload = json.loads(_proposal_response(source, check).text)
    payload.update(updates)
    return _proposal_response(source, check).model_copy(update={"text": json.dumps(payload)})


def _fixture_files(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "buggy_impl.py"
    source.write_text(
        """from pathlib import Path

def get_write_function(output: Path | str):
    def write(value: str) -> None:
        with open(output_path, "a") as stream:
            stream.write(value)
    return write
""",
        encoding="utf-8",
    )
    check = tmp_path / "check.py"
    check.write_text(
        """from pathlib import Path

def verify(implementation):
    output = Path(__file__).with_name("result.txt")
    output.unlink(missing_ok=True)
    try:
        implementation.get_write_function(output)("trace-line")
        assert output.read_text() == "trace-line"
    finally:
        output.unlink(missing_ok=True)
""",
        encoding="utf-8",
    )
    return source, check


def test_controller_selects_one_call_source_patch_proposal(tmp_path: Path) -> None:
    source, check = _fixture_files(tmp_path)
    client = FakeLLMClient([_proposal_response(source, check)])
    registry = CapabilityRegistry()
    registry.register(
        source_patch_investigator_capability(CognitiveModelGateway(client, "same-fake-model"))
    )

    result = CognitiveKernel(registry).run(_ready_state(source, check), max_cycles=1)

    assert result.decisions[0].selected.capability == "source_patch_investigator"
    assert len(client.requests) == 1
    assert len(result.state["hypotheses"]) == 1
    assert result.state["plan"][0].tool_name == "source_patch_sandbox"
    assert result.state["execution_outputs"] == []

    request_payload = json.loads(client.requests[0].messages[1].content)
    projected = request_payload["current_state"]
    assert set(projected) == {
        "admitted_evidence",
        "constraints",
        "observed_failure",
        "problem",
        "projection_version",
        "success_criteria",
    }
    assert projected["projection_version"] == "source_patch_context@0.1.0"
    assert len(projected["admitted_evidence"]) == 2
    assert "Investigate the explicit Python failure" not in json.dumps(projected)


def test_source_patch_resolves_unique_admitted_filenames_deterministically(
    tmp_path: Path,
) -> None:
    source, check = _fixture_files(tmp_path)
    client = FakeLLMClient(
        [
            _proposal_response_with(
                source,
                check,
                implicated_source_uri=source.name,
                regression_check_uri=check.name,
            )
        ]
    )
    registry = CapabilityRegistry()
    registry.register(
        source_patch_investigator_capability(CognitiveModelGateway(client, "same-fake-model"))
    )

    result = CognitiveKernel(registry).run(_ready_state(source, check), max_cycles=1)

    assert result.observations[0].status.value == "succeeded"
    assert result.state["plan"][0].params["source_uri"] == source.as_uri()
    assert result.state["plan"][0].params["check_uri"] == check.as_uri()
    assert len(client.requests) == 1


def test_source_patch_guard_preserves_reason_and_spent_usage(tmp_path: Path) -> None:
    source, check = _fixture_files(tmp_path)
    client = FakeLLMClient(
        [_proposal_response_with(source, check, old_text="not present in admitted source")]
    )
    registry = CapabilityRegistry()
    registry.register(
        source_patch_investigator_capability(CognitiveModelGateway(client, "same-fake-model"))
    )

    result = CognitiveKernel(registry).run(_ready_state(source, check), max_cycles=1)
    observation = result.observations[0]

    assert observation.status.value == "failed"
    assert observation.failure_kind == "source_patch_edit_not_unique"
    assert observation.payload["model_calls"] == 1
    assert observation.payload["usage"] == {
        "cached_input_tokens": 0,
        "estimated_cost_usd": None,
        "input_tokens": 100,
        "output_tokens": 60,
        "reasoning_tokens": 0,
    }
    assert observation.payload["old_text_occurrences_in_excerpt"] == 0


def test_source_patch_matches_multiline_edit_without_inspector_line_prefixes(
    tmp_path: Path,
) -> None:
    source, check = _fixture_files(tmp_path)
    state = _ready_state(source, check)
    source_evidence = state["evidence"][0]
    numbered = "\n".join(
        f"{index}: {line}"
        for index, line in enumerate(
            (source_evidence.raw_excerpt or "").splitlines(),
            start=1,
        )
    )
    state["evidence"][0] = source_evidence.model_copy(update={"raw_excerpt": numbered})
    old_text = 'with open(output_path, "a") as stream:\n            stream.write(value)'
    new_text = 'with open(output, "a") as stream:\n            stream.write(value)'
    client = FakeLLMClient(
        [
            _proposal_response_with(
                source,
                check,
                old_text=old_text,
                new_text=new_text,
            )
        ]
    )
    registry = CapabilityRegistry()
    registry.register(
        source_patch_investigator_capability(CognitiveModelGateway(client, "same-fake-model"))
    )

    result = CognitiveKernel(registry).run(state, max_cycles=1)

    assert result.observations[0].status.value == "succeeded"
    assert result.state["plan"][0].params["old_text"] == old_text


def test_diagnosis_grounding_uses_edit_context_and_changed_concept() -> None:
    params = SourcePatchTask(
        source_uri="file:///case/buggy_impl.py",
        check_uri="file:///case/check.py",
        old_text=('for name, value in request_headers.items():\n    value = value.decode("utf8")'),
        new_text=(
            "for name, value in request_headers.items():\n"
            "    if value is None:\n"
            "        continue\n"
            '    value = value.decode("utf8")'
        ),
        diagnosis=(
            "update_headers receives None and unconditionally calls value.decode instead of "
            "omitting the unset header."
        ),
        verification=[],
    )

    assert _diagnosis_grounded(params) is True
    assert (
        _diagnosis_grounded(params.model_copy(update={"diagnosis": "The network is slow."}))
        is False
    )


def test_diagnosis_grounding_preserves_changed_qualified_identifier() -> None:
    params = SourcePatchTask(
        source_uri="file:///case/buggy_impl.py",
        check_uri="file:///case/check.py",
        old_text=('value = {"name": response.name, "note": response.note}\nreturn dict(value)'),
        new_text="return response.dict(skip_defaults=skip_defaults)",
        diagnosis=("Manual response attributes bypass response.dict, so skip_defaults is ignored."),
        verification=[],
    )

    assert _diagnosis_grounded(params) is True
    assert (
        _diagnosis_grounded(
            params.model_copy(
                update={
                    "diagnosis": (
                        "serialize_response ignores skip_defaults instead of delegating to "
                        "ResponseModel.dict."
                    )
                }
            )
        )
        is True
    )


@pytest.mark.parametrize("change", ["source", "check", "partial", "missing", "line_identity"])
def test_source_patch_rejects_unbound_snapshots_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    source, check = _fixture_files(tmp_path)
    state = _ready_state(source, check)
    client = FakeLLMClient([_proposal_response(source, check)])
    registry = CapabilityRegistry()
    registry.register(
        source_patch_investigator_capability(CognitiveModelGateway(client, "same-fake-model"))
    )
    proposed = CognitiveKernel(registry).run(state, max_cycles=1)
    if change == "source":
        source.write_text(source.read_text() + "\nraise RuntimeError('unseen source')\n")
    elif change == "check":
        check.write_text("def verify(implementation):\n    pass\n")
    elif change == "partial":
        item = proposed.state["evidence"][0]
        proposed.state["evidence"][0] = item.model_copy(
            update={
                "source_uri": source.as_uri() + "#L1-L1",
                "raw_excerpt": "1: from pathlib import Path",
            }
        )
    elif change == "missing":
        proposed.state["evidence"][1] = proposed.state["evidence"][1].model_copy(
            update={"raw_excerpt": None},
        )
    else:
        lines = source.read_text().splitlines()
        proposed.state["evidence"][0] = proposed.state["evidence"][0].model_copy(
            update={
                "source_uri": source.as_uri() + f"#L1-L{len(lines)}",
                "raw_excerpt": "\n".join(f"{i + 2}: {line}" for i, line in enumerate(lines)),
            }
        )

    sandbox = DockerPythonSandbox()

    def forbidden_execution(*args: object, **kwargs: object) -> None:
        pytest.fail("an unbound snapshot reached the sandbox")

    monkeypatch.setattr(sandbox, "execute", forbidden_execution)
    capability = source_patch_sandbox_capability(sandbox, [tmp_path])
    observation = capability.execute(
        CognitiveActionCandidate(
            id="snapshot-check",
            action_type=CognitiveActionType.EXECUTE,
            target="verify-source-patch",
            capability="source_patch_sandbox",
            purpose="Verify an evidence-bound correction.",
            expected_observation="A checked patch.",
            expected_usefulness=0.95,
            estimated_cost=0.08,
            success_condition="The admitted check passes.",
            failure_condition="Snapshot changed.",
        ),
        proposed.state,
    )

    assert observation.status.value == "failed"
    assert observation.failure_kind == "source_patch_boundary_failure"
    assert not observation.proposed_update.execution_outputs_to_add


@pytest.mark.skipif(not _docker_available(), reason="requires the pinned Docker sandbox image")
@pytest.mark.parametrize("numbered", [False, True])
def test_passing_isolated_patch_enables_zero_call_deterministic_finalization(
    tmp_path: Path,
    numbered: bool,
) -> None:
    source, check = _fixture_files(tmp_path)
    original_source = source.read_text(encoding="utf-8")
    client = FakeLLMClient([_proposal_response(source, check)])
    proposal_registry = CapabilityRegistry()
    proposal_registry.register(
        source_patch_investigator_capability(CognitiveModelGateway(client, "same-fake-model"))
    )
    state = _ready_state(source, check)
    if numbered:
        for index, path in enumerate((source, check)):
            lines = path.read_text().splitlines()
            state["evidence"][index] = state["evidence"][index].model_copy(
                update={
                    "source_uri": path.as_uri() + f"#L1-L{len(lines)}",
                    "raw_excerpt": "\n".join(
                        f"{number}: {line}" for number, line in enumerate(lines, 1)
                    ),
                }
            )
    proposed = CognitiveKernel(proposal_registry).run(state, max_cycles=1)
    sandbox_capability = source_patch_sandbox_capability(
        DockerPythonSandbox(),
        [tmp_path],
    )
    execution = sandbox_capability.execute(
        CognitiveActionCandidate(
            id="execute-source-patch",
            action_type=CognitiveActionType.EXECUTE,
            target="verify-source-patch",
            purpose="Run the admitted regression check in isolation.",
            expected_observation="A structured patch verification result.",
            expected_usefulness=0.95,
            estimated_cost=0.08,
            capability="source_patch_sandbox",
            success_condition="The independent check passes.",
            failure_condition="The edit or check fails.",
        ),
        proposed.state,
    )
    executed_state = apply_cognitive_observation(proposed.state, execution)
    verifier_registry = CapabilityRegistry()
    verifier_registry.register(verifier_factory_capability())

    final = CognitiveKernel(verifier_registry).run(executed_state, max_cycles=2)

    assert execution.payload["patch_verified"] is True
    output = execution.proposed_update.execution_outputs_to_add[0].output
    assert isinstance(output, dict)
    assert len(output["source_snapshot_sha256"]) == 64
    assert len(output["check_snapshot_sha256"]) == 64
    assert source.read_text(encoding="utf-8") == original_source
    assert final.status is CognitiveRunStatus.COMPLETED
    assert final.state["verification"] is not None
    assert final.state["verification"].passed is True
    assert "replace 'output_path' with 'output'" in (final.state["final_answer"] or "")
    assert len(client.requests) == 1
