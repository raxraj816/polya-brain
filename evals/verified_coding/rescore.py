"""Re-score saved paired attempts with the isolated scorer, without any model call.

Delivered code is recovered from the saved artifacts and accepted only when its
SHA-256 equals the digest recorded by the original scoring, so re-scoring cannot
substitute different code. Writes rescore.json next to every record.json.

PYTHONPATH=backend:. .venv/bin/python -m evals.verified_coding.rescore RUN_DIRECTORY
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.chapter_13p.coding_execution.evidence import digest, extract_code
from pydantic import ValidationError

from app.verified_coding.pipeline import parse_proposal

from .run import CHECKS
from .scoring import SCORER_VERSION, score_code


def _proposal_codes(directory: Path) -> list[str]:
    codes = []
    for path in sorted(
        directory.glob("model-*.response.json"),
        key=lambda p: int(p.name.split("-")[1].split(".")[0]),
    ):
        try:
            codes.append(parse_proposal(json.loads(path.read_text())["text"]).code)
        except ValidationError, ValueError, KeyError:
            continue
    return codes


def _candidates(attempt: Path, arm: str) -> list[str]:
    if arm == "verified":
        code = json.loads((attempt / "verified" / "outcome.json").read_text()).get("code")
        return [code] if code else []
    if arm == "kernel":
        answer = json.loads((attempt / "kernel" / "outcome.json").read_text()).get(
            "delivered_answer"
        )
        code = extract_code(answer or "")
        return [code] if code else []
    codes = _proposal_codes(attempt / arm)
    if arm == "self_review":
        codes += _proposal_codes(attempt / "lean")
    return codes


def rescore(attempt: Path) -> dict[str, Any]:
    record = json.loads((attempt / "record.json").read_text())
    result: dict[str, Any] = {
        "case": record["case"],
        "repeat": record["repeat"],
        "scorer": SCORER_VERSION,
    }
    for arm in ("lean", "self_review", "verified", "kernel"):
        if arm not in record:
            continue
        original = record[arm]["score"]
        wanted = original.get("code_sha256")
        if wanted is None:
            result[arm] = {
                "original_passed": original["passed"],
                "score": {"passed": False, "reason": "no code delivered"},
            }
            continue
        code = next((item for item in _candidates(attempt, arm) if digest(item) == wanted), None)
        if code is None:
            result[arm] = {
                "original_passed": original["passed"],
                "score": {
                    "passed": False,
                    "reason": "delivered code not recoverable with matching digest",
                },
            }
            continue
        result[arm] = {
            "original_passed": original["passed"],
            "score": score_code(code, CHECKS[record["case"]]),
        }
    path = attempt / "rescore.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    for record in sorted(args.run_directory.rglob("record.json")):
        result = rescore(record.parent)
        print(
            json.dumps(
                {
                    "case": result["case"],
                    "repeat": result["repeat"],
                    **{
                        arm: [result[arm]["original_passed"], result[arm]["score"]["passed"]]
                        for arm in ("lean", "self_review", "verified", "kernel")
                        if arm in result
                    },
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
