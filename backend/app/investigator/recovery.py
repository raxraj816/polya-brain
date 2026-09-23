"""Single-use local recovery authority, separate from editable report exports.

The private SQLite store is trusted local application state, not an import
format. Exported tokens can refer only to records already created on this host.
Process locks release on death; durable in-flight markers do not.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import stat
import sys
from importlib.metadata import version
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from pydantic import JsonValue, TypeAdapter

from app.cognition.kernel import CognitiveRunResult
from app.cognition.task_model import BUDGET_EVENT, USAGE_EVENT
from app.config import Settings
from app.graph.state import PolyaState, StateEvent, create_initial_state
from app.models.contracts import ReasoningMode
from app.tracing.sanitization import sanitize_json_value

STATE = TypeAdapter(PolyaState)


class RecoveryError(ValueError):
    """A safe, user-facing recovery refusal without secret exception details."""


def runtime_fingerprint(settings: Settings, directory: Path | None = None) -> str:
    """Bind all configuration without saving credentials or settings to disk."""
    config = settings.model_dump(mode="json")
    for key in ("openrouter_api_key", "search_api_key", "secret_key", "database_url", "redis_url"):
        config.pop(key, None)
    config["model_available"] = bool(settings.openrouter_api_key.get_secret_value())
    config["search_available"] = bool(settings.search_api_key.get_secret_value())
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode())
    if directory is not None:
        digest.update(str(directory.resolve()).encode())
    digest.update(sys.version.encode())
    for package in ("pydantic", "pydantic-settings", "langgraph", "langchain-core", "httpx"):
        digest.update(f"{package}={version(package)}".encode())
    root = Path(__file__).resolve().parents[1]
    for path in sorted(root.rglob("*.py")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _private_file(path: Path) -> int:
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        os.close(fd)
        raise RecoveryError("Recovery files must be regular, owner-private files.")
    return fd


class RecoveryStore:
    """Host-local checkpoints with serialized claims and exclusive process leases."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(
            os.environ.get("POLYABRAIN_RECOVERY_HOME", str(Path.home() / ".local/state/polyabrain"))
        )
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = self.root.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise RecoveryError("The recovery directory must be owner-private (mode 700).")
        db = self.root / "recovery.sqlite"
        os.close(_private_file(db))
        self.connection = sqlite3.connect(db, timeout=5)
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints ("
            "token TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, state TEXT, "
            "status TEXT NOT NULL, in_flight INTEGER NOT NULL DEFAULT 0, "
            "redacted INTEGER NOT NULL DEFAULT 0, consumed INTEGER NOT NULL DEFAULT 0)"
        )
        self.connection.commit()
        self._locks: dict[str, int] = {}

    def close(self) -> None:
        self.connection.close()
        for fd in self._locks.values():
            os.close(fd)
        self._locks.clear()

    def _lock(self, token: str) -> None:
        if str(UUID(token)) != token:
            raise RecoveryError("Invalid recovery token.")
        if token in self._locks:
            return
        fd = _private_file(self.root / f"{token}.lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise RecoveryError("This investigation is still running or being resumed.") from None
        self._locks[token] = fd

    def create(self, fingerprint: str) -> str:
        token = str(uuid4())
        self._lock(token)
        with self.connection:
            self.connection.execute(
                "INSERT INTO checkpoints (token, fingerprint, status) VALUES (?, ?, 'running')",
                (token, fingerprint),
            )
        return token

    def save(self, token: str, state: PolyaState, in_flight: bool, status: str = "running") -> None:
        raw = cast(JsonValue, STATE.dump_python(state, mode="json"))
        safe = sanitize_json_value(raw)
        with self.connection:
            changed = self.connection.execute(
                "UPDATE checkpoints SET state=?, status=?, in_flight=?, redacted=? "
                "WHERE token=? AND consumed=0",
                (json.dumps(safe), status, int(in_flight), int(safe != raw), token),
            ).rowcount
            if changed != 1:
                raise RecoveryError("Recovery checkpoint was already consumed or is unavailable.")

    def finish(self, token: str, result: CognitiveRunResult) -> None:
        self.save(token, result.state, False, result.status.value)

    def load(self, token: str, fingerprint: str, answer: str | None) -> PolyaState:
        self._lock(token)
        row = self.connection.execute(
            "SELECT fingerprint, state, status, in_flight, redacted, consumed "
            "FROM checkpoints WHERE token=?",
            (token,),
        ).fetchone()
        if row is None:
            raise RecoveryError(
                "No local checkpoint exists. Reports from other hosts cannot be resumed."
            )
        saved_fingerprint, raw, status, in_flight, redacted, consumed = row
        if consumed:
            raise RecoveryError(
                "This checkpoint has already been resumed. Use its continuation directory."
            )
        if in_flight:
            raise RecoveryError(
                "A capability was interrupted in flight; its outcome and cost are unknown. Automatic replay is refused."
            )
        if redacted or raw is None:
            raise RecoveryError(
                "No executable checkpoint is available; state was absent or changed by secret redaction."
            )
        if saved_fingerprint != fingerprint:
            raise RecoveryError(
                "Runtime code, configuration, or report directory changed. Restore the original directory and options (including --offline, artifact roots and budgets) before resuming."
            )
        if status not in {"running", "max_cycles", "needs_input"}:
            raise RecoveryError(
                "This run is terminal. Only a cycle pause, missing-input pause, or safe interrupted boundary can resume."
            )
        if (status == "needs_input") != (answer is not None):
            raise RecoveryError(
                "A missing-input run requires --answer with the full revised problem. Other runs cannot change their problem during recovery."
            )
        state = STATE.validate_json(raw)
        if answer is not None:
            revised = create_initial_state(
                answer, session_id=state["session_id"], max_iterations=state["max_iterations"]
            )
            # Prior semantic events cannot satisfy gates for the revised task.
            # Immutable parent exports retain the full earlier audit trace.
            revised["events"] = [
                event
                for event in state["events"]
                if event.event_type in {BUDGET_EVENT, USAGE_EVENT}
            ]
            state = revised
        state["events"].append(
            StateEvent(
                engine_name="investigator_recovery",
                event_type="investigation_resumed",
                reasoning_mode=ReasoningMode.REFRAME if answer else ReasoningMode.EXECUTE,
                summary="Revalidated a revised problem with prior resource charges."
                if answer
                else "Continued the saved investigation without replaying completed capabilities.",
                metadata={"parent_recovery_id": token, "revised_problem": answer is not None},
            )
        )
        return state

    def initialize(self, token: str, state: PolyaState, parent: str | None) -> None:
        """Atomically replace the parent's recovery right with a saved child."""
        raw = cast(JsonValue, STATE.dump_python(state, mode="json"))
        safe = sanitize_json_value(raw)
        with self.connection:
            if parent is not None:
                if parent not in self._locks:
                    raise RecoveryError("Parent checkpoint must be locked before continuation.")
                changed = self.connection.execute(
                    "UPDATE checkpoints SET consumed=1 WHERE token=? AND consumed=0", (parent,)
                ).rowcount
                if changed != 1:
                    raise RecoveryError("This checkpoint has already been resumed.")
            changed = self.connection.execute(
                "UPDATE checkpoints SET state=?, redacted=? WHERE token=? AND state IS NULL",
                (json.dumps(safe), int(safe != raw), token),
            ).rowcount
            if changed != 1:
                raise RecoveryError("Continuation checkpoint could not be initialized.")
