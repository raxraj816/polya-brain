#!/usr/bin/env python3
"""Verify the generated pre-platform proof artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = ROOT / "proofs" / "pre_platform" / "runs" / "cache_investigation"

REQUIRED_FILES = [
    "trace.jsonl",
    "direct_llm_baseline.md",
    "evidence.json",
    "hypotheses.json",
    "verification_checklist.json",
    "report.md",
    "baseline_comparison.json",
]

REQUIRED_REPORT_SECTIONS = [
    "Final conclusion",
    "Confidence level",
    "Evidence used",
    "Evidence against",
    "Checks performed",
    "Open questions",
    "Recommended next action",
    "Audit trace",
]

REQUIRED_REASONING_MODES = {"explore", "reframe", "compare", "verify", "reflect"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit(f"VERIFY FAILED: {message}")


def verify_files(run_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (run_dir / name).exists()]
    if missing:
        fail(f"missing required artifacts: {', '.join(missing)}")


def verify_report(run_dir: Path) -> None:
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_REPORT_SECTIONS if f"## {section}" not in report]
    if missing:
        fail(f"report missing required sections: {', '.join(missing)}")


def verify_trace(run_dir: Path) -> None:
    events = [
        json.loads(line)
        for line in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    modes = {event.get("reasoning_mode") for event in events}
    missing = REQUIRED_REASONING_MODES - modes
    if missing:
        fail(f"trace missing reasoning modes: {', '.join(sorted(missing))}")
    for event in events:
        for field in ["id", "session_id", "engine_name", "event_type", "reasoning_mode", "summary", "metadata", "created_at"]:
            if field not in event:
                fail(f"trace event missing field {field}: {event}")


def verify_evidence(run_dir: Path) -> None:
    evidence = load_json(run_dir / "evidence.json")
    required = {"id", "source_type", "source_uri", "claim", "raw_excerpt", "reliability_score", "relevance_score"}
    for item in evidence:
        missing = required - set(item)
        if missing:
            fail(f"evidence item {item.get('id', '<unknown>')} missing fields: {', '.join(sorted(missing))}")
        if not item["source_uri"]:
            fail(f"evidence item {item['id']} has empty source_uri")


def verify_hypotheses(run_dir: Path) -> None:
    hypotheses = load_json(run_dir / "hypotheses.json")
    if len(hypotheses) < 3:
        fail("expected at least three divergent hypotheses")
    selected = [item for item in hypotheses if item.get("status") == "selected"]
    if len(selected) != 1:
        fail("expected exactly one selected hypothesis")
    for hypothesis in hypotheses:
        if "novelty_score" in hypothesis:
            fail(f"hypothesis {hypothesis['id']} includes forbidden core MVP field novelty_score")
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
                fail(f"hypothesis {hypothesis.get('id', '<unknown>')} missing field {field}")
    if not selected[0]["evidence_for"] or not selected[0]["verification_checks"]:
        fail("selected hypothesis must include evidence_for and verification_checks")


def verify_checks(run_dir: Path) -> None:
    verification = load_json(run_dir / "verification_checklist.json")
    if verification.get("passed") is not True:
        fail("verification checklist did not pass")
    checks = verification.get("checks_run", [])
    if not checks:
        fail("verification checklist has no checks_run")
    deterministic = [item for item in checks if item.get("deterministic") is True]
    if not deterministic:
        fail("expected at least one deterministic/non-LLM check")
    failed = [item for item in checks if item.get("result") != "passed"]
    if failed:
        fail(f"verification has failed checks: {failed}")


def verify_baseline_comparison(run_dir: Path) -> None:
    comparison = load_json(run_dir / "baseline_comparison.json")
    if comparison.get("result") != "polya_artifact_more_auditable":
        fail("baseline comparison did not show a more auditable Polya artifact")
    polya_count = comparison["polya_score"]["required_section_count"]
    baseline_count = comparison["baseline_score"]["required_section_count"]
    if polya_count <= baseline_count:
        fail("Polya artifact did not beat baseline on required report sections")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify pre-platform proof artifacts.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir
    verify_files(run_dir)
    verify_report(run_dir)
    verify_trace(run_dir)
    verify_evidence(run_dir)
    verify_hypotheses(run_dir)
    verify_checks(run_dir)
    verify_baseline_comparison(run_dir)
    print(f"Pre-platform proof verified: {run_dir}")


if __name__ == "__main__":
    main()
