"""Conservative, durable admission before authenticated provider work starts."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ProblemSession, RunAdmission, utc_now

# All API workers using this database serialize only the short admission transaction.
ADMISSION_LOCK = 73177001


class UsageLimitError(RuntimeError):
    def __init__(self, message: str, *, retry_after: int) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def resource_limits(settings: Settings) -> dict[str, Any]:
    return {
        "model_calls": settings.cognitive_max_model_calls,
        "external_calls": settings.cognitive_max_external_calls,
        "input_tokens": settings.cognitive_max_input_tokens,
        "output_tokens": settings.cognitive_max_output_tokens,
        "normalized_cost": settings.cognitive_max_normalized_cost,
        "duration_ms": settings.cognitive_max_duration_ms,
    }


class RunAdmissionPolicy:
    def __init__(self, db: Session, settings: Settings, user_id: str) -> None:
        self.db = db
        self.settings = settings
        self.user_id = user_id

    def snapshot(self, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or utc_now()
        start = day_start(now)
        count = select(func.count()).select_from(RunAdmission)
        user = count.where(RunAdmission.user_id == self.user_id)
        used = int(self.db.scalar(user.where(RunAdmission.started_at >= start)) or 0)
        active = int(self.db.scalar(user.where(RunAdmission.finished_at.is_(None))) or 0)
        return {
            "enforced": True,
            "daily_limit": self.settings.daily_user_run_limit,
            "daily_used": used,
            "daily_remaining": max(0, self.settings.daily_user_run_limit - used),
            "active_runs": active,
            "concurrent_limit": self.settings.concurrent_user_run_limit,
            "resets_at": (start + timedelta(days=1)).isoformat(),
            "per_invocation_limits": resource_limits(self.settings),
        }

    def acquire(self, session_id: UUID) -> UUID:
        """Participate in the caller's session-claim transaction; never commit separately."""
        problem_session = self.db.get(ProblemSession, session_id)
        if problem_session is None or problem_session.user_id != self.user_id:
            raise ValueError("Admission session is outside this owner namespace")
        self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADMISSION_LOCK})
        # Read the UTC day after waiting for the lock, including midnight contention.
        now = utc_now()
        start = day_start(now)
        count = select(func.count()).select_from(RunAdmission)
        today = count.where(RunAdmission.started_at >= start)
        active = count.where(RunAdmission.finished_at.is_(None))
        daily_retry = max(1, int((start + timedelta(days=1) - now).total_seconds()))
        if (
            int(self.db.scalar(today.where(RunAdmission.user_id == self.user_id)) or 0)
            >= self.settings.daily_user_run_limit
        ):
            raise UsageLimitError(
                "Your daily run allowance is used. Existing reports remain available; try again after the UTC reset.",
                retry_after=daily_retry,
            )
        if int(self.db.scalar(today) or 0) >= self.settings.daily_global_run_limit:
            raise UsageLimitError(
                "The service's daily run allowance is used. Existing reports remain available; try again after the UTC reset.",
                retry_after=daily_retry,
            )
        if (
            int(self.db.scalar(active.where(RunAdmission.user_id == self.user_id)) or 0)
            >= self.settings.concurrent_user_run_limit
        ):
            raise UsageLimitError(
                "You already have the maximum number of active runs. Wait for them to finish. Interrupted work may require operator review.",
                retry_after=30,
            )
        if int(self.db.scalar(active) or 0) >= self.settings.concurrent_global_run_limit:
            raise UsageLimitError(
                "The service is at its concurrent run limit. Try again shortly.", retry_after=30
            )
        record = RunAdmission(
            session_id=session_id,
            user_id=self.user_id,
            started_at=now,
            resource_limits=resource_limits(self.settings),
        )
        self.db.add(record)
        self.db.flush()
        return record.id

    def finish(self, admission_id: UUID, outcome: str) -> None:
        record = self.db.get(RunAdmission, admission_id)
        if record is None or record.user_id != self.user_id:
            raise ValueError("Admission is outside this owner namespace")
        if record.finished_at is not None:
            return
        record.finished_at = utc_now()
        record.outcome = outcome
        self.db.commit()
