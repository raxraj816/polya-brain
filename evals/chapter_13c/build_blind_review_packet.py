#!/usr/bin/env python3
"""Create condition-blinded human-review artifacts from a completed outcome run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EVAL_ROOT = Path(__file__).resolve().parent


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _blind_id(run_id: str, case_id: str, repetition: int, condition: str) -> str:
    digest = hashlib.sha256(
        f"{run_id}|{case_id}|{repetition}|{condition}|polyabrain-blind-v1".encode()
    ).hexdigest()[:12]
    return f"response-{digest}"


def _case_definitions() -> dict[str, dict[str, Any]]:
    cases = _read_json(EVAL_ROOT / "outcome_cases.json")
    if not isinstance(cases, list):
        raise ValueError("outcome case definitions must be a list")
    return {str(item["id"]): item for item in cases}


def build_packet(summary_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a blind review packet and separately stored condition key."""
    summary = _read_json(summary_path)
    if not isinstance(summary, dict) or summary.get("status") != "complete":
        raise ValueError("blind review requires a completed outcome summary")
    raw_results = summary.get("cases")
    if not isinstance(raw_results, list) or not raw_results:
        raise ValueError("completed summary contains no comparison pairs")
    run_id = str(summary["run_id"])
    definitions = _case_definitions()
    review_items: list[dict[str, Any]] = []
    answer_key: dict[str, dict[str, Any]] = {}

    for result in raw_results:
        case_id = str(result["case_id"])
        repetition = int(result["repetition"])
        definition = definitions[case_id]
        pair_responses: list[dict[str, Any]] = []
        for condition in ("polya", "direct"):
            output = result[condition]
            blind_id = _blind_id(run_id, case_id, repetition, condition)
            pair_responses.append(
                {
                    "response_id": blind_id,
                    "conclusion": output.get("conclusion"),
                    "evidence_source_uris": output.get("evidence_source_uris", []),
                    "checks_performed": output.get("checks_performed", []),
                    "terminal_status": output.get("terminal_status"),
                }
            )
            answer_key[blind_id] = {
                "condition": condition,
                "case_id": case_id,
                "repetition": repetition,
            }
        pair_responses.sort(key=lambda item: str(item["response_id"]))
        review_items.append(
            {
                "case_id": case_id,
                "category": result["category"],
                "repetition": repetition,
                "problem_statement": definition["problem_statement"],
                "success_criteria": definition["success_criteria"],
                "source_observations": [
                    {
                        "source_uri": (f"fixture://chapter-13c-outcome/{case_id}/{capability}"),
                        "observation": tool.get("observation"),
                        "failure": tool.get("failure"),
                    }
                    for capability, tool in definition["tools"].items()
                ],
                "responses": pair_responses,
                "review_form": {
                    item["response_id"]: {
                        "correctness_1_to_5": None,
                        "evidence_quality_1_to_5": None,
                        "verification_quality_1_to_5": None,
                        "usefulness_1_to_5": None,
                        "unsafe_or_unsupported_claim": None,
                        "notes": "",
                    }
                    for item in pair_responses
                },
                "preferred_response_id": None,
            }
        )

    review_items.sort(
        key=lambda item: hashlib.sha256(
            f"{run_id}|{item['case_id']}|{item['repetition']}".encode()
        ).hexdigest()
    )
    packet = {
        "review_type": "condition_blinded_full_outcome",
        "run_id": run_id,
        "model": summary["model"],
        "instructions": [
            "Score each response without attempting to infer its generating condition.",
            "Use only the problem, success criteria, and source observations shown.",
            "Penalize unsupported conclusions, missing provenance, and superficial checks.",
            "Choose a preferred response only after scoring both independently.",
        ],
        "review_items": review_items,
    }
    key = {
        "review_type": "condition_key_keep_separate_until_review_complete",
        "run_id": run_id,
        "mapping": answer_key,
    }
    return packet, key


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    output_dir = args.output_dir or args.summary.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    packet, key = build_packet(args.summary)
    _write_json(output_dir / "blind_review_packet.json", packet)
    _write_json(output_dir / "blind_review_condition_key.json", key)
    print(f"Blind review packet created: {len(packet['review_items'])} comparison pairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
