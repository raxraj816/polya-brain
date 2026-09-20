"""Bounded public-knowledge recovery from failed independent verification."""

from app.cognition.model_contracts import ConclusionCheckOutput
from app.graph.state import PolyaState, StateEvent
from app.models.contracts import KnowledgeGap, PriorityLevel, ReasoningMode

RESEARCH_EVENT = "verification_research_requested"
ANALYSIS_EVENT = "verification_research_analyzed"
VERSION = "verification_research@0.1.0"


def research_requested(state: PolyaState) -> bool:
    return any(event.event_type == RESEARCH_EVENT for event in state["events"])


def needs_recovery_analysis(state: PolyaState) -> bool:
    return research_requested(state) and not any(
        event.event_type == ANALYSIS_EVENT for event in state["events"]
    )


def research_update(
    state: PolyaState, output: ConclusionCheckOutput, *, action_id: str
) -> tuple[list[KnowledgeGap], list[StateEvent]]:
    """Translate failed-check-bound requests once; ordinary acquisition gates still apply."""
    if output.report.passed or not output.public_research_needs or research_requested(state):
        return [], []
    gaps = [
        KnowledgeGap(
            # Distinct from a previously filled discovery gap: its prior coverage
            # was insufficient for this independently identified failed check.
            description=f"Verification research {index}: {need.question}",
            gap_type="current_external_fact",
            priority=PriorityLevel.HIGH,
            why_needed=output.report.failed_checks[need.failed_check_index],
            suggested_source="official web source",
        )
        for index, need in enumerate(output.public_research_needs, start=1)
    ]
    return gaps, [
        StateEvent(
            engine_name="conclusion_checker",
            event_type=RESEARCH_EVENT,
            reasoning_mode=ReasoningMode.VERIFY,
            summary="Failed verification requested one bounded public-research round.",
            metadata={
                "version": VERSION,
                "action_id": action_id,
                "report": output.report.model_dump(mode="json"),
                "requests": [need.model_dump(mode="json") for need in output.public_research_needs],
                "gaps": [gap.model_dump(mode="json") for gap in gaps],
                "scope": "Research requests only; no new evidence or successful checks.",
            },
        )
    ]
