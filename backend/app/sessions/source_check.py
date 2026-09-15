"""Admit browser-selected snapshots into the existing bounded source/check runtime."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, Self

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.cognition.bootstrap import build_cognitive_runtime
from app.cognition.session_runner import CognitiveSessionRunner
from app.config import Settings
from app.graph.state import StateEvent
from app.investigator.source_patch import source_patch_state
from app.models.contracts import ContractModel, NonEmptyStr
from app.sessions.service import SessionExecutionResult
from app.tracing.sanitization import sanitize_text


class SourceCheckRequest(ContractModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, strict=True)
    raw_input: NonEmptyStr = Field(max_length=20000)
    source_code: str = Field(min_length=1, max_length=18000)
    check_code: str = Field(min_length=1, max_length=18000)
    execution_approved: Literal[True]
    provider_approved: Literal[True]

    @field_validator("execution_approved", "provider_approved", mode="before")
    @classmethod
    def explicit_consent(cls, value: object) -> Literal[True]:
        if value is not True:
            raise ValueError(
                "Explicit boolean consent is required for execution and provider access."
            )
        return True

    @model_validator(mode="after")
    def validate_snapshots(self) -> Self:
        texts = [self.source_code, self.check_code]
        if any(not text.strip() or "\x00" in text for text in texts):
            raise ValueError(
                "Source and check must contain nonempty Python text without NUL bytes."
            )
        if sum(len(repr(text)) for text in texts) > 18000:
            raise ValueError(
                "The source and check exceed the bounded sandbox payload (18,000 escaped characters)."
            )
        if any(sanitize_text(text) != text for text in texts):
            raise ValueError(
                "A selected snapshot contains secret-like data. Remove it before submitting; executable snapshots are never silently redacted."
            )
        return self


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def input_metadata(request: SourceCheckRequest) -> dict[str, Any]:
    return {
        **request.model_dump(mode="json"),
        "source_sha256": content_hash(request.source_code),
        "check_sha256": content_hash(request.check_code),
    }


def validated_input(metadata: dict[str, Any]) -> SourceCheckRequest:
    request = SourceCheckRequest.model_validate(
        {
            key: value
            for key, value in metadata.items()
            if key not in {"source_sha256", "check_sha256"}
        }
    )
    if metadata.get("source_sha256") != content_hash(request.source_code) or metadata.get(
        "check_sha256"
    ) != content_hash(request.check_code):
        raise ValueError("The stored source/check snapshots changed after admission.")
    return request


class SourceCheckSessionRunner:
    def __init__(
        self,
        settings: Settings,
        metadata: dict[str, Any],
        *,
        progress_writer: Callable[[str, list[StateEvent]], None],
    ) -> None:
        self.settings = settings
        self.metadata = metadata
        self.progress_writer = progress_writer

    def __call__(self, raw_input: str, *, session_id: str) -> SessionExecutionResult:
        if not self.settings.code_execution_enabled:
            raise ValueError("Source/check execution is disabled in the backend configuration.")
        request = validated_input(self.metadata)
        with TemporaryDirectory(prefix="polyabrain-source-check-") as temporary:
            root = Path(temporary)
            source, check = root / "source.py", root / "check.py"
            for path, content in ((source, request.source_code), (check, request.check_code)):
                path.write_text(content, encoding="utf-8")
                path.chmod(0o600)
            settings = self.settings.model_copy(update={"artifact_allowed_roots": str(root)})
            state = source_patch_state(raw_input, source, check, settings)
            state["session_id"] = session_id
            runner = CognitiveSessionRunner(
                build_cognitive_runtime(settings, enable_source_patch=True),
                progress_writer=self.progress_writer,
                initial_state=state,
            )
            return runner(raw_input, session_id=session_id)
