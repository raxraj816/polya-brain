"""Validate withheld checks: correct references must pass and every mutant must fail.

PYTHONPATH=backend:. .venv/bin/python -m evals.verified_coding.validate_checks [--output FILE]
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from evals.chapter_13p.coding_execution.evidence import checks_digest

from app.execution import DockerSandboxLimits

from .checks import CHECKS
from .checks_v2 import CHECKS_V2
from .references import CORRECT, MUTANTS
from .references_v2 import CORRECT_V2, MUTANTS_V2
from .scoring import score_code

CHECKS = {**CHECKS, **CHECKS_V2}
CORRECT = {**CORRECT, **CORRECT_V2}
MUTANTS = {**MUTANTS, **MUTANTS_V2}

SCORING_LIMITS = DockerSandboxLimits(timeout_seconds=20)


def unsafe_globals(check: str) -> list[str]:
    """Top-level names a check binds that could overwrite the candidate's own names."""
    names: list[str] = []
    for node in ast.parse(check).body:
        targets: list[ast.AST] = []
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names += [(alias.asname or alias.name).split(".")[0] for alias in node.names]
        elif isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign, ast.For)):
            targets = [node.target]
        for target in targets:
            names += [item.id for item in ast.walk(target) if isinstance(item, ast.Name)]
    return sorted({name for name in names if not name.startswith("_x_")})


def run(code: str, checks: list[str]) -> dict[str, object]:
    result = score_code(code, checks)
    return {**result, "runtime_ms": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case", action="append")
    parser.add_argument(
        "--namespace-strict",
        action="store_true",
        help="fail when a check binds a top-level name without the _x_ prefix",
    )
    args = parser.parse_args()
    report: dict[str, object] = {}
    ok = True
    for case in args.case or sorted(CHECKS):
        checks = CHECKS[case]
        sizes = [len(item) for item in checks]
        if len(checks) > 20 or max(sizes) > 2000:
            raise SystemExit(f"{case}: check set exceeds sandbox bounds {sizes}")
        unsafe = sorted({name for item in checks for name in unsafe_globals(item)})
        if args.namespace_strict and unsafe:
            ok = False
            print(json.dumps({"case": case, "unsafe_globals": unsafe}), flush=True)
        correct = run(CORRECT[case], checks)
        mutants = [run(code, checks) for code in MUTANTS[case]]
        valid = bool(correct["passed"]) and not any(item["passed"] for item in mutants)
        ok &= valid
        report[case] = {
            "valid": valid,
            "checks_sha256": checks_digest(checks),
            "check_sizes": sizes,
            "correct": correct,
            "mutants": mutants,
        }
        print(
            json.dumps(
                {
                    "case": case,
                    "valid": valid,
                    "correct_passed": correct["passed"],
                    "correct_ms": correct["runtime_ms"],
                    "mutants_failed": [not item["passed"] for item in mutants],
                }
            ),
            flush=True,
        )
        if not correct["passed"]:
            print(correct["stderr_tail"] or correct["stdout_tail"], flush=True)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
