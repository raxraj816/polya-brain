"""Run the independent coding checks as one reproducible readiness gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .evidence import assignments as parse_assignments
    from .evidence import load_cases
    from .verify import CHECKS, verify
except ImportError:  # direct script execution
    from evidence import assignments as parse_assignments
    from evidence import load_cases
    from verify import CHECKS, verify


def run_gate(cases_path: Path, assignments: list[str]) -> dict[str, Any]:
    expected = set(load_cases(cases_path))
    parsed = parse_assignments(assignments)
    if expected - set(CHECKS):
        raise ValueError("declared case has no independent checks")
    supplied = set(parsed)
    missing = sorted(expected - supplied)
    unexpected = sorted(supplied - expected)
    if missing or unexpected:
        return {
            "gate": "coding_execution_readiness",
            "passed": False,
            "reason": "case coverage does not match the declared benchmark",
            "missing_cases": missing,
            "unexpected_cases": unexpected,
            "cases": [],
        }

    results = []
    for case in sorted(expected):
        directory = parsed[case]
        if not directory.is_dir():
            results.append({"case": case, "passed": False, "reason": "run directory missing"})
            continue
        result = verify(case, directory)
        result["passed"] = bool(
            result.get("passed")
            and result.get("runtime_reported_pass")
            and result.get("delivered_code_identical_to_executed")
        )
        results.append(result)

    return {
        "gate": "coding_execution_readiness",
        "passed": all(bool(result.get("passed")) for result in results),
        "case_count": len(results),
        "passed_cases": sum(bool(result.get("passed")) for result in results),
        "cases": results,
        "standard": {
            "independent_checks": True,
            "runtime_report_must_pass": True,
            "delivered_code_must_match_executed_code": True,
            "external_judge_submission": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).with_name("cases.json"),
        help="Declared coding benchmark cases JSON.",
    )
    parser.add_argument(
        "--case",
        action="append",
        required=True,
        metavar="ID=RUN_DIRECTORY",
        help="Run directory for one declared case; repeat for every case.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()
    summary = run_gate(args.cases, args.case)
    encoded = json.dumps(summary, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
