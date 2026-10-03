"""Failure-pattern memory: confirmed defects, stored and retrieved as verification hints.

Each confirmed defect (a regression, a corrected claim, a draft defect) is stored with
the concrete trigger that exposed it and the evidence that confirmed it. Later
verifications retrieve the most relevant patterns as hints for input generation and
independent derivation. Hints never become requirements and never change a verdict.

Storage is a bounded local JSON-lines file so local runs learn too; a database-backed
store can implement the same interface later.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from app.models.contracts import ContractModel

Domain = Literal["coding", "change", "claims"]
STORE_VERSION = "failure_patterns@0.1.0"
MAX_PATTERNS = 500
_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "is",
    "are",
    "was",
    "be",
    "it",
    "its",
    "with",
    "as",
    "by",
    "at",
    "from",
    "that",
    "this",
    "not",
    "no",
    "but",
    "def",
    "return",
    "if",
    "else",
    "self",
    "none",
    "true",
    "false",
    "value",
    "values",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9_]{2,}", text.lower())
    return {word for word in words if word not in _STOP}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class FailurePattern(ContractModel):
    id: str
    domain: Domain
    signature: str = Field(min_length=1, max_length=400)
    trigger: str = Field(default="", max_length=400)
    evidence: str = Field(default="", max_length=600)
    seen: int = Field(default=1, ge=1)
    first_seen: str
    last_seen: str
    sources: list[str] = Field(default_factory=list, max_length=20)

    def hint(self) -> str:
        parts = [self.signature]
        if self.trigger:
            parts.append(f"exposed by: {self.trigger}")
        if self.evidence:
            parts.append(f"confirmed because: {self.evidence}")
        return f"- {'; '.join(parts)} (seen {self.seen}x)"


class FailurePatternStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[FailurePattern]:
        if not self.path.is_file():
            return []
        patterns: list[FailurePattern] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                patterns.append(FailurePattern.model_validate_json(line))
            except ValidationError:
                continue  # A damaged line is skipped, never trusted.
        return patterns

    def _save(self, patterns: list[FailurePattern]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        kept = sorted(patterns, key=lambda p: (p.seen, p.last_seen), reverse=True)[:MAX_PATTERNS]
        handle, temp = tempfile.mkstemp(dir=self.path.parent, prefix=".patterns-", suffix=".jsonl")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            for pattern in kept:
                stream.write(pattern.model_dump_json() + "\n")
        os.replace(temp, self.path)

    def record(
        self,
        domain: Domain,
        signature: str,
        *,
        trigger: str = "",
        evidence: str = "",
        source: str = "",
    ) -> FailurePattern:
        signature = " ".join(signature.split())[:400]
        key = hashlib.sha256(f"{domain}\x00{signature.lower()}".encode()).hexdigest()[:16]
        patterns = self.load()
        now = _now()
        for index, pattern in enumerate(patterns):
            if pattern.id == key:
                sources = (
                    pattern.sources
                    if source in pattern.sources or not source
                    else [*pattern.sources, source][-20:]
                )
                updated = pattern.model_copy(
                    update={"seen": pattern.seen + 1, "last_seen": now, "sources": sources}
                )
                patterns[index] = updated
                self._save(patterns)
                return updated
        created = FailurePattern(
            id=key,
            domain=domain,
            signature=signature,
            trigger=" ".join(trigger.split())[:400],
            evidence=" ".join(evidence.split())[:600],
            first_seen=now,
            last_seen=now,
            sources=[source] if source else [],
        )
        self._save([*patterns, created])
        return created

    def relevant(self, domain: Domain, text: str, *, limit: int = 5) -> list[FailurePattern]:
        query = _tokens(text)
        scored = []
        for pattern in self.load():
            if pattern.domain != domain:
                continue
            overlap = len(
                query & _tokens(f"{pattern.signature} {pattern.trigger} {pattern.evidence}")
            )
            if overlap >= 2:
                scored.append((overlap * (1 + math.log(pattern.seen)), pattern))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [pattern for _, pattern in scored[:limit]]

    def prompt_hints(self, domain: Domain, text: str, *, limit: int = 5) -> str:
        patterns = self.relevant(domain, text, limit=limit)
        if not patterns:
            return ""
        return (
            "\nDEFECTS POLYABRAIN CONFIRMED BEFORE IN SIMILAR WORK (hints for what to test; "
            "they are NOT requirements and must not override the text above):\n"
            + "\n".join(pattern.hint() for pattern in patterns)
            + "\n"
        )


def default_store(path: str, enabled: bool) -> FailurePatternStore | None:
    return FailurePatternStore(Path(path).expanduser()) if enabled and path.strip() else None


def describe(store: FailurePatternStore) -> dict[str, object]:
    patterns = store.load()
    return {
        "version": STORE_VERSION,
        "path": str(store.path),
        "patterns": len(patterns),
        "by_domain": {
            d: sum(1 for p in patterns if p.domain == d) for d in ("coding", "change", "claims")
        },
        "top": [
            json.loads(p.model_dump_json())
            for p in sorted(patterns, key=lambda p: p.seen, reverse=True)[:5]
        ],
    }
