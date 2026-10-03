"""Aggregate paired verified-coding records into outcome, calibration and cost tables.

PYTHONPATH=backend:. .venv/bin/python -m evals.verified_coding.report RUN_DIRECTORY [--output FILE]
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

ARMS = ("lean", "self_review", "verified", "kernel")
CERTIFIED = {"verified", "repaired_and_verified"}


def records(root: Path, rescored: bool = False) -> list[dict[str, Any]]:
    """Load attempts; with rescored=True, replace each arm's score by rescore.json."""
    found = []
    for path in sorted(root.rglob("record.json")):
        record = json.loads(path.read_text())
        if rescored:
            update = json.loads((path.parent / "rescore.json").read_text())
            for arm in ARMS:
                if arm in record:
                    record[arm] = {**record[arm], "score": update[arm]["score"]}
        found.append(record)
    return found


def _usage_cost(items: list[dict[str, Any]]) -> tuple[Decimal, int, int, bool]:
    cost, tokens_in, tokens_out, complete = Decimal(0), 0, 0, True
    for item in items:
        value = item.get("cost_usd", item.get("estimated_cost_usd"))
        if "failure" in item or value is None:
            complete = False
        else:
            cost += Decimal(str(value))
        tokens_in += int(item.get("input_tokens") or 0)
        tokens_out += int(item.get("output_tokens") or 0)
    return cost, tokens_in, tokens_out, complete


def kernel_usage(root: Path, record: dict[str, Any]) -> list[dict[str, Any]]:
    directory = next(
        (
            path / "kernel"
            for path in root.rglob(f"{record['case']}-{record['repeat']}")
            if (path / "kernel").is_dir()
        ),
        None,
    )
    if directory is None:
        return []
    items = []
    for response in sorted(directory.glob("model-*.response.json")):
        usage = json.loads(response.read_text())["usage"]
        items.append(usage)
    items += [{"failure": True} for _ in directory.glob("model-*.failure.json")]
    return items


def arm_summary(root: Path, rows: list[dict[str, Any]], arm: str) -> dict[str, Any] | None:
    present = [row for row in rows if arm in row]
    if not present:
        return None
    cost, tin, tout, complete = Decimal(0), 0, 0, True
    calls = 0
    seconds = 0.0
    for row in present:
        data = row[arm]
        usage = kernel_usage(root, row) if arm == "kernel" else data.get("usage", [])
        c, i, o, ok = _usage_cost(usage)
        cost, tin, tout, complete = cost + c, tin + i, tout + o, complete and ok
        calls += (
            sum(1 for item in usage if "failure" not in item)
            if arm != "verified"
            else int(data.get("model_calls", 0))
        )
        elapsed = (
            data.get("usage", {}).get("elapsed_ms") if arm == "kernel" else data.get("elapsed_ms")
        )
        seconds += float(elapsed or 0) / 1000
    passed = sum(1 for row in present if row[arm]["score"]["passed"])
    return {
        "attempts": len(present),
        "passed": passed,
        "model_calls": calls,
        "input_tokens": tin,
        "output_tokens": tout,
        "provider_reported_usd": str(cost),
        "cost_complete": complete,
        "seconds": round(seconds, 1),
    }


def transitions(rows: list[dict[str, Any]], arm: str) -> dict[str, int]:
    result = {"fixed": 0, "harmed": 0, "both_pass": 0, "both_fail": 0}
    for row in rows:
        before = row["lean"]["score"]["passed"]
        after = row[arm]["score"]["passed"]
        key = (
            "both_pass"
            if before and after
            else "fixed"
            if after
            else "harmed"
            if before
            else "both_fail"
        )
        result[key] += 1
    return result


def calibration(rows: list[dict[str, Any]]) -> dict[str, int]:
    result = {
        "certified_and_correct": 0,
        "certified_but_wrong": 0,
        "flagged_and_wrong": 0,
        "flagged_but_correct": 0,
    }
    for row in rows:
        certified = row["verified"]["status"] in CERTIFIED
        correct = row["verified"]["score"]["passed"]
        key = (
            "certified_and_correct"
            if certified and correct
            else "certified_but_wrong"
            if certified
            else "flagged_but_correct"
            if correct
            else "flagged_and_wrong"
        )
        result[key] += 1
    return result


def spend(root: Path) -> dict[str, Any]:
    reported, pending, calls = Decimal(0), Decimal(0), 0
    for spend_dir in root.rglob("spend"):
        reported_ids = {path.name.split(".")[0] for path in spend_dir.glob("*.reported.json")}
        for path in spend_dir.glob("*.reported.json"):
            reported += Decimal(str(json.loads(path.read_text())["provider_reported_cost_usd"]))
            calls += 1
        for path in spend_dir.glob("*.reserved.json"):
            if path.name.split(".")[0] not in reported_ids:
                pending += Decimal(json.loads(path.read_text())["reserve_usd"])
    return {
        "provider_calls": calls,
        "provider_reported_usd": str(reported),
        "unreconciled_reservations_usd": str(pending),
        "worst_case_usd": str(reported + pending),
    }


def per_case(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table = []
    for row in sorted(rows, key=lambda item: (item["case"], item["repeat"])):
        table.append(
            {
                "case": row["case"],
                "repeat": row["repeat"],
                **{arm: row[arm]["score"]["passed"] for arm in ARMS if arm in row},
                "verified_status": row["verified"]["status"],
                "findings": row["verified"].get("findings"),
            }
        )
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rescored", action="store_true", help="use isolated-scorer results")
    args = parser.parse_args()
    rows = records(args.run_directory, args.rescored)
    report = {
        "scoring": "isolated_checks@1 (rescore.json)" if args.rescored else "original run scoring",
        "attempts": len(rows),
        "arms": {arm: arm_summary(args.run_directory, rows, arm) for arm in ARMS},
        "paired_vs_lean": {arm: transitions(rows, arm) for arm in ("self_review", "verified")},
        "verified_calibration": calibration(rows),
        "spend": spend(args.run_directory),
        "per_case": per_case(rows),
    }
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
