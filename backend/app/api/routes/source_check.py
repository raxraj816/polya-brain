"""Explicit local source/check admission and reviewable candidate edits."""

from __future__ import annotations

import difflib
import shutil
import subprocess
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.config import Settings
from app.db.models import Artifact, PlanTask, ProblemSession, ReasoningEvent
from app.models.contracts import ContractModel
from app.models.sessions import SessionResponse
from app.sessions.source_check import (
    SourceCheckRequest,
    content_hash,
    input_metadata,
    validated_input,
)

router = APIRouter(tags=["source-check"])
DB = Depends(get_db_session)


class SourceCheckAvailability(ContractModel):
    available: bool
    reason: str


def availability(settings: Settings) -> SourceCheckAvailability:
    if not settings.code_execution_enabled:
        return SourceCheckAvailability(
            available=False,
            reason="Enable CODE_EXECUTION_ENABLED in a local backend with Docker access to run source/check investigations.",
        )
    if (
        not settings.openrouter_api_key.get_secret_value().strip()
        or not settings.openrouter_model.strip()
    ):
        return SourceCheckAvailability(
            available=False,
            reason="Configure the backend model provider before requesting a source edit.",
        )
    if shutil.which("docker") is None:
        return SourceCheckAvailability(
            available=False,
            reason="The local backend cannot find Docker. The general Compose API intentionally has no Docker socket access.",
        )
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", settings.code_execution_image],
            capture_output=True,
            timeout=3,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        result = None
    if result is None or result.returncode != 0:
        return SourceCheckAvailability(
            available=False,
            reason="Start Docker and pull the configured pinned sandbox image before running source checks.",
        )
    return SourceCheckAvailability(
        available=True,
        reason="The local backend can run the supplied check in the bounded sandbox.",
    )


@router.get("/api/v1/source-check", response_model=SourceCheckAvailability)
def source_check_availability(request: Request) -> SourceCheckAvailability:
    return availability(request.app.state.settings)


@router.post("/api/v1/source-check", response_model=SessionResponse, status_code=201)
def create_source_check(
    request: Request, payload: SourceCheckRequest, db: Session = DB
) -> SessionResponse:
    gate = availability(request.app.state.settings)
    if not gate.available:
        raise HTTPException(status_code=409, detail=gate.reason)
    session = ProblemSession(
        raw_input=payload.raw_input,
        mode="investigate",
        domain="software_debugging",
        status="created",
    )
    db.add(session)
    db.flush()
    metadata = input_metadata(payload)
    db.add(
        Artifact(
            session_id=session.id,
            artifact_type="source_check_input",
            name="source.py + check.py",
            uri_or_storage_key=f"source-check://{session.id}",
            content_hash=content_hash(payload.source_code + "\x00" + payload.check_code),
            artifact_metadata=metadata,
            source="explicit_user_upload",
            sensitivity="private",
        )
    )
    db.commit()
    db.refresh(session)
    return SessionResponse.model_validate(session)


class CandidateEdit(ContractModel):
    source_sha256: str
    check_sha256: str
    old_text: str
    new_text: str
    patch: str
    verification_status: str
    host_files_modified: bool = False
    scope: str = "Supplied regression check only. Review before applying; causal correctness and broader regression safety remain unproven."


class SourceCheckReview(ContractModel):
    source_check: bool = False
    candidate: CandidateEdit | None = None
    questions: list[str] = Field(default_factory=list)


@router.get("/api/v1/sessions/{session_id}/candidate", response_model=SourceCheckReview)
def get_candidate(session_id: UUID, db: Session = DB) -> SourceCheckReview:
    session = db.get(ProblemSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Problem session not found.")
    artifact = db.scalar(
        select(Artifact).where(
            Artifact.session_id == session_id, Artifact.artifact_type == "source_check_input"
        )
    )
    if artifact is None:
        return SourceCheckReview()
    try:
        admitted = validated_input(artifact.artifact_metadata)
    except ValueError as exc:
        raise HTTPException(
            status_code=409, detail="Stored source/check integrity validation failed."
        ) from exc
    plan = db.scalar(
        select(PlanTask).where(
            PlanTask.session_id == session_id, PlanTask.tool_name == "source_patch_sandbox"
        )
    )
    if plan is None:
        return SourceCheckReview(
            source_check=True, questions=["No bounded candidate edit has been recorded yet."]
        )
    old, new = plan.params.get("old_text"), plan.params.get("new_text")
    if (
        not isinstance(old, str)
        or not old
        or not isinstance(new, str)
        or admitted.source_code.count(old) != 1
    ):
        raise HTTPException(
            status_code=409, detail="Candidate edit does not uniquely match the admitted source."
        )
    if session.verification_status == "passed":
        execution = db.scalar(
            select(ReasoningEvent)
            .where(
                ReasoningEvent.session_id == session_id,
                ReasoningEvent.event_type == "execution_output_recorded",
            )
            .order_by(ReasoningEvent.sequence_number.desc())
            .limit(1)
        )
        measured = execution.event_metadata.get("output") if execution is not None else None
        if (
            not isinstance(measured, dict)
            or not measured.get("patch_verified")
            or measured.get("source_snapshot_sha256") != content_hash(admitted.source_code)
            or measured.get("check_snapshot_sha256") != content_hash(admitted.check_code)
            or measured.get("patched_source_sha256")
            != content_hash(admitted.source_code.replace(old, new, 1))
        ):
            raise HTTPException(
                status_code=409,
                detail="The candidate no longer matches the verified execution snapshots.",
            )
    patch = "".join(
        line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
        for line in difflib.unified_diff(
            admitted.source_code.splitlines(keepends=True),
            admitted.source_code.replace(old, new, 1).splitlines(keepends=True),
            fromfile="original.py",
            tofile="candidate.py",
        )
    )
    return SourceCheckReview(
        source_check=True,
        candidate=CandidateEdit(
            source_sha256=content_hash(admitted.source_code),
            check_sha256=content_hash(admitted.check_code),
            old_text=old,
            new_text=new,
            patch=patch,
            verification_status=session.verification_status or "not_verified",
        ),
    )
