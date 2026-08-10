"""Chapter 11 prompt and parser boundary."""

from app.problem_understanding.contracts import (
    MODE_CLARIFICATION_THRESHOLD,
    ParserRetryPolicy,
    ProblemUnderstandingExample,
    ProblemUnderstandingOutput,
    ProblemUnderstandingParseResult,
    ProblemUnderstandingRunResult,
    PromptExampleCategory,
)
from app.problem_understanding.examples import PROBLEM_UNDERSTANDING_EXAMPLES
from app.problem_understanding.fallbacks import deterministic_problem_understanding
from app.problem_understanding.parser import (
    ProblemUnderstandingParseError,
    parse_problem_understanding,
)
from app.problem_understanding.prompt import (
    PROBLEM_UNDERSTANDING_PROMPT_VERSION,
    PROBLEM_UNDERSTANDING_REPAIR_PROMPT_VERSION,
    build_problem_understanding_repair_request,
    build_problem_understanding_request,
    format_problem_understanding_input,
    problem_understanding_json_schema,
    problem_understanding_system_prompt,
)
from app.problem_understanding.service import generate_problem_understanding

__all__ = [
    "MODE_CLARIFICATION_THRESHOLD",
    "PROBLEM_UNDERSTANDING_EXAMPLES",
    "PROBLEM_UNDERSTANDING_PROMPT_VERSION",
    "PROBLEM_UNDERSTANDING_REPAIR_PROMPT_VERSION",
    "ParserRetryPolicy",
    "ProblemUnderstandingExample",
    "ProblemUnderstandingOutput",
    "ProblemUnderstandingParseError",
    "ProblemUnderstandingParseResult",
    "ProblemUnderstandingRunResult",
    "PromptExampleCategory",
    "build_problem_understanding_repair_request",
    "build_problem_understanding_request",
    "deterministic_problem_understanding",
    "format_problem_understanding_input",
    "generate_problem_understanding",
    "parse_problem_understanding",
    "problem_understanding_json_schema",
    "problem_understanding_system_prompt",
]
