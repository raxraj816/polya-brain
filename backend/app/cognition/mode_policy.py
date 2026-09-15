"""Existing product-mode guidance derived from validated approach trace events."""

from __future__ import annotations

from pydantic import JsonValue

from app.graph.state import PolyaState
from app.models.contracts import ProductMode

MODE_CHECKLISTS = {
    ProductMode.INVESTIGATE: [
        "Distinguish the observed symptom from a proposed cause.",
        "Consider competing explanations and identify evidence that discriminates between them.",
        "Ground the conclusion in observed checks; carry unresolved causes as uncertainty.",
    ],
    ProductMode.COMPARE: [
        "Identify at least two explicit alternatives and common decision criteria.",
        "Compare alternatives against the same criteria, constraints, and evidence standard.",
        "Expose tradeoffs and missing comparative evidence; do not declare a winner without support.",
    ],
    ProductMode.REVIEW: [
        "Identify the provided claim, artifact, or design and its acceptance criteria.",
        "Check material claims, counterexamples, failure cases, and consequential omissions.",
        "Separate confirmed defects from unresolved risks and specify checks needed to close them.",
    ],
    ProductMode.EXPLORE: [
        "Generate plausible alternatives without presenting them as established conclusions.",
        "Name the evidence and next checks needed to choose among the alternatives.",
    ],
}


def mode_context(state: PolyaState) -> dict[str, JsonValue]:
    """Keep mode as auditable prompt context, never an invented ranking signal."""
    for event in reversed(state["events"]):
        if (
            event.engine_name == "problem_representation"
            and event.event_type == "approach_selected"
        ):
            raw_mode = event.metadata.get("selected_mode")
            if not isinstance(raw_mode, str):
                continue
            try:
                mode = ProductMode(raw_mode)
            except ValueError, TypeError:
                continue
            return {
                "selected_mode": mode.value,
                "mode_verification_checklist": list(MODE_CHECKLISTS[mode]),
            }
    return {}
