"""Explain, from the trace, why a run stopped without a verified conclusion.

A stopped run must never read as "nothing happened". This turns the recorded
trace into the work that was completed, the step that failed and why, and a
specific next action. It reads trace events only and never changes run state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

STEP_NAMES = {
    "problem_representation": "Problem framing",
    "deterministic_problem_representation": "Problem framing",
    "constraint_discovery": "Constraint discovery",
    "task_gap_detector": "Knowledge-gap check",
    "gap_detector": "Knowledge-gap check",
    "deliberator": "Solution design (hypotheses and analysis)",
    "hypothesis_generator": "Hypothesis generation",
    "planner": "Planning",
    "analysis_executor": "Analysis",
    "conclusion_checker": "Final verification",
    "verifier": "Final verification",
    "web_search": "Web research",
    "public_page_reader": "Reading public sources",
    "evidence_evaluator": "Evidence evaluation",
    "python_sandbox": "Code execution",
}


@dataclass
class StopExplanation:
    progress: list[str] = field(default_factory=list)
    failure: str | None = None
    next_action: str | None = None

    @property
    def headline(self) -> str:
        return (
            f"PolyaBrain stopped without a verified conclusion: {self.failure}"
            if self.failure
            else "PolyaBrain stopped without a verified conclusion."
        )


def _step(capability: str) -> str:
    return STEP_NAMES.get(capability, capability.replace("_", " ").capitalize())


def _failure_text(step: str, metadata: Mapping[str, Any]) -> tuple[str, str]:
    kinds = {
        str(metadata.get("failure_kind") or ""),
        str(metadata.get("terminal_failure_kind") or ""),
        *(
            str(item.get("failure_kind") or "")
            for item in metadata.get("route_attempts") or []
            if isinstance(item, Mapping)
        ),
    }
    calls = metadata.get("model_calls")
    tried = f" ({calls} model attempts)" if isinstance(calls, int) and calls > 1 else ""
    if "output_truncated" in kinds:
        return (
            f"{step} failed: the model's answer was cut off at its output limit on every "
            f"attempt{tried}, so no complete answer was produced.",
            "Ask for one part at a time (for example the architecture first, then the failure "
            "timeline and edge cases) so each answer fits, then continue with the next part.",
        )
    if "permission" in kinds or "authentication" in kinds:
        return (
            f"{step} failed: the model provider refused the request (check the API key and "
            "the account's credits).",
            "Fix the model provider account (API key and credits), then run the problem again.",
        )
    if "timeout" in kinds:
        return (
            f"{step} failed: the model did not answer within its time limit{tried}.",
            "Run again; if it repeats, split the problem into smaller questions.",
        )
    if kinds & {"unavailable", "provider_error"}:
        return (
            f"{step} failed: the model provider was unavailable{tried}.",
            "Run the problem again shortly; if it repeats, check the provider status.",
        )
    if "rate_limit" in kinds:
        return (
            f"{step} failed: the model provider rate-limited the request.",
            "Wait a little and run the problem again.",
        )
    if kinds & {"schema_validation", "malformed_response", "semantic_routes_exhausted"}:
        return (
            f"{step} failed: the model's responses did not match the required structure{tried}.",
            "Run again with a specific model pinned in OPENROUTER_MODEL (openrouter/auto picks a "
            "different model each time), or split the problem into smaller questions.",
        )
    label = next((kind for kind in sorted(kinds) if kind), "unknown")
    return (
        f"{step} failed ({label}).",
        "Inspect the audit trace for the failed step, then run again or narrow the problem.",
    )


def explain_stop(events: Iterable[tuple[str, Mapping[str, Any], str]]) -> StopExplanation:
    """Build an explanation from (event_type, metadata, summary) triples in trace order."""
    explanation = StopExplanation()
    ordered = list(events)
    # Discovered-constraint events follow the observation that reports them.
    constraints = sum(1 for event_type, _, _ in ordered if event_type == "constraint_discovered")
    last_failure: tuple[str, Mapping[str, Any]] | None = None
    seen_steps: set[str] = set()
    for event_type, metadata, summary in ordered:
        if event_type != "capability_observation":
            continue
        capability = str(metadata.get("capability") or "")
        status = str(metadata.get("status") or "")
        if status == "succeeded":
            step = _step(capability)
            line = f"{step}: {summary.rstrip('.')}."
            if capability == "constraint_discovery" and constraints:
                line = f"{step}: identified {constraints} explicit and implicit constraints."
            if line not in seen_steps:
                seen_steps.add(line)
                explanation.progress.append(line)
            last_failure = None
        elif status in {"failed", "inconclusive"} or (
            status == "blocked" and metadata.get("failure_kind") != "human_input_required"
        ):
            last_failure = (capability, metadata)
    if last_failure is not None:
        explanation.failure, explanation.next_action = _failure_text(
            _step(last_failure[0]), last_failure[1]
        )
    return explanation
