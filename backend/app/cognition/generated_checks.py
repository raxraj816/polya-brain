"""Reject unsourced literal expected outputs before model-generated tests are admitted."""

from __future__ import annotations

import ast
import io
import tokenize
from collections.abc import Mapping, Sequence
from contextlib import suppress

from app.graph.state import StateEvent
from app.models.contracts import PlanTask, ReasoningMode

VERSION = "generated_check_sources@0.1.0"


def check_source_event(tasks: Sequence[PlanTask], engine_name: str) -> list[StateEvent]:
    task_ids = [task.id for task in tasks if task.tool_name == "python_sandbox"]
    return (
        [
            StateEvent(
                engine_name=engine_name,
                event_type="generated_check_sources_screened",
                reasoning_mode=ReasoningMode.VERIFY,
                summary="Screened literal test expectations against supplied examples and admitted checks; oracle correctness still requires review.",
                metadata={
                    "version": VERSION,
                    "task_ids": [task_id for task_id in task_ids],
                    "semantic_oracle_review_required": True,
                },
            )
        ]
        if task_ids
        else []
    )


def _tokens(source: str) -> tuple[tuple[int, str], ...]:
    tokens = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type in {
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.COMMENT,
            } or (token.type == tokenize.ERRORTOKEN and token.string.isspace()):
                continue
            value = token.string
            if token.type == tokenize.STRING:
                with suppress(ValueError, SyntaxError):
                    value = repr(ast.literal_eval(value))
            # A prose example can end with "== 1."; retain the sentence period
            # as its own token, never treat "== 1" as a prefix of "== 10".
            if token.type == tokenize.NUMBER and value.endswith("."):
                tokens.append((token.type, value[:-1]))
                tokens.append((tokenize.OP, "."))
                continue
            tokens.append((token.type, value))
    except tokenize.TokenError, IndentationError:
        # Partial tokenization is conservative: unmatched examples are rejected.
        pass
    return tuple(tokens)


def _literal(node: ast.AST) -> bool:
    try:
        ast.literal_eval(node)
    except ValueError, TypeError, SyntaxError:
        return False
    return True


def validate_generated_checks(tasks: Sequence[PlanTask], context: object) -> None:
    """Necessary origin check, not proof that a reference or implementation is correct."""
    if not isinstance(context, Mapping) or not isinstance(context.get("raw_input"), str):
        return
    supplied = _tokens(context["raw_input"])
    existing = context.get("existing_python_tests", ())
    known = (
        set(existing)
        if isinstance(existing, (list, tuple)) and all(isinstance(item, str) for item in existing)
        else set()
    )
    for task in tasks:
        if task.tool_name != "python_sandbox":
            continue
        tests = task.params.get("tests")
        if not isinstance(tests, list):
            continue  # Parameter bounds are enforced at the capability boundary.
        for test in tests:
            if not isinstance(test, str) or test in known:
                continue
            try:
                tree = ast.parse(test)
            except SyntaxError as exc:
                raise ValueError("Python checks must have valid syntax before admission.") from exc
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
                    continue
                comparison = node.test
                if len(comparison.ops) != 1 or not isinstance(comparison.ops[0], (ast.Eq, ast.Is)):
                    continue
                left, right = comparison.left, comparison.comparators[0]
                if not (
                    (isinstance(left, ast.Call) and _literal(right))
                    or (isinstance(right, ast.Call) and _literal(left))
                ):
                    continue
                wanted = _tokens(ast.unparse(comparison))
                if any(
                    supplied[index : index + len(wanted)] == wanted
                    for index in range(len(supplied) - len(wanted) + 1)
                ):
                    continue
                raise ValueError(
                    "Generated check contains a literal expected output not present as an explicit "
                    "example in raw_input. Preserve user examples and existing checks. For invented "
                    "cases, replace guessed literal expectations with assertions against a simple "
                    "executable reference derived from the specification; do not call the candidate "
                    "from the reference or claim unobserved execution."
                )
