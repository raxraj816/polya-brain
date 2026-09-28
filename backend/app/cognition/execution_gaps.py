"""Narrow routing of internal execution work; external observations remain evidence gaps."""

import re

from app.graph.state import PolyaState

SANDBOX_GAP_TYPE = "pending_runtime_execution"


def is_sandbox_work(unknown: str, sources: list[str], task_context: str = "") -> bool:
    """Recognize explicitly local runtime tool work, never arbitrary missing results."""
    text = " ".join([unknown, *sources]).casefold()
    if re.search(
        r"\b(?:private|production|staging|remote|customer|historical|previous|past|yesterday|"
        r"credentials?|permissions?|approval|logs?|deployment|installed|release|repository|"
        r"expected|desired|requirements?|specifications?|behavior|leetcode|judge)\b",
        unknown.casefold(),
    ):
        return False
    tool = re.search(
        r"\b(?:python_sandbox|python sandbox|sandbox|isolated python)\b",
        text + " " + task_context.casefold(),
    )
    operation = re.search(
        r"\b(?:invocation|invoke|execution|execute|tests?|testing|results?|outcomes?|output|pass)\b",
        unknown.casefold(),
    )
    return bool(tool and operation)


def pending_sandbox_gaps(state: PolyaState) -> list[str]:
    return [
        gap.description
        for gap in state["gaps"]
        if not gap.filled
        and gap.gap_type == SANDBOX_GAP_TYPE
        and gap.suggested_source == "python_sandbox"
    ]
