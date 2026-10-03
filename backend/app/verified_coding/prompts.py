"""Versioned prompts for lean solving, independent oracles and adjudication."""

from __future__ import annotations

import json

from app.verified_coding.harness import DifferentialResult

PROMPT_VERSION = "verified_coding@0.1.0"

# Identical to the matched lean baseline so paired comparisons share stage one.
SOLVE_PROMPT = (
    "Solve the problem using a networkless Python standard-library sandbox. "
    "Return a JSON object with code (complete implementation, max 20000 chars), "
    "tests (1..20 Python assertion strings, each max 2000 chars), and explanation "
    "(correctness and complexity). Your code/tests will run; if execution fails, "
    "use the feedback to repair it. Preserve earlier tests when repairing code. "
    "Do not claim external judge acceptance.\n\nPROBLEM:\n"
)

ORACLE_PROMPT = """You are PolyaBrain's independent verification oracle (prompt {version}).
Another solver is implementing the PROBLEM below. You will never see its code.
Your job is to make it possible to TEST that solver mechanically. Return exactly
one JSON object with these keys:

- "entrypoint": {{"name": <function or method name>, "class_name": <class name or null>}}
  exactly as the problem requires (class_name only when the problem asks for a
  class with a method).
- "reference_code": Python standard-library code defining the same entrypoint with
  the same parameters. Write the most LITERAL, obviously correct implementation
  of the specification: brute force, exhaustive search or direct step-by-step
  simulation. IGNORE all efficiency requirements; it only needs to be correct on
  small inputs. Implement every stated rule, edge case and tie-break visibly and
  separately. Do not rely on the "well-known" version of a similar problem: the
  problem text overrides convention wherever they differ.
- "generator_code": defines generate(rng, size) returning a TUPLE of positional
  arguments for one call. rng is a random.Random instance; size is an int from 0
  to 8 controlling input scale (size 0 should give the smallest valid inputs).
  Every generated input must satisfy all stated preconditions. Deliberately
  produce the inputs most likely to expose mistakes: empty and single-element
  inputs, duplicates, ties, equal or touching values, boundaries, negative values
  and any special characters or cases the problem mentions. Keep inputs small
  enough for the brute-force reference to finish in well under a second.
- "examples": every example the problem states, as objects
  {{"call": <Python expression calling the entrypoint>, "expected": <Python literal>}},
  copied exactly from the problem text. Use [] when none are stated. Do not invent
  examples.
- "scale_code": defines scale_inputs(rng) returning a list of at most 3 argument
  tuples at or near the largest sizes the problem allows, to time the solver.
  Use "" if the problem states no size limits.
- "same_code": "" unless the problem explicitly allows several correct outputs
  (for example any valid ordering). Only then define same(args, got, want) that
  returns True when got is a correct output for args (want is the reference
  output).
- "assumptions": short strings naming any interpretation you had to choose where
  the problem text is genuinely unclear. Use [] when it is clear.

Only the Python standard library is available; no files or network. Each code
string must be at most 6000 characters. Do not include Markdown fences.

PROBLEM:
{problem}
"""

ADJUDICATE_PROMPT = """You are PolyaBrain's adjudicator (prompt {version}).
Two independently written implementations of the PROBLEM below disagree on one
concrete input. The CANDIDATE is the delivered solution. The REFERENCE is a
deliberately simple brute-force oracle written from the same problem text; it can
also be wrong. Decide, from the PROBLEM TEXT ALONE, what the correct output for
this exact input is. Apply each relevant rule of the problem to this input
step by step before answering, but do not output that reasoning.

Return exactly one JSON object:
- "verdict": one of "candidate_wrong", "reference_wrong", "both_wrong",
  "both_acceptable" (the problem allows both outputs), "ambiguous" (the problem
  text genuinely does not determine the answer).
- "expected": Python literal of the correct output for this input (use a literal
  such as -1000000000, not an expression). "" for both_acceptable or ambiguous.
- "governing_requirement": a phrase copied VERBATIM from the problem text (5 to
  40 words, contiguous, no ellipsis) that decides this case.
- "explanation": at most three sentences.
- "repaired_candidate_code": when the candidate is wrong, its COMPLETE corrected
  code. Change it minimally, keep the same entrypoint and keep every efficiency
  requirement of the problem. Otherwise "".
- "repaired_reference_code": when the reference is wrong, its COMPLETE corrected
  brute-force code. Otherwise "".
- "relaxation": "" unless verdict is both_acceptable, then "numeric_type" (int and
  float with equal value are both acceptable), "unordered" (element order of a
  returned list does not matter) or "mutation_allowed" (the problem does not
  forbid modifying the input arguments).
- "question": for ambiguous only, the precise question the user must answer.

PROBLEM:
{problem}

DISAGREEMENT ({source}):
input arguments (Python repr): {args}
candidate output: {candidate_output}
reference output: {reference_output}

CANDIDATE CODE:
{candidate_code}

REFERENCE CODE:
{reference_code}
"""

PERFORMANCE_PROMPT = """You are PolyaBrain's repair step (prompt {version}).
The CANDIDATE below agreed with an independent brute-force reference on every
small input, but it exceeded {seconds} seconds on inputs within the problem's
stated limits: {inputs}. Return exactly one JSON object
{{"repaired_candidate_code": <complete corrected code>, "explanation": <at most three sentences>}}
that keeps the exact behaviour and entrypoint but meets the problem's efficiency
requirements. Do not change results on any input.

PROBLEM:
{problem}

CANDIDATE CODE:
{candidate_code}
"""


def oracle_prompt(problem: str) -> str:
    return ORACLE_PROMPT.format(version=PROMPT_VERSION, problem=problem)


def adjudicate_prompt(
    *,
    problem: str,
    source: str,
    args: str,
    candidate_output: str,
    reference_output: str,
    candidate_code: str,
    reference_code: str,
) -> str:
    return ADJUDICATE_PROMPT.format(
        version=PROMPT_VERSION,
        problem=problem,
        source=source,
        args=args,
        candidate_output=candidate_output,
        reference_output=reference_output,
        candidate_code=candidate_code,
        reference_code=reference_code,
    )


def performance_prompt(
    *, problem: str, candidate_code: str, result: DifferentialResult, seconds: float
) -> str:
    inputs = json.dumps([item.input_summary for item in result.scale_failures])
    return PERFORMANCE_PROMPT.format(
        version=PROMPT_VERSION,
        problem=problem,
        candidate_code=candidate_code,
        inputs=inputs,
        seconds=seconds,
    )
