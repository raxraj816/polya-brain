"""Private, inspectable artifacts derived from actual cognitive-run outcomes."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from pydantic import JsonValue, TypeAdapter

from app.cognition.contracts import CognitiveRunStatus
from app.cognition.kernel import CognitiveRunResult
from app.cognition.report_metadata import REPORT_METADATA_EVENT, report_questions
from app.cognition.source_patch_report import source_patch_checks, source_patch_conclusion
from app.cognition.task_model import accumulated_usage, configured_budget
from app.graph.state import PolyaState
from app.models.sessions import SessionReportEvidence, SessionReportResponse
from app.tracing.sanitization import sanitize_json_value, sanitize_text


def report_from_result(result: CognitiveRunResult) -> SessionReportResponse:
    """Reuse the public report shape without requiring database persistence."""
    state = result.state
    verification = state["verification"]
    verified = result.status is CognitiveRunStatus.COMPLETED and bool(
        verification and verification.passed and state["final_answer"]
    )
    used = [item for item in state["evidence"] if not item.contradicts_hypothesis_ids]
    against = [item for item in state["evidence"] if item.contradicts_hypothesis_ids]
    questions = [item.description for item in state["gaps"] if not item.filled]
    metadata_event = next(
        (event for event in reversed(state["events"]) if event.event_type == REPORT_METADATA_EVENT),
        None,
    )
    if verified and metadata_event is not None:
        questions.extend(report_questions(metadata_event.metadata, state["final_answer"]))
    if result.status is CognitiveRunStatus.NEEDS_INPUT:
        for observation in reversed(result.observations):
            if observation.proposed_update.questions_to_ask:
                questions = [*observation.proposed_update.questions_to_ask, *questions]
                break
    reflection = state["reflection"]
    conclusion = state["final_answer"] if verified else "No verified conclusion is available."
    if verified:
        patch_task = next(
            (task for task in state["plan"] if task.tool_name == "source_patch_sandbox"), None
        )
        if patch_task is not None:
            # The proposal was written before execution. Its future-tense check
            # statements must not masquerade as the current measured outcome.
            conclusion = source_patch_conclusion(patch_task.params)
            questions.append(
                "Do additional integration or regression checks support this candidate edit?"
            )
    next_action = (
        "Review the evidence and checks before acting on the conclusion."
        if verified
        else "Supply the missing evidence or resolve the reported failure, then run again."
    )
    if result.status is CognitiveRunStatus.MAX_CYCLES:
        next_action = "Resume this run with the original runtime options to continue within its remaining resource budget."
    if reflection and reflection.follow_up_actions:
        next_action = reflection.follow_up_actions[0]
    if result.status is CognitiveRunStatus.NEEDS_INPUT:
        next_action = "Resume this run with --answer containing the full revised problem and the original runtime options."

    def concise(items: list[object]) -> list[SessionReportEvidence]:
        return [SessionReportEvidence.model_validate(item, from_attributes=True) for item in items]

    confidence = "insufficient_evidence"
    if verified:
        confidence = "medium"
        if used and all(
            item.reliability_score is not None and item.reliability_score >= 0.9 for item in used
        ):
            confidence = "high"
        if any(task.tool_name == "source_patch_sandbox" for task in state["plan"]):
            confidence = "medium"
    elif verification is not None:
        confidence = "low"
    return SessionReportResponse(
        session_id=UUID(state["session_id"]),
        final_conclusion=conclusion,
        confidence_level=confidence,
        verification_status="passed" if verified else result.status.value,
        evidence_used=concise(list(used)),
        evidence_against=concise(list(against)),
        checks_performed=(
            source_patch_checks()
            if verified and any(task.tool_name == "source_patch_sandbox" for task in state["plan"])
            else verification.checks_run
            if verification
            else []
        ),
        failed_checks=verification.failed_checks if verification else [],
        contradictions=verification.contradictions if verification else [],
        open_questions=list(dict.fromkeys(questions)),
        recommended_next_action=next_action,
        reflection=reflection.model_dump(mode="json") if reflection else None,
        audit_trace_path="trace.json",
    )


def _write_private(path: Path, content: str) -> None:
    # Exclusive creation prevents replacing an existing report or following a symlink.
    with open(
        path, "x", encoding="utf-8", opener=lambda name, flags: os.open(name, flags, 0o600)
    ) as stream:
        stream.write(content)


def write_json(path: Path, payload: JsonValue) -> None:
    """Write sanitized JSON exclusively, with owner-only permissions."""
    _write_private(
        path, json.dumps(sanitize_json_value(payload), indent=2, ensure_ascii=False) + "\n"
    )


def _code_provenance() -> dict[str, JsonValue]:
    repository = Path(__file__).resolve().parents[3]
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except OSError, subprocess.SubprocessError:
        return {"git_commit": None, "worktree_dirty": None}
    return {"git_commit": head.stdout.strip(), "worktree_dirty": bool(status.stdout.strip())}


def export_run(
    result: CognitiveRunResult, directory: Path, *, elapsed_ms: float
) -> SessionReportResponse:
    """Export actual state plus a user report; never reconstruct a template answer."""
    report = SessionReportResponse.model_validate(
        sanitize_json_value(report_from_result(result).model_dump(mode="json"))
    )
    state = cast(
        dict[str, JsonValue], TypeAdapter(PolyaState).dump_python(result.state, mode="json")
    )
    usage = accumulated_usage(result.state)
    budget = configured_budget(result.state)
    write_json(directory / "state.json", state)
    for name, key in (
        ("trace", "events"),
        ("evidence", "evidence"),
        ("hypotheses", "hypotheses"),
        ("plan", "plan"),
        ("execution", "execution_outputs"),
        ("verification", "verification"),
        ("reflection", "reflection"),
    ):
        write_json(directory / f"{name}.json", state[key])
    write_json(directory / "report.json", report.model_dump(mode="json"))
    for task in result.state["plan"]:
        if task.tool_name != "source_patch_sandbox":
            continue
        params = task.params
        source_uri, old, new = (
            params.get("source_uri"),
            params.get("old_text"),
            params.get("new_text"),
        )
        if not all(isinstance(value, str) for value in (source_uri, old, new)):
            continue
        assert isinstance(source_uri, str) and isinstance(old, str) and isinstance(new, str)
        original = next(
            (
                item.raw_excerpt
                for item in result.state["evidence"]
                if item.source_uri == source_uri and item.raw_excerpt
            ),
            None,
        )
        if original is None or original.count(old) != 1:
            continue
        write_json(
            directory / "candidate_edit.json",
            {
                "source_uri": source_uri,
                "old_text": old,
                "new_text": new,
                "source_sha256": hashlib.sha256(original.encode()).hexdigest(),
                "host_files_modified": False,
                "verification_scope": "Supplied regression check only; proposed diagnosis is not independently proven.",
            },
        )
        patch = "".join(
            line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
            for line in difflib.unified_diff(
                original.splitlines(keepends=True),
                original.replace(old, new, 1).splitlines(keepends=True),
                fromfile="original.py",
                tofile="candidate.py",
            )
        )
        _write_private(directory / "candidate.patch", sanitize_text(patch))
        break
    write_json(
        directory / "run.json",
        {
            "artifact_version": "investigator_run@0.2.0",
            "session_id": result.state["session_id"],
            "status": result.status.value,
            "created_at": datetime.now(UTC).isoformat(),
            "cycles": result.cycles,
            "elapsed_ms": round(elapsed_ms, 3),
            "code": _code_provenance(),
            "budget": budget.model_dump(mode="json") if budget else None,
            "usage": usage.model_dump(mode="json"),
            "capabilities_used": cast(
                JsonValue,
                sorted(
                    {
                        str(event.metadata["capability_version"])
                        for event in result.state["events"]
                        if event.event_type == "capability_observation"
                        and isinstance(event.metadata.get("capability_version"), str)
                    }
                    | {observation.capability_version for observation in result.observations}
                ),
            ),
            "limitations": [
                "Verification covers the recorded checks, not every possible failure.",
                "Confidence is a rule-based label, not a calibrated probability.",
                "Normalized cost is a scheduling unit, not a currency amount.",
                "Local recovery requires this host's private store and unchanged code/configuration; in-flight interruptions cannot be replayed.",
            ],
        },
    )

    lines = [
        "# PolyaBrain investigation",
        "",
        report.final_conclusion or "No verified conclusion.",
        "",
        f"Status: {result.status.value} · Verification: {report.verification_status} · Confidence: {report.confidence_level}",
        "",
    ]

    def section(title: str, entries: list[str], empty: str) -> None:
        body = [f"- {entry}" for entry in entries] if entries else [empty]
        lines.extend([f"## {title}", "", *body, ""])

    section(
        "Evidence used",
        [f"{item.claim} — {item.source_uri or item.source_type}" for item in report.evidence_used],
        "No evidence admitted.",
    )
    section(
        "Evidence against",
        [
            f"{item.claim} — {item.source_uri or item.source_type}"
            for item in report.evidence_against
        ],
        "No opposing evidence recorded; this is not proof that none exists.",
    )
    section("Checks performed", report.checks_performed, "No checks completed.")
    section(
        "Failed checks and contradictions",
        [*report.failed_checks, *report.contradictions],
        "None recorded.",
    )
    section("Open questions", report.open_questions, "None recorded.")
    lines.extend(
        [
            "## Recommended next action",
            "",
            report.recommended_next_action,
            "",
            "## Resources",
            "",
            f"{usage.model_calls} model calls · {usage.input_tokens + usage.output_tokens} tokens · {usage.external_calls} external calls (cumulative). This invocation: {elapsed_ms / 1000:.2f} seconds.",
            "",
            "## Audit trace",
            "",
            "See [trace.json](trace.json), [state.json](state.json), and [run.json](run.json) for actual decisions, evidence, version metadata, budgets, and resource usage.",
            "",
            "Verification is limited to the recorded checks. Confidence is a rule-based label. This local run does not establish general product superiority.",
            "",
        ]
    )
    _write_private(directory / "report.md", sanitize_text("\n".join(lines)))
    manifest = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }
    write_json(
        directory / "manifest.json", cast(JsonValue, {"algorithm": "sha256", "files": manifest})
    )
    return report
