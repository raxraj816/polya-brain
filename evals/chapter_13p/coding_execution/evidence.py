"""Shared fail-closed rules for coding experiment artifacts, not product contracts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from app.execution.sandbox import SandboxExecutionResult


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def checks_digest(checks: list[str]) -> str:
    return digest(json.dumps(checks, ensure_ascii=False, separators=(",", ":")))


def load_cases(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("cases must be a nonempty list")
    cases: dict[str, str] = {}
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("every case must be an object")
        case, prompt = item.get("id"), item.get("prompt")
        if not isinstance(case, str) or not case.strip() or case != case.strip():
            raise ValueError("every case needs a nonempty, unpadded id")
        if case in cases:
            raise ValueError(f"duplicate case: {case}")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"case {case} needs a prompt")
        cases[case] = prompt
    return cases


def assignments(values: list[str]) -> dict[str, Path]:
    if not values:
        raise ValueError("at least one case assignment is required")
    parsed: dict[str, Path] = {}
    for value in values:
        case, separator, directory = value.partition("=")
        case = case.strip()
        if not separator or not case or not directory.strip():
            raise ValueError("expected CASE=RUN_DIRECTORY")
        if case in parsed:
            raise ValueError(f"duplicate assignment: {case}")
        parsed[case] = Path(directory).expanduser()
    return parsed


def extract_code(answer: str) -> str | None:
    """Require exactly one fenced block, explicitly Python or unlabelled."""
    blocks = re.findall(r"^```([^\n]*)\n(.*?)^```[ \t]*$", answer, re.MULTILINE | re.DOTALL)
    if len(blocks) != 1 or answer.count("```") != 2:
        return None
    language, code = blocks[0]
    if language.strip().lower() not in {"", "python", "py"}:
        return None
    return code.strip() or None


def execution_passed(result: SandboxExecutionResult, count: int) -> bool:
    return bool(
        count > 0
        and result.exit_code == 0
        and not result.timed_out
        and not result.output_truncated
        and result.tests_run == count
        and [test.index for test in result.test_results] == list(range(1, count + 1))
        and all(test.passed for test in result.test_results)
    )
