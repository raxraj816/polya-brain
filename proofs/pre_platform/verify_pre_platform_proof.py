#!/usr/bin/env python3
"""Verify generated pre-platform investigation artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from proofs.pre_platform.core import DEFAULT_OUTPUT_ROOT, REQUIRED_FILES, REQUIRED_REPORT_SECTIONS


DEFAULT_RUN_DIR = DEFAULT_OUTPUT_ROOT / "cache_investigation"
REQUIRED_REASONING_MODES = {"explore", "reframe", "compare", "verify", "reflect"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit(f"VERIFY FAILED: {message}")


def verify_files(run_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (run_dir / name).exists()]
    if missing:
        fail(f"{run_dir}: missing required artifacts: {', '.join(missing)}")


def verify_report(run_dir: Path) -> None:
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_REPORT_SECTIONS if f"## {section}" not in report]
    if missing:
        fail(f"{run_dir}: report missing required sections: {', '.join(missing)}")


def verify_trace(run_dir: Path) -> None:
    events = [
        json.loads(line)
        for line in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    modes = {event.get("reasoning_mode") for event in events}
    missing = REQUIRED_REASONING_MODES - modes
    if missing:
        fail(f"{run_dir}: trace missing reasoning modes: {', '.join(sorted(missing))}")
    for event in events:
        for field in ["id", "session_id", "engine_name", "event_type", "reasoning_mode", "summary", "metadata", "created_at"]:
            if field not in event:
                fail(f"{run_dir}: trace event missing field {field}: {event}")


def verify_evidence(run_dir: Path) -> None:
    evidence = load_json(run_dir / "evidence.json")
    required = {"id", "source_type", "source_uri", "claim", "raw_excerpt", "reliability_score", "relevance_score"}
    for item in evidence:
        missing = required - set(item)
        if missing:
            fail(f"{run_dir}: evidence item {item.get('id', '<unknown>')} missing fields: {', '.join(sorted(missing))}")
        if not item["source_uri"]:
            fail(f"{run_dir}: evidence item {item['id']} has empty source_uri")


def verify_hypotheses(run_dir: Path) -> None:
    hypotheses = load_json(run_dir / "hypotheses.json")
    if len(hypotheses) < 3:
        fail(f"{run_dir}: expected at least three divergent hypotheses")
    selected = [item for item in hypotheses if item.get("status") == "selected"]
    if len(selected) != 1:
        fail(f"{run_dir}: expected exactly one selected hypothesis")
    for hypothesis in hypotheses:
        if "novelty_score" in hypothesis:
            fail(f"{run_dir}: hypothesis {hypothesis['id']} includes forbidden core MVP field novelty_score")
        for field in [
            "statement",
            "mechanism",
            "origin",
            "analogical_source_ids",
            "expected_signals",
            "evidence_for",
            "evidence_against",
            "verification_checks",
            "falsification_criteria",
            "confidence",
            "selection_rationale",
            "status",
        ]:
            if field not in hypothesis:
                fail(f"{run_dir}: hypothesis {hypothesis.get('id', '<unknown>')} missing field {field}")
    if not selected[0]["evidence_for"] or not selected[0]["verification_checks"]:
        fail(f"{run_dir}: selected hypothesis must include evidence_for and verification_checks")


def verify_checks(run_dir: Path) -> None:
    verification = load_json(run_dir / "verification_checklist.json")
    if verification.get("passed") is not True:
        fail(f"{run_dir}: verification checklist did not pass")
    checks = verification.get("checks_run", [])
    if not checks:
        fail(f"{run_dir}: verification checklist has no checks_run")
    deterministic = [item for item in checks if item.get("deterministic") is True]
    if not deterministic:
        fail(f"{run_dir}: expected at least one deterministic/non-LLM check")
    failed = [item for item in checks if item.get("result") != "passed"]
    if failed:
        fail(f"{run_dir}: verification has failed checks: {failed}")


def verify_baseline_comparison(run_dir: Path) -> None:
    comparison = load_json(run_dir / "baseline_comparison.json")
    required = {"baseline_kind", "baseline_metadata", "baseline_score", "polya_score", "result", "why"}
    missing = required - set(comparison)
    if missing:
        fail(f"{run_dir}: baseline comparison missing fields: {', '.join(sorted(missing))}")
    if comparison["polya_score"]["required_section_count"] < len(REQUIRED_REPORT_SECTIONS):
        fail(f"{run_dir}: Polya artifact does not include all required report sections")
    if comparison["result"] not in {"polya_artifact_more_auditable", "baseline_matches_required_sections"}:
        fail(f"{run_dir}: unexpected baseline comparison result: {comparison['result']}")


def verify_run(run_dir: Path) -> None:
    verify_files(run_dir)
    verify_report(run_dir)
    verify_trace(run_dir)
    verify_evidence(run_dir)
    verify_hypotheses(run_dir)
    verify_checks(run_dir)
    verify_baseline_comparison(run_dir)
    print(f"Pre-platform proof verified: {run_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify pre-platform proof artifacts.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--all", action="store_true", help="Verify every run directory under proofs/pre_platform/runs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.all:
        run_dirs = sorted(path for path in DEFAULT_OUTPUT_ROOT.iterdir() if path.is_dir())
        if not run_dirs:
            fail(f"no run directories found under {DEFAULT_OUTPUT_ROOT}")
        for run_dir in run_dirs:
            verify_run(run_dir)
        return
    verify_run(args.run_dir)


if __name__ == "__main__":
    main()
