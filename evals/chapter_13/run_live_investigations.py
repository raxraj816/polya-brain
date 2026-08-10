#!/usr/bin/env python3
"""Run three artifact-backed Chapter 13 investigations and direct baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from app.config import get_settings
from app.engines import EngineStatus, ProblemRepresentationEngine, run_engine
from app.graph.state import create_initial_state
from app.llm import (
    LLMCapabilities,
    LLMClient,
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMResponse,
    LLMRole,
    LLMTokenUsage,
    OpenRouterLLMClient,
    complete_with_retry,
)
from app.models.contracts import ProductMode

ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = Path(__file__).resolve().parent

REQUIRED_REPORT_SECTIONS = (
    "Final conclusion",
    "Confidence level",
    "Evidence used",
    "Evidence against",
    "Checks performed",
    "Open questions",
    "Recommended next action",
    "Audit trace",
)


class RecordingLLMClient:
    """Record normalized successful calls without changing adapter behavior."""

    def __init__(self, wrapped: LLMClient) -> None:
        self.wrapped = wrapped
        self.provider: str = wrapped.provider
        self.capabilities: LLMCapabilities = wrapped.capabilities
        self.responses: list[LLMResponse] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        response = self.wrapped.complete(request)
        self.responses.append(response)
        return response


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_artifacts() -> dict[str, float]:
    generated = EVAL_ROOT / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    durations: dict[str, float] = {}

    started = perf_counter()
    pagination = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_pagination_service.py",
            "-q",
        ],
        cwd=EVAL_ROOT / "fixtures" / "pagination",
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    pagination_log = f"exit_code={pagination.returncode}\n\nSTDOUT\n{pagination.stdout}\nSTDERR\n{pagination.stderr}"
    (generated / "pagination_pytest.log").write_text(pagination_log, encoding="utf-8")
    if pagination.returncode == 0:
        raise RuntimeError(
            "pagination fixture unexpectedly passed; the investigation lost its signal"
        )
    durations["pagination_cursor_overlap"] = (perf_counter() - started) * 1000

    started = perf_counter()
    query_metrics = subprocess.run(
        [
            sys.executable,
            str(EVAL_ROOT / "fixtures" / "query_path" / "measure_query_paths.py"),
            "--csv-output",
            str(generated / "query_metrics.csv"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if query_metrics.returncode != 0:
        raise RuntimeError(f"query measurement failed with exit {query_metrics.returncode}")
    (generated / "query_metrics_summary.json").write_text(
        query_metrics.stdout,
        encoding="utf-8",
    )
    durations["n_plus_one_query_path"] = (perf_counter() - started) * 1000

    started = perf_counter()
    policy_probe = subprocess.run(
        [
            sys.executable,
            str(EVAL_ROOT / "fixtures" / "openrouter_privacy" / "probe_openrouter_policy.py"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=45,
    )
    if policy_probe.returncode != 0:
        raise RuntimeError(f"OpenRouter policy probe failed with exit {policy_probe.returncode}")
    (generated / "openrouter_policy_probe.json").write_text(
        policy_probe.stdout,
        encoding="utf-8",
    )
    durations["openrouter_privacy_policy"] = (perf_counter() - started) * 1000
    return durations


def load_cases() -> list[dict[str, Any]]:
    payload = json.loads((EVAL_ROOT / "cases.json").read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Chapter 13 cases must be a JSON list")
    return [item for item in payload if isinstance(item, dict)]


def artifact_bundle(case: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    blocks: list[str] = []
    manifest: list[dict[str, Any]] = []
    for artifact in case["artifacts"]:
        path = (EVAL_ROOT / artifact["path"]).resolve()
        content = path.read_text(encoding="utf-8", errors="replace")
        bounded_content = content[: int(artifact["max_chars"])]
        blocks.append(
            f"ARTIFACT [{artifact['id']}]\nPATH: {path.relative_to(ROOT)}\nCONTENT:\n{bounded_content}"
        )
        manifest.append(
            {
                "id": artifact["id"],
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "included_chars": len(bounded_content),
            }
        )
    return "\n\n".join(blocks), manifest


def aggregate_usage(responses: list[LLMResponse]) -> dict[str, int | float | None]:
    usage = LLMTokenUsage(
        input_tokens=sum(response.usage.input_tokens for response in responses),
        output_tokens=sum(response.usage.output_tokens for response in responses),
        cached_input_tokens=sum(response.usage.cached_input_tokens for response in responses),
        reasoning_tokens=sum(response.usage.reasoning_tokens for response in responses),
        estimated_cost_usd=sum(response.usage.estimated_cost_usd or 0.0 for response in responses),
    )
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "estimated_cost_usd": usage.estimated_cost_usd,
    }


def direct_request(model: str, problem_with_artifacts: str) -> LLMRequest:
    return LLMRequest(
        model=model,
        messages=[
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "Act as a direct technical assistant. Diagnose the supplied problem from "
                    "the artifacts and recommend what to do next. Be concise. Do not imitate "
                    "PolyaBrain's mandatory audit-section format unless it is naturally useful."
                ),
            ),
            LLMMessage(role=LLMRole.USER, content=problem_with_artifacts),
        ],
        options=LLMRequestOptions(
            temperature=0.1,
            max_output_tokens=1400,
            json_mode=False,
            timeout_seconds=120,
            max_retries=2,
            max_retry_delay_seconds=8,
        ),
    )


def polya_report_request(
    model: str,
    *,
    structured_problem_json: str,
    problem_with_artifacts: str,
) -> LLMRequest:
    return LLMRequest(
        model=model,
        messages=[
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "Produce an artifact-grounded PolyaBrain technical investigation report. "
                    "Use only supplied artifacts; cite them as [artifact_id]. Separate evidence "
                    "used from evidence against or uncertainty. Consider at least two hypotheses, "
                    "state checks that were actually performed separately from checks still needed, "
                    "and say insufficient evidence when appropriate. Include exactly these Markdown "
                    "headings: Final conclusion, Confidence level, Evidence used, Evidence against, "
                    "Checks performed, Open questions, Recommended next action, Audit trace. Do not "
                    "invent files, logs, measurements, or completed checks."
                ),
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=(
                    f"VALIDATED STRUCTURED PROBLEM:\n{structured_problem_json}\n\n"
                    f"PROBLEM AND ARTIFACTS:\n{problem_with_artifacts}"
                ),
            ),
        ],
        options=LLMRequestOptions(
            temperature=0.1,
            max_output_tokens=1800,
            json_mode=False,
            timeout_seconds=120,
            max_retries=2,
            max_retry_delay_seconds=8,
        ),
    )


def score_text(case: dict[str, Any], text: str) -> dict[str, Any]:
    lowered = text.casefold()
    term_groups = case["correctness_term_groups"]
    matched_groups = [
        [term for term in group if term.casefold() in lowered] for group in term_groups
    ]
    correctness = sum(bool(matches) for matches in matched_groups) / len(term_groups)
    artifact_ids = [artifact["id"] for artifact in case["artifacts"]]
    cited_artifacts = [
        artifact_id for artifact_id in artifact_ids if artifact_id.casefold() in lowered
    ]
    citation_coverage = len(cited_artifacts) / len(artifact_ids)
    required_sections = [
        section for section in REQUIRED_REPORT_SECTIONS if section.casefold() in lowered
    ]
    completeness = len(required_sections) / len(REQUIRED_REPORT_SECTIONS)
    has_evidence_against = "evidence against" in lowered or "contradict" in lowered
    has_checks = "checks performed" in lowered or "verified" in lowered or "test" in lowered
    has_uncertainty = any(
        term in lowered for term in ["confidence", "uncertain", "insufficient evidence", "unknown"]
    )
    evidence_quality = (
        0.35 * citation_coverage
        + 0.15 * float(has_evidence_against)
        + 0.15 * float(has_checks)
        + 0.1 * float(has_uncertainty)
        + 0.25 * completeness
    )
    actionability = float(
        any(
            term in lowered
            for term in ["recommended next action", "next step", "change", "run", "keep"]
        )
    )
    return {
        "correctness": round(correctness, 3),
        "matched_correctness_terms": matched_groups,
        "evidence_quality": round(evidence_quality, 3),
        "artifact_citation_coverage": round(citation_coverage, 3),
        "cited_artifact_ids": cited_artifacts,
        "required_section_count": len(required_sections),
        "report_completeness": round(completeness, 3),
        "required_sections": required_sections,
        "actionability": actionability,
    }


def add_reuse_proxy(score: dict[str, Any], *, time_to_decision_ms: float) -> dict[str, Any]:
    """Add a neutral content/action/latency proxy without claiming user feedback."""
    utility = (
        0.5 * float(score["correctness"])
        + 0.25 * float(score["evidence_quality"])
        + 0.25 * float(score["actionability"])
    )
    latency_penalty = 0.0
    if time_to_decision_ms > 120_000:
        latency_penalty = 0.2
    elif time_to_decision_ms > 60_000:
        latency_penalty = 0.1
    reuse_score = max(utility - latency_penalty, 0.0)
    return {
        **score,
        "reuse_proxy_score": round(reuse_score, 3),
        "would_use_again_proxy": reuse_score >= 0.7,
        "human_user_feedback_collected": False,
    }


def trace_json(output: Any) -> str:
    events = output.state_delta.get("events", [])
    return "\n".join(event.model_dump_json() for event in events) + "\n"


def run_case(
    case: dict[str, Any],
    *,
    output_root: Path,
    artifact_preparation_ms: float,
) -> dict[str, Any]:
    settings = get_settings()
    base_adapter = OpenRouterLLMClient.from_settings(settings)
    artifact_text, artifact_manifest = artifact_bundle(case)
    problem_with_artifacts = f"{case['problem']}\n\n{artifact_text}"
    case_dir = output_root / case["case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    write_json(case_dir / "artifact_manifest.json", artifact_manifest)

    recording_client = RecordingLLMClient(base_adapter)
    representation_engine = ProblemRepresentationEngine(
        client=recording_client,
        model=settings.openrouter_model,
        mode_hint=ProductMode(case["mode"]),
        domain_hint=case["domain"],
    )
    polya_started = perf_counter()
    representation_output = run_engine(
        representation_engine,
        create_initial_state(problem_with_artifacts, session_id=case["case_id"]),
    )
    if representation_output.result.status is not EngineStatus.OK:
        raise RuntimeError(
            f"representation failed for {case['case_id']}: {representation_output.result.errors}"
        )
    structured_problem = representation_output.state_delta["structured_problem"]
    report_response = complete_with_retry(
        recording_client,
        polya_report_request(
            settings.openrouter_model,
            structured_problem_json=structured_problem.model_dump_json(indent=2),
            problem_with_artifacts=problem_with_artifacts,
        ),
    )
    polya_time_ms = (perf_counter() - polya_started) * 1000

    baseline_client = RecordingLLMClient(OpenRouterLLMClient.from_settings(settings))
    baseline_started = perf_counter()
    baseline_response = complete_with_retry(
        baseline_client,
        direct_request(settings.openrouter_model, problem_with_artifacts),
    )
    baseline_time_ms = (perf_counter() - baseline_started) * 1000

    polya_text = report_response.text.strip() + "\n"
    baseline_text = baseline_response.text.strip() + "\n"
    (case_dir / "polya_report.md").write_text(polya_text, encoding="utf-8")
    (case_dir / "direct_model.md").write_text(baseline_text, encoding="utf-8")
    (case_dir / "representation_trace.jsonl").write_text(
        trace_json(representation_output),
        encoding="utf-8",
    )
    write_json(
        case_dir / "structured_problem.json",
        structured_problem.model_dump(mode="json"),
    )

    polya_score = add_reuse_proxy(
        score_text(case, polya_text),
        time_to_decision_ms=polya_time_ms,
    )
    baseline_score = add_reuse_proxy(
        score_text(case, baseline_text),
        time_to_decision_ms=baseline_time_ms,
    )
    polya_usage = aggregate_usage(recording_client.responses)
    baseline_usage = aggregate_usage(baseline_client.responses)
    metrics = {
        "case_id": case["case_id"],
        "title": case["title"],
        "provider": "openrouter",
        "model": settings.openrouter_model,
        "benchmark_policy_overrides": {
            "data_collection": settings.openrouter_data_collection,
            "require_parameters_for_json": settings.openrouter_require_parameters_for_json,
            "non_confidential_fixtures_only": True,
        },
        "artifact_preparation_ms": round(artifact_preparation_ms, 3),
        "polya": {
            "time_to_decision_ms": round(polya_time_ms, 3),
            "usage": polya_usage,
            "score": polya_score,
        },
        "direct_model": {
            "time_to_decision_ms": round(baseline_time_ms, 3),
            "usage": baseline_usage,
            "score": baseline_score,
        },
        "overhead": {
            "latency_ms": round(polya_time_ms - baseline_time_ms, 3),
            "latency_ratio": round(polya_time_ms / baseline_time_ms, 3),
            "token_count": int(polya_usage["total_tokens"] or 0)
            - int(baseline_usage["total_tokens"] or 0),
            "token_ratio": round(
                int(polya_usage["total_tokens"] or 0)
                / max(int(baseline_usage["total_tokens"] or 0), 1),
                3,
            ),
        },
    }
    write_json(case_dir / "metrics.json", metrics)
    return metrics


def build_summary(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(metrics)

    def average(path: tuple[str, ...]) -> float:
        values: list[float] = []
        for item in metrics:
            current: Any = item
            for key in path:
                current = current[key]
            values.append(float(current))
        return round(sum(values) / len(values), 3)

    return {
        "run_date": date.today().isoformat(),
        "case_count": count,
        "model": metrics[0]["model"] if metrics else None,
        "averages": {
            "polya_time_to_decision_ms": average(("polya", "time_to_decision_ms")),
            "direct_time_to_decision_ms": average(("direct_model", "time_to_decision_ms")),
            "polya_correctness": average(("polya", "score", "correctness")),
            "direct_correctness": average(("direct_model", "score", "correctness")),
            "polya_evidence_quality": average(("polya", "score", "evidence_quality")),
            "direct_evidence_quality": average(("direct_model", "score", "evidence_quality")),
            "latency_ratio": average(("overhead", "latency_ratio")),
            "token_ratio": average(("overhead", "token_ratio")),
        },
        "would_use_again_proxy": {
            "polya_yes": sum(
                bool(item["polya"]["score"]["would_use_again_proxy"]) for item in metrics
            ),
            "direct_yes": sum(
                bool(item["direct_model"]["score"]["would_use_again_proxy"]) for item in metrics
            ),
            "denominator": count,
            "human_user_feedback_collected": False,
        },
        "limitations": [
            "Correctness and reuse are deterministic rubric proxies, not blinded human judgments.",
            "The Polya path contains two model stages (representation plus report); the direct path contains one.",
            "Fixtures are executable and reproducible but are not customer production incidents.",
            "The configured free endpoint required benchmark-only data_collection=allow and best-effort JSON routing.",
        ],
        "cases": metrics,
    }


def rescore_existing(output_root: Path) -> dict[str, Any]:
    """Reapply the deterministic rubric without spending another provider call."""
    rescored: list[dict[str, Any]] = []
    for case in load_cases():
        case_dir = output_root / case["case_id"]
        metrics = json.loads((case_dir / "metrics.json").read_text(encoding="utf-8"))
        polya_text = (case_dir / "polya_report.md").read_text(encoding="utf-8")
        direct_text = (case_dir / "direct_model.md").read_text(encoding="utf-8")
        metrics["polya"]["score"] = add_reuse_proxy(
            score_text(case, polya_text),
            time_to_decision_ms=float(metrics["polya"]["time_to_decision_ms"]),
        )
        metrics["direct_model"]["score"] = add_reuse_proxy(
            score_text(case, direct_text),
            time_to_decision_ms=float(metrics["direct_model"]["time_to_decision_ms"]),
        )
        write_json(case_dir / "metrics.json", metrics)
        rescored.append(metrics)
    summary = build_summary(rescored)
    write_json(output_root / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=EVAL_ROOT / "runs" / date.today().isoformat(),
    )
    parser.add_argument(
        "--rescore-only",
        action="store_true",
        help="Reapply deterministic rubrics to saved outputs without provider calls.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.rescore_only:
        summary = rescore_existing(args.output_root)
        print(json.dumps(summary["averages"], indent=2, sort_keys=True))
        print(f"Rescored Chapter 13 artifacts in {args.output_root}")
        return
    settings = get_settings()
    if not settings.openrouter_model.strip():
        raise RuntimeError("OPENROUTER_MODEL is required")
    if not settings.openrouter_api_key.get_secret_value().strip():
        raise RuntimeError("OPENROUTER_API_KEY is required")
    preparation_durations = prepare_artifacts()
    metrics: list[dict[str, Any]] = []
    for case in load_cases():
        print(f"Starting {case['case_id']}...", flush=True)
        result = run_case(
            case,
            output_root=args.output_root,
            artifact_preparation_ms=preparation_durations[case["case_id"]],
        )
        metrics.append(result)
        print(
            f"Completed {case['case_id']}: "
            f"Polya={result['polya']['time_to_decision_ms']:.0f}ms, "
            f"direct={result['direct_model']['time_to_decision_ms']:.0f}ms",
            flush=True,
        )
    summary = build_summary(metrics)
    write_json(args.output_root / "summary.json", summary)
    print(json.dumps(summary["averages"], indent=2, sort_keys=True))
    print(f"Wrote Chapter 13 live investigation artifacts to {args.output_root}")


if __name__ == "__main__":
    main()
