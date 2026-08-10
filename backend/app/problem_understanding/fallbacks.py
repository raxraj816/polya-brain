"""Narrow deterministic fallbacks for obvious Chapter 13 inputs."""

from __future__ import annotations

import re

from app.graph.state import PolyaState
from app.llm import LLMTokenUsage
from app.models.contracts import ProductMode
from app.problem_understanding.contracts import (
    ProblemUnderstandingOutput,
    ProblemUnderstandingRunResult,
)
from app.problem_understanding.examples import PROBLEM_UNDERSTANDING_EXAMPLES
from app.problem_understanding.prompt import PROBLEM_UNDERSTANDING_PROMPT_VERSION

DETERMINISTIC_PROVIDER = "deterministic"
DETERMINISTIC_MODEL = "problem_understanding_fallback@1.0.0"

_SIMPLE_ARITHMETIC = re.compile(
    r"^(?:what\s+is\s+)?(?P<left>-?\d+(?:\.\d+)?)\s*"
    r"(?P<operator>[+\-*/])\s*(?P<right>-?\d+(?:\.\d+)?)\s*\??$",
    re.IGNORECASE,
)
_AMBIGUOUS_REQUESTS = {
    "fix it",
    "help me",
    "investigate it",
    "make it better",
    "make it faster",
    "solve this",
    "what should i do",
}
_CLARIFICATION_MARKER = "USER CLARIFICATION (treat as additional problem information):"
_MEASURABLE_OR_CONSTRAINED_TERMS = {
    "baseline",
    "budget",
    "cost",
    "error",
    "errors",
    "latency",
    "milliseconds",
    "ms",
    "p95",
    "percent",
    "risk",
    "seconds",
    "success",
    "time",
}


def _example_fallback(
    state: PolyaState,
    *,
    mode_hint: ProductMode | None,
    domain_hint: str | None,
) -> ProblemUnderstandingOutput | None:
    normalized_input = " ".join(state["raw_input"].split()).casefold()
    for example in PROBLEM_UNDERSTANDING_EXAMPLES:
        if " ".join(example.raw_input.split()).casefold() != normalized_input:
            continue
        if mode_hint is not None and example.output.selected_mode is not mode_hint:
            return None
        if domain_hint is not None and example.output.domain not in {None, domain_hint.strip()}:
            return None
        return example.output
    return None


def _arithmetic_fallback(
    state: PolyaState,
    *,
    mode_hint: ProductMode | None,
    domain_hint: str | None,
) -> ProblemUnderstandingOutput | None:
    match = _SIMPLE_ARITHMETIC.fullmatch(state["raw_input"].strip())
    if match is None:
        return None
    expression = f"{match.group('left')} {match.group('operator')} {match.group('right')}"
    return ProblemUnderstandingOutput(
        literal_framing=f"Evaluate the arithmetic expression {expression}.",
        deeper_framing="Compute the result and independently check the arithmetic operation.",
        goal=f"Calculate and verify {expression}.",
        problem_type="simple_arithmetic",
        domain=domain_hint.strip() if domain_hint and domain_hint.strip() else "mathematics",
        selected_mode=mode_hint or ProductMode.EXPLORE,
        mode_confidence=1.0,
        mode_selection_reason=(
            "The input is a fully specified deterministic arithmetic problem."
            if mode_hint is None
            else "The user-supplied mode override is preserved for a deterministic arithmetic problem."
        ),
        given=[f"Expression: {expression}."],
        unknown=["The numeric result."],
        constraints=["Use the stated arithmetic operator and operands."],
        success_criteria=["The result is computed and checked independently."],
        required_data_sources=["deterministic calculator"],
    )


def _ambiguous_fallback(
    state: PolyaState,
    *,
    mode_hint: ProductMode | None,
    domain_hint: str | None,
) -> ProblemUnderstandingOutput | None:
    normalized = " ".join(state["raw_input"].lower().rstrip(".!?").split())
    if normalized not in _AMBIGUOUS_REQUESTS:
        return None
    return ProblemUnderstandingOutput(
        literal_framing="Act on an unspecified problem or target.",
        deeper_framing="Identify the affected system, observed symptom, desired outcome, and evidence before choosing an action.",
        wrong_problem_warning="Acting without a target or success measure could solve the wrong problem.",
        goal="Clarify the target problem and measurable success condition.",
        problem_type="underspecified_request",
        domain=domain_hint.strip() if domain_hint and domain_hint.strip() else None,
        selected_mode=mode_hint or ProductMode.EXPLORE,
        mode_confidence=0.35 if mode_hint is None else 0.75,
        mode_selection_reason=(
            "The request does not identify the target, symptom, evidence, or desired outcome."
            if mode_hint is None
            else "The user mode override is known, but the target and desired outcome are missing."
        ),
        needs_clarification=True,
        clarifying_questions=[
            "Which system, artifact, or decision should PolyaBrain investigate?",
            "What observed result and measurable success condition should guide the investigation?",
        ],
        given=["The user requested help without specifying the target problem."],
        unknown=["Target system or artifact.", "Observed symptom.", "Desired outcome."],
        constraints=["Do not select a solution before the target and success condition are known."],
        success_criteria=["The target, symptom, and measurable outcome are explicit."],
    )


def _clarified_ambiguous_fallback(
    state: PolyaState,
    *,
    mode_hint: ProductMode | None,
    domain_hint: str | None,
) -> ProblemUnderstandingOutput | None:
    raw_input = state["raw_input"]
    if _CLARIFICATION_MARKER not in raw_input:
        return None
    original, answer = raw_input.split(_CLARIFICATION_MARKER, maxsplit=1)
    normalized_original = " ".join(original.lower().rstrip(".!? \n").split())
    normalized_answer = " ".join(answer.split())
    if normalized_original not in _AMBIGUOUS_REQUESTS:
        return None

    answer_terms = {token.strip(".,:;!?()[]").lower() for token in normalized_answer.split()}
    sufficient = len(normalized_answer) >= 24 and bool(
        answer_terms.intersection(_MEASURABLE_OR_CONSTRAINED_TERMS)
    )
    if not sufficient:
        return ProblemUnderstandingOutput(
            literal_framing="Use the clarification to identify the target and success condition.",
            deeper_framing=(
                "The supplied clarification still lacks a measurable outcome or decision constraint."
            ),
            wrong_problem_warning=(
                "Continuing without an observable success condition would still risk solving "
                "the wrong problem."
            ),
            goal="Obtain a target plus an observable or constrained success condition.",
            problem_type="underspecified_request",
            domain=domain_hint.strip() if domain_hint and domain_hint.strip() else None,
            selected_mode=mode_hint or ProductMode.EXPLORE,
            mode_confidence=0.45 if mode_hint is None else 0.75,
            mode_selection_reason="The clarification adds context but remains insufficient.",
            needs_clarification=True,
            clarifying_questions=[
                "What target should change, and which measurable outcome or constraint defines success?"
            ],
            given=[f"User clarification: {normalized_answer}"],
            unknown=["Measurable outcome or decision constraint."],
            constraints=["Do not proceed until success is observable or explicitly constrained."],
            success_criteria=["The target and success condition are both explicit."],
        )

    return ProblemUnderstandingOutput(
        literal_framing=f"Act on the clarified request: {normalized_answer}",
        deeper_framing=(
            "Determine a verified action that improves the stated target under the supplied "
            "success condition or constraint."
        ),
        goal=normalized_answer,
        problem_type="clarified_request",
        domain=domain_hint.strip() if domain_hint and domain_hint.strip() else None,
        selected_mode=mode_hint or ProductMode.EXPLORE,
        mode_confidence=0.9,
        mode_selection_reason=(
            "The user supplied both a target and an observable metric or decision constraint."
        ),
        given=[f"Original request: {original.strip()}", f"User clarification: {normalized_answer}"],
        unknown=[],
        constraints=["Preserve the user-supplied success condition or constraint."],
        success_criteria=[f"A proposed outcome is checked against: {normalized_answer}"],
    )


def deterministic_problem_understanding(
    state: PolyaState,
    *,
    mode_hint: ProductMode | None = None,
    domain_hint: str | None = None,
) -> ProblemUnderstandingRunResult | None:
    """Return a validated no-LLM result only for narrowly recognized inputs."""
    output = (
        _example_fallback(state, mode_hint=mode_hint, domain_hint=domain_hint)
        or _arithmetic_fallback(state, mode_hint=mode_hint, domain_hint=domain_hint)
        or _clarified_ambiguous_fallback(
            state,
            mode_hint=mode_hint,
            domain_hint=domain_hint,
        )
        or _ambiguous_fallback(state, mode_hint=mode_hint, domain_hint=domain_hint)
    )
    if output is None:
        return None
    return ProblemUnderstandingRunResult(
        output=output,
        structured_problem=output.to_structured_problem(),
        prompt_version=PROBLEM_UNDERSTANDING_PROMPT_VERSION,
        provider=DETERMINISTIC_PROVIDER,
        model=DETERMINISTIC_MODEL,
        llm_call_count=0,
        llm_repair_attempts=0,
        usage=LLMTokenUsage(),
    )
