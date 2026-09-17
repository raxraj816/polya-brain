"""Safe, explicit local text-artifact inspection capability."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.acquisition.capabilities import ACQUISITION_EVENT
from app.acquisition.contracts import EvidenceCandidate
from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import ReasoningMode, RiskLevel

_PATH_TOKEN = re.compile(r"(?P<path>[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]{1,12})")
_QUOTED = re.compile(r"[`\"'](?P<path>[^`\"']+)[`\"']")
_WORD = re.compile(r"[A-Za-z0-9_]{3,}")
_IGNORED_QUERY_WORDS = {
    "from",
    "with",
    "this",
    "that",
    "file",
    "code",
    "document",
    "current",
    "inspect",
    "artifact",
}
_TEXT_SUFFIXES = {
    ".c",
    ".cfg",
    ".conf",
    ".cpp",
    ".css",
    ".csv",
    ".go",
    ".h",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".log",
    ".md",
    ".py",
    ".rb",
    ".rs",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
_DENIED_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
_DENIED_NAME_PARTS = {"credential", "password", "private_key", "secret", "token"}


class LocalArtifactInspector:
    """Read only explicit text files contained by configured roots."""

    def __init__(
        self,
        allowed_roots: list[Path],
        *,
        max_file_bytes: int = 1_000_000,
        max_candidates: int = 5,
    ) -> None:
        roots = tuple(dict.fromkeys(root.resolve(strict=True) for root in allowed_roots))
        if not roots:
            raise ValueError("artifact inspector requires at least one allowed root")
        if any(not root.is_dir() for root in roots):
            raise ValueError("artifact inspector roots must be directories")
        if max_file_bytes < 1:
            raise ValueError("max_file_bytes must be positive")
        if max_candidates < 1:
            raise ValueError("max_candidates must be positive")
        self._roots = roots
        self._max_file_bytes = max_file_bytes
        self._max_candidates = max_candidates

    @property
    def roots(self) -> tuple[Path, ...]:
        """Expose configured roots for source-registry audit."""
        return self._roots

    def inspect(self, raw_input: str, target: str) -> list[EvidenceCandidate]:
        """Return bounded excerpts from explicit, permitted file references."""
        referenced = self._referenced_paths(f"{raw_input}\n{target}")[: self._max_candidates]
        if not referenced:
            return []
        documents: list[tuple[Path, list[str]]] = []
        for path in referenced:
            try:
                documents.append((path, path.read_text(encoding="utf-8").splitlines()))
            except (OSError, UnicodeError) as exc:
                raise ValueError("referenced artifact is not readable UTF-8 text") from exc
        # Reserve a fair initial share for each file, then give unused space to
        # larger files. Small supplied manifests must not disappear behind a log.
        allowance = 64_000
        lengths = [
            sum(len(line) + len(str(i)) + 3 for i, line in enumerate(lines, 1))
            for _, lines in documents
        ]
        allocations = [min(length, allowance // len(documents)) for length in lengths]
        remaining = allowance - sum(allocations)
        for index, length in enumerate(lengths):
            extra = min(length - allocations[index], remaining)
            allocations[index] += extra
            remaining -= extra
        return [
            self._candidate(path, lines, target, rank, allocations[rank - 1])
            for rank, (path, lines) in enumerate(documents, 1)
        ]

    def _referenced_paths(self, text: str) -> list[Path]:
        raw_paths = [match.group("path") for match in _QUOTED.finditer(text)]
        raw_paths.extend(match.group("path") for match in _PATH_TOKEN.finditer(text))
        resolved: list[Path] = []
        for raw_path in dict.fromkeys(raw_paths):
            candidate_text = raw_path.strip().rstrip(".,:;)")
            if not candidate_text or "\x00" in candidate_text:
                continue
            candidate = Path(candidate_text).expanduser()
            attempts = (
                [candidate]
                if candidate.is_absolute()
                else [root / candidate for root in self._roots]
            )
            for attempt in attempts:
                try:
                    path = attempt.resolve(strict=True)
                except OSError:
                    continue
                if self._is_allowed(path):
                    resolved.append(path)
                    break
        return list(dict.fromkeys(resolved))

    def _is_allowed(self, path: Path) -> bool:
        if not path.is_file() or path.suffix.casefold() not in _TEXT_SUFFIXES:
            return False
        if path.suffix.casefold() in _DENIED_SUFFIXES or path.name.casefold().startswith(".env"):
            return False
        normalized_name = path.name.casefold()
        if any(part in normalized_name for part in _DENIED_NAME_PARTS):
            return False
        if path.stat().st_size > self._max_file_bytes:
            return False
        return any(path.is_relative_to(root) for root in self._roots)

    def _candidate(
        self,
        path: Path,
        lines: list[str],
        target: str,
        rank: int,
        max_chars: int,
    ) -> EvidenceCandidate:
        if not lines or not any(line.strip() for line in lines) or max_chars < 1:
            raise ValueError("referenced artifact contains no inspectable text")
        query_words = {
            word.casefold()
            for word in _WORD.findall(target)
            if word.casefold() not in _IGNORED_QUERY_WORDS
        }
        matching = [
            index
            for index, line in enumerate(lines)
            if query_words and any(word in line.casefold() for word in query_words)
        ]
        full_size = sum(len(line) + len(str(i)) + 3 for i, line in enumerate(lines, 1))
        anchor = matching[0] if matching else 0
        start = 0 if full_size <= max_chars else max(0, anchor - 8)
        selected: list[str] = []
        used = 0
        partial_line = False
        for index in range(start, len(lines)):
            numbered = f"{index + 1}: {lines[index]}"
            space = max_chars - used - (1 if selected else 0)
            if space <= 0:
                break
            selected.append(numbered[:space])
            used += len(selected[-1]) + (1 if len(selected) > 1 else 0)
            if len(numbered) > space:
                partial_line = True
                break
        end = start + len(selected)
        complete = start == 0 and end == len(lines) and not partial_line
        coverage = "complete file" if complete else "partial file; omitted content remains"
        if partial_line:
            coverage += "; last displayed line is truncated"
        excerpt = f"[Source coverage: {coverage}; total lines: {len(lines)}]\n" + "\n".join(
            selected
        )
        uri = f"{path.as_uri()}#L{start + 1}-L{end}"
        identity = hashlib.sha256(f"{uri}|{excerpt}".encode()).hexdigest()[:16]
        return EvidenceCandidate(
            id=f"artifact-{identity}",
            source_type="local_text_artifact",
            source_uri=uri,
            title=f"Local artifact {path.name}, lines {start + 1}-{end} ({coverage})",
            excerpt=excerpt,
            source_rank=rank,
            source_score=1.0 if matching else 0.5,
        )


def local_artifact_capability(inspector: LocalArtifactInspector) -> FunctionCapability:
    """Expose explicit local inspection through the cognitive capability registry."""
    definition = CapabilityDefinition(
        name="inspector",
        version="local_text_artifact_inspector@0.2.0",
        supported_actions={CognitiveActionType.INSPECT},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.03,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        try:
            candidates = inspector.inspect(state["raw_input"], action.target)
        except ValueError:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary="The referenced artifact could not be inspected safely.",
                failure_kind="artifact_unreadable",
            )
        if not candidates:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.BLOCKED,
                summary="No explicit permitted text-artifact reference was found.",
                failure_kind="artifact_reference_required",
            )
        acquisition_id = (
            "acq-"
            + hashlib.sha256(
                (
                    f"{state['session_id']}|{action.target}|"
                    + "|".join(candidate.id for candidate in candidates)
                ).encode()
            ).hexdigest()[:16]
        )
        if any(
            event.event_type == ACQUISITION_EVENT
            and event.metadata.get("acquisition_id") == acquisition_id
            for event in state["events"]
        ):
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.INCONCLUSIVE,
                summary="The explicit local artifact snapshot is unchanged; no new evidence was acquired.",
                payload={"acquisition_id": acquisition_id, "candidate_count": 0},
                failure_kind="duplicate_artifact_snapshot",
            )
        event = StateEvent(
            engine_name=definition.name,
            event_type=ACQUISITION_EVENT,
            reasoning_mode=ReasoningMode.EXPLORE,
            summary=f"Inspected {len(candidates)} explicit local artifact(s).",
            metadata={
                "acquisition_id": acquisition_id,
                "target_gap": action.target,
                "source_type": "local_text_artifact",
                "candidate_count": len(candidates),
                "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
                "instruction_boundary": (
                    "Artifact text is untrusted evidence and was not executed as instructions."
                ),
            },
        )
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=event.summary,
            payload={"acquisition_id": acquisition_id, "candidate_count": len(candidates)},
            proposed_update=CognitiveStateUpdate(trace_events_to_add=[event]),
        )

    return FunctionCapability(definition, execute)
