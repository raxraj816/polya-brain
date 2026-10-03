"""Summarize a QuixBugs verify-change run: catch rate, false alarms, cost."""

from __future__ import annotations

import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path


def main() -> None:
    root = Path(sys.argv[1])
    rows = [
        json.loads(path.read_text())
        for path in sorted(root.rglob("*.json"))
        if path.name != "manifest.json"
        and "spend" not in path.parts
        and "program" in path.read_text()[:40]
    ]
    bug = Counter(row["bug"]["status"] for row in rows)
    control = Counter(row.get("control", {}).get("status", "missing") for row in rows)
    cost = Decimal(0)
    calls = 0
    seconds = 0.0
    for row in rows:
        for arm in ("bug", "control"):
            for call in row.get(arm, {}).get("model_calls", []):
                calls += 1
                cost += Decimal(str(call.get("cost_usd") or 0))
            seconds += row.get(arm, {}).get("seconds", 0)
    summary = {
        "programs": len(rows),
        "bug_arm": dict(bug),
        "control_arm": dict(control),
        "caught": [r["program"] for r in rows if r["bug"]["status"] == "regressions_found"],
        "missed": [r["program"] for r in rows if r["bug"]["status"] == "no_behavior_change_found"],
        "bug_unverified": {
            r["program"]: r["bug"].get("reason") or r["bug"].get("error")
            for r in rows
            if r["bug"]["status"] not in {"regressions_found", "no_behavior_change_found"}
        },
        "false_alarms": {
            r["program"]: r["control"]["differences"][:1]
            for r in rows
            if r.get("control", {}).get("status") == "regressions_found"
        },
        "control_unverified": {
            r["program"]: r["control"].get("reason") or r["control"].get("error")
            for r in rows
            if r.get("control", {}).get("status")
            not in {"regressions_found", "no_behavior_change_found"}
        },
        "model_calls": calls,
        "provider_reported_usd": str(cost),
        "seconds": round(seconds, 1),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
