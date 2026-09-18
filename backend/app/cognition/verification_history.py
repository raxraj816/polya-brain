"""Historical failure diagnostics for runs interrupted during recovery.

Audit history is presentation context only, never current verification evidence.
"""

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.graph.state import StateEvent
from app.models.contracts import ReasoningMode, VerificationReport

VERIFICATION_INVALIDATED_EVENT = "verification_invalidated"
VERIFICATION_HISTORY_VERSION = "verification_history@0.1.0"
HISTORICAL_CHECK_PREFIX = "Earlier attempt, before recovery: "
HISTORICAL_NEXT_ACTION = (
    "Provide evidence addressing the earlier failed checks, then rerun verification "
    "against the current state."
)


def verification_invalidated_event(report: VerificationReport, *, action_id: str) -> StateEvent:
    """Preserve the old report before a material change clears current verification."""
    return StateEvent(
        engine_name="cognitive_kernel",
        event_type=VERIFICATION_INVALIDATED_EVENT,
        reasoning_mode=ReasoningMode.VERIFY,
        summary="A material state change invalidated the previous verification; retained its audit history.",
        metadata={
            "version": VERIFICATION_HISTORY_VERSION,
            "action_id": action_id,
            "report": report.model_dump(mode="json"),
            "scope": "historical diagnostics only; not current verification",
        },
    )


def historical_failure(metadata: Mapping[str, Any] | None) -> VerificationReport | None:
    """Parse and label a previous failure without ever reactivating its verdict."""
    if not metadata or metadata.get("version") != VERIFICATION_HISTORY_VERSION:
        return None
    try:
        report = VerificationReport.model_validate(metadata.get("report"))
    except ValidationError:
        return None
    if report.passed:
        return None
    return VerificationReport(
        passed=False,
        checks_run=[HISTORICAL_CHECK_PREFIX + item for item in report.checks_run],
        failed_checks=[HISTORICAL_CHECK_PREFIX + item for item in report.failed_checks],
        contradictions=[HISTORICAL_CHECK_PREFIX + item for item in report.contradictions],
        recommended_route=HISTORICAL_NEXT_ACTION,
    )
