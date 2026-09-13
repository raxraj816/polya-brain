#!/usr/bin/env python3
"""Build condition-blinded review artifacts for a Chapter 13-K live run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from evals.chapter_13k.contracts import FieldCase, FieldPreflight
from evals.chapter_13k.corpus import case_root, load_cases, visible_evidence_packet

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _opaque_id(*parts: object, prefix: str) -> str:
    digest = hashlib.sha256(
        "|".join(str(part) for part in (*parts, "chapter-13k-blind-v1")).encode()
    ).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _sanitize_text(text: str, case: FieldCase) -> str:
    root = case_root(case)
    replacements = (
        (root.as_uri(), "artifact://case"),
        (str(root), "<case-artifacts>"),
        (REPOSITORY_ROOT.as_uri(), "artifact://workspace"),
        (str(REPOSITORY_ROOT), "<workspace>"),
    )
    sanitized = text
    for original, replacement in replacements:
        sanitized = sanitized.replace(original, replacement)
    return sanitized


def _sanitize_value(value: Any, case: FieldCase) -> Any:
    if isinstance(value, str):
        return _sanitize_text(value, case)
    if isinstance(value, list):
        return [_sanitize_value(item, case) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(item, case) for key, item in value.items()}
    return value


def _review_response(
    output: dict[str, Any],
    response_id: str,
    case: FieldCase,
) -> dict[str, Any]:
    response = {
        "response_id": response_id,
        "status": output.get("status"),
        "root_cause": output.get("root_cause"),
        "implicated_artifacts": output.get("implicated_artifacts", []),
        "corrective_action": output.get("corrective_action"),
        "verification_steps": output.get("verification_steps", []),
        "evidence_references": output.get("evidence_references", []),
        "execution_attestations": output.get("execution_attestations", []),
        "remaining_uncertainty": output.get("remaining_uncertainty", []),
    }
    return cast(dict[str, Any], _sanitize_value(response, case))


def _review_evidence(case: FieldCase, preflight: FieldPreflight) -> str:
    """Keep evidence intact while removing local paths and descriptive case ids."""
    packet = visible_evidence_packet(case, preflight)
    return _sanitize_text(packet, case)


def build_packet(summary_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a reviewer packet and separately stored condition/rubric key."""
    summary = _read_json(summary_path)
    if not isinstance(summary, dict) or summary.get("status") != "completed":
        raise ValueError("blind review requires a completed Chapter 13-K summary")
    raw_results = summary.get("results")
    if not isinstance(raw_results, list) or not raw_results:
        raise ValueError("completed summary contains no Chapter 13-K comparison pairs")

    run_id = str(summary["run_id"])
    cases = {case.id: case for case in load_cases()}
    review_items: list[dict[str, Any]] = []
    key_mapping: dict[str, dict[str, Any]] = {}
    for result in raw_results:
        if not isinstance(result, dict):
            raise ValueError("comparison result must be an object")
        case_id = str(result["case_id"])
        repetition = int(result["repetition"])
        case: FieldCase = cases[case_id]
        preflight = FieldPreflight.model_validate(result["preflight"])
        pair_id = _opaque_id(run_id, case_id, repetition, prefix="case")
        responses: list[dict[str, Any]] = []
        for condition in ("polya", "direct"):
            condition_result = result[condition]
            response_id = _opaque_id(
                run_id,
                case_id,
                repetition,
                condition,
                prefix="response",
            )
            responses.append(_review_response(condition_result["output"], response_id, case))
            key_mapping[response_id] = {
                "condition": condition,
                "case_id": case_id,
                "repetition": repetition,
                "automated_score": condition_result["score"],
            }
        responses.sort(key=lambda item: str(item["response_id"]))
        review_items.append(
            {
                "pair_id": pair_id,
                "problem_and_visible_evidence": _review_evidence(case, preflight),
                "responses": responses,
                "review_form": {
                    response["response_id"]: {
                        "diagnosis_correctness_1_to_5": None,
                        "evidence_grounding_1_to_5": None,
                        "correction_quality_1_to_5": None,
                        "regression_check_quality_1_to_5": None,
                        "uncertainty_discipline_1_to_5": None,
                        "practical_usefulness_1_to_5": None,
                        "unsupported_or_fabricated_claim": None,
                        "notes": "",
                    }
                    for response in responses
                },
                "preferred_response_id": None,
                "preference_confidence_1_to_5": None,
            }
        )

    review_items.sort(key=lambda item: str(item["pair_id"]))
    packet = {
        "review_type": "blinded_field_derived_technical_investigation",
        "run_id": run_id,
        "instructions": [
            "Score each response independently before choosing a preference.",
            "Use only the visible problem, source, test, and failing observation shown.",
            "Reward the concrete failure mechanism, smallest semantic correction, and an executable regression check.",
            "Penalize unsupported execution claims, invented evidence, vague fixes, and unjustified certainty.",
            "Do not try to infer which system generated a response.",
        ],
        "review_items": review_items,
    }
    key = {
        "review_type": "condition_and_hidden_rubric_key_keep_separate",
        "run_id": run_id,
        "mapping": key_mapping,
        "hidden_case_rubrics": {
            case.id: {
                "required_mechanism_concepts": [
                    concept.model_dump(mode="json") for concept in case.required_mechanism_concepts
                ],
                "required_correction_concepts": [
                    concept.model_dump(mode="json") for concept in case.required_correction_concepts
                ],
                "required_check_concepts": [
                    concept.model_dump(mode="json") for concept in case.required_check_concepts
                ],
                "forbidden_conclusions": case.forbidden_conclusions,
            }
            for case in cases.values()
        },
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
