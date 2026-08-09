#!/usr/bin/env python3
"""Run the default pre-platform proof case."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from proofs.pre_platform.core import (
    DEFAULT_CASE,
    DEFAULT_OUTPUT_ROOT,
    run_from_case_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PolyaBrain pre-platform proof harness.")
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--baseline", type=Path, help="Optional static baseline fixture path.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--clean", action="store_true", help="Delete the target run directory before writing artifacts.")
    parser.add_argument(
        "--baseline-provider",
        choices=["auto", "template", "openai", "openrouter"],
        default="auto",
        help="Baseline provider used when --baseline is not supplied.",
    )
    parser.add_argument("--baseline-model")
    parser.add_argument("--baseline-timeout-seconds", type=float, default=30)
    parser.add_argument("--run-id")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = run_from_case_path(
        case_path=args.case,
        output_root=args.output_root,
        clean=args.clean,
        baseline_provider=args.baseline_provider,
        baseline_path=args.baseline,
        baseline_model=args.baseline_model,
        baseline_timeout_seconds=args.baseline_timeout_seconds,
        run_id=args.run_id,
    )
    print(f"Wrote pre-platform proof artifacts to {run_dir}")


if __name__ == "__main__":
    main()
