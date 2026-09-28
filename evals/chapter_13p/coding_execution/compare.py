"""Replay selected coding artifacts; never infer correctness from completed status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.execution import DockerPythonSandbox, DockerSandboxLimits

try:
    from .evidence import assignments as parse_assignments
    from .evidence import checks_digest, digest, execution_passed, extract_code, load_cases
    from .verify import CHECKS, verify
except ImportError:  # direct script execution
    from evidence import assignments as parse_assignments
    from evidence import checks_digest, digest, execution_passed, extract_code, load_cases
    from verify import CHECKS, verify


def verify_direct(case: str, record: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"passed": False}
    try:
        prompt, code = record.get("prompt"), record.get("code")
        response = record.get("response")
        if (
            not isinstance(prompt, str)
            or not isinstance(code, str)
            or not isinstance(response, dict)
        ):
            result["reason"] = (
                "Saved prompt, response or code unavailable; reported pass is not replayable."
            )
            return result
        if (
            digest(prompt) != record.get("prompt_sha256")
            or digest(code) != record.get("code_sha256")
            or extract_code(response.get("text", "")) != code
            or record.get("checks_sha256") != checks_digest(CHECKS[case])
        ):
            result["reason"] = "Saved artifact binding or check version differs."
            return result
        sandbox = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=20))
        execution = sandbox.execute(code, CHECKS[case])
        result.update(
            passed=execution_passed(execution, len(CHECKS[case])),
            independent_checks=execution.model_dump(mode="json"),
            prompt_sha256=digest(prompt),
            code_sha256=digest(code),
            checks_sha256=checks_digest(CHECKS[case]),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result["failure"] = type(exc).__name__
    return result


def total_tokens(usage: Any) -> int | None:
    if not isinstance(usage, dict):
        return None
    values = [usage.get("input_tokens"), usage.get("output_tokens")]
    if any(type(value) is not int or value < 0 for value in values):
        return None
    return sum(values)


def compare(
    baseline_path: Path, assignments: list[str], cases_path: Path | None = None
) -> dict[str, Any]:
    cases = load_cases(cases_path or Path(__file__).with_name("cases.json"))
    if set(cases) - set(CHECKS):
        raise ValueError("declared cases need independent checks")
    directories = parse_assignments(assignments)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    direct_cases = {}
    for item in baseline.get("cases", []):
        if not isinstance(item, dict) or item.get("case") not in cases:
            raise ValueError("invalid baseline case")
        if item["case"] in direct_cases:
            raise ValueError("duplicate baseline case")
        direct_cases[item["case"]] = item
    if set(direct_cases) != set(cases) or set(directories) != set(cases):
        raise ValueError("comparison requires every declared case in both arms")
    rows = []
    for case, directory in sorted(directories.items()):
        direct = direct_cases[case]
        polya_check = verify(case, directory)
        direct_check = verify_direct(case, direct)
        try:
            run = json.loads((directory / "run.json").read_text())
        except OSError, ValueError:
            run = {}
        usage = run.get("usage")
        direct_usage = direct.get("usage")
        prompt_matches = polya_check.get("prompt_sha256") == digest(
            cases[case]
        ) and direct_check.get("prompt_sha256") == digest(cases[case])
        rows.append(
            {
                "case": case,
                "polya_passed": polya_check.get("passed") is True,
                "direct_passed": direct_check.get("passed") is True,
                "polya_reported_completed": run.get("status") == "completed",
                "direct_reported_pass": direct.get("passed") is True,
                "polya_verification": polya_check,
                "direct_verification": direct_check,
                "both_inputs_match_declared_case": prompt_matches,
                "polya_model_calls": usage.get("model_calls") if isinstance(usage, dict) else None,
                "direct_model_calls": direct.get("model_calls"),
                "polya_total_tokens": total_tokens(usage),
                "direct_total_tokens": total_tokens(direct_usage),
                "polya_elapsed_ms": run.get("elapsed_ms"),
                "direct_elapsed_ms": direct.get("elapsed_ms"),
                "polya_normalized_scheduling_cost": (
                    usage.get("normalized_cost") if isinstance(usage, dict) else None
                ),
                "direct_estimated_cost_usd": (
                    direct_usage.get("estimated_cost_usd")
                    if isinstance(direct_usage, dict)
                    else None
                ),
            }
        )
    return {
        "comparison": "selected_artifact_replay@0.2.0",
        "cases": rows,
        "all_polya_passed": all(row["polya_passed"] for row in rows),
        "all_direct_passed": all(row["direct_passed"] for row in rows),
        "all_inputs_match": all(row["both_inputs_match_declared_case"] for row in rows),
        "controlled_superiority_evidence": False,
        "limitations": [
            "Selected historical runs do not include the cost of all development attempts.",
            "The direct one-call arm has no tools; tool access and budgets are unequal.",
            "Same-model routing across every request is not established by this replay.",
            "Normalized scheduling cost and USD are different units and must not be compared.",
            "Unavailable usage is null; an interrupted baseline is incomplete evidence.",
            "Checks are developer-authored; they do not prove general correctness or complexity.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--polya", action="append", required=True, metavar="CASE=RUN_DIRECTORY")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Reserve the destination before replaying; never replace earlier evidence.
    with args.output.open("x", encoding="utf-8") as stream:
        summary = compare(args.baseline, args.polya, args.cases)
        stream.write(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return (
        0
        if (
            summary["all_polya_passed"]
            and summary["all_direct_passed"]
            and summary["all_inputs_match"]
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
