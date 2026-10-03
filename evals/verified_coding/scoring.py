"""Isolated withheld-check scoring shared by the runner, validator and re-scorer.

Checks run in a private copy of the candidate's module namespace. They can call the
candidate's functions, but names a check binds (rng, datetime, cases, ...) can never
overwrite the candidate's own globals. The candidate's functions keep their real
module globals. Each check's outcome is then asserted by a short sandbox test.
"""

from __future__ import annotations

import json
from typing import Any

from evals.chapter_13p.coding_execution.evidence import execution_passed

from app.execution import DockerPythonSandbox, DockerSandboxLimits

SCORER_VERSION = "isolated_checks@1"
LIMITS = DockerSandboxLimits(timeout_seconds=20)

_RUNNER = """

import json as _x_json
_x_ns = dict(globals())
_x_res = []
for _x_src in _x_json.loads({checks!r}):
    try:
        exec(compile(_x_src, "<withheld-check>", "exec"), _x_ns)
        _x_res.append(None)
    except BaseException as _x_err:
        _x_res.append(type(_x_err).__name__ + ": " + str(_x_err)[:300])
print("__X_CHECK_RESULTS__=" + _x_json.dumps(_x_res))
"""


def program(code: str, checks: list[str]) -> tuple[str, list[str]]:
    runner = _RUNNER.format(checks=json.dumps(checks))
    tests = [f"assert _x_res[{index}] is None, _x_res[{index}]" for index in range(len(checks))]
    return code + runner, tests


def score_code(code: str | None, checks: list[str]) -> dict[str, Any]:
    if not code:
        return {"passed": False, "reason": "no code delivered", "scorer": SCORER_VERSION}
    source, tests = program(code, checks)
    try:
        result = DockerPythonSandbox(limits=LIMITS).execute(source, tests)
    except ValueError as exc:
        return {"passed": False, "reason": f"scoring admission: {exc}", "scorer": SCORER_VERSION}
    return {
        "passed": execution_passed(result, len(tests)),
        "scorer": SCORER_VERSION,
        "tests": [item.passed for item in result.test_results],
        "timed_out": result.timed_out,
        "exit_code": result.exit_code,
        "stdout_tail": result.stdout[-400:],
        "stderr_tail": result.stderr[-600:],
    }
