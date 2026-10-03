"""Presentation of research stops recorded in existing controller decisions."""

from pydantic import ValidationError

from app.cognition.contracts import CognitiveActionDecision, CognitiveActionType

RESEARCH_BUDGET_STOP_REASON = "public research cannot fit the remaining acquisition budget"
RESEARCH_BUDGET_NEXT_ACTION = (
    "Public research stopped because another acquisition could not fit the remaining "
    "run budget. Review the retained evidence and unresolved questions, then decide "
    "whether to narrow the investigation or explicitly authorize a separately budgeted "
    "investigation. No automatic retry or budget increase was performed."
)
RESEARCH_UNAVAILABLE_STOP_REASON = "no safe research route remains for missing public evidence"
RESEARCH_UNAVAILABLE_NEXT_ACTION = (
    "Public evidence remains unresolved because no safe research route is currently available. "
    "Review the trace for unavailable capabilities, failed attempts or privacy restrictions. "
    "Resolve the research access problem or narrow the investigation before starting a new run. "
    "No automatic retry was performed; no verified conclusion is available."
)


def research_stop_next_action(metadata: object) -> str | None:
    """Read only the latest decision of an already unsuccessful terminal run."""
    try:
        decision = CognitiveActionDecision.model_validate(metadata)
    except ValidationError:
        return None
    if (
        decision.selected.action_type is CognitiveActionType.STOP
        and decision.selected.capability == "cognitive_controller"
    ):
        return {
            f"Stop safely because {RESEARCH_BUDGET_STOP_REASON}.": RESEARCH_BUDGET_NEXT_ACTION,
            f"Stop safely because {RESEARCH_UNAVAILABLE_STOP_REASON}.": RESEARCH_UNAVAILABLE_NEXT_ACTION,
        }.get(decision.selected.purpose)
    return None
