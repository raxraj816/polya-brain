"""Bound successful authenticated storage writes in the caller's transaction."""

from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import HumanFeedback, ProblemSession, utc_now
from app.sessions.admission import UsageLimitError, day_start

SESSION_WRITE_LOCK = 73177002
FEEDBACK_WRITE_LOCK = 73177003
FEEDBACK_PER_SESSION = 100


def database_now(db: Session) -> datetime:
    now = db.scalar(select(func.clock_timestamp()))
    if not isinstance(now, datetime):
        raise RuntimeError("Database clock unavailable")
    return now.astimezone(UTC)


class WriteAdmissionPolicy:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def acquire(
        self, kind: Literal["session", "feedback"], *, session_id: UUID | None = None
    ) -> datetime:
        """Hold the lock until the caller commits the new row or rolls back."""
        if not self.settings.auth_required:
            return utc_now()
        owner = self.db.info.get("owner_id")
        if not isinstance(owner, str) or not owner:
            raise ValueError("Write admission requires an authenticated owner")
        if kind == "feedback":
            target = self.db.get(ProblemSession, session_id) if session_id else None
            if target is None or target.user_id != owner:
                raise ValueError("Feedback target is outside this owner namespace")
        lock = SESSION_WRITE_LOCK if kind == "session" else FEEDBACK_WRITE_LOCK
        self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
        now = database_now(self.db)
        start = day_start(now)
        end = start + timedelta(days=1)
        if kind == "session":
            count = (
                select(func.count())
                .select_from(ProblemSession)
                .where(
                    ProblemSession.created_at >= start,
                    ProblemSession.created_at < end,
                    ProblemSession.user_id.is_not(None),
                )
            )
            user_limit = self.settings.daily_user_session_limit
            global_limit = self.settings.daily_global_session_limit
        else:
            count = (
                select(func.count())
                .select_from(HumanFeedback)
                .join(ProblemSession)
                .where(
                    HumanFeedback.created_at >= start,
                    HumanFeedback.created_at < end,
                    ProblemSession.user_id.is_not(None),
                )
            )
            user_limit = self.settings.daily_user_feedback_limit
            global_limit = self.settings.daily_global_feedback_limit
            existing = self.db.scalar(
                select(func.count())
                .select_from(HumanFeedback)
                .where(HumanFeedback.session_id == session_id)
            )
            if int(existing or 0) >= FEEDBACK_PER_SESSION:
                # This is permanent for this session, so do not imply a timed reset.
                raise FeedbackCapacityError(
                    "This investigation has reached its feedback limit (100 records). "
                    "Existing feedback and reports remain available. Keep further corrections locally."
                )
        retry = max(1, ceil((end - now).total_seconds()))
        if int(self.db.scalar(count.where(ProblemSession.user_id == owner)) or 0) >= user_limit:
            raise UsageLimitError(
                f"Your daily {kind} creation allowance is used. Existing records remain available. "
                "Keep your input and try again after the UTC reset.",
                retry_after=retry,
            )
        if int(self.db.scalar(count) or 0) >= global_limit:
            raise UsageLimitError(
                f"The service's daily {kind} creation allowance is used. Existing records remain available. "
                "Keep your input and try again after the UTC reset.",
                retry_after=retry,
            )
        return now


class FeedbackCapacityError(RuntimeError):
    """Permanent per-session cap; retrying at midnight cannot open space."""
