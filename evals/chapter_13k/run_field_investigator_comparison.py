#!/usr/bin/env python3
"""Live same-model field-derived Investigator comparison for Chapter 13-K."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from evals.chapter_13k.build_blind_review_packet import build_packet
from evals.chapter_13k.contracts import (
    FieldCase,
    FieldConcept,
    FieldConditionScore,
    FieldInvestigationOutput,
    FieldPreflight,
)
from evals.chapter_13k.corpus import (
    FIXTURES_ROOT,
    case_root,
    load_cases,
    polya_problem_input,
    preflight_case,
    visible_evidence_packet,
)

from app.acquisition import (
    LocalArtifactInspector,
    evidence_evaluator_capability,
    local_artifact_capability,
)
from app.cognition import (
    CapabilityRegistry,
    CognitiveController,
    CognitiveModelGateway,
    CognitiveResourceBudget,
    CognitiveRuntime,
    ProcedureCompiler,
    source_patch_investigator_capability,
)
from app.cognition.adapters import (
    constraint_discovery_capability,
    problem_representation_capability,
)
from app.cognition.kernel import CognitiveRunResult
from app.cognition.on_demand_capabilities import on_demand_cognitive_capabilities
from app.config import Settings
from app.engines import ConstraintDiscoveryEngine, ProblemRepresentationEngine
from app.execution import (
    DockerPythonSandbox,
    DockerSandboxLimits,
    source_patch_sandbox_capability,
)
from app.graph.state import PolyaState, create_initial_state
from app.llm import LLMClient, LLMRequest, LLMResponse, OpenRouterLLMClient
from app.llm.errors import LLMClientError
from app.models.contracts import EvidenceItem, StructuredProblem

EVAL_ROOT = Path(__file__).resolve().parent
LIVE_EVAL_OPT_IN = "POLYABRAIN_ALLOW_NONCONFIDENTIAL_FIELD_EVAL"
MAX_POLYA_MODEL_CALLS = 12
MAX_DIRECT_MODEL_CALLS = 3
MAX_OUTPUT_TOKENS = 3000
MAX_CYCLES = 14
_TOKEN = re.compile(r"[a-z0-9_]+")
_SCORER_STOP_TOKENS = {
    "a",
    "an",
    "and",
    "does",
    "for",
    "from",
    "in",
    "instead",
    "is",
    "its",
    "of",
    "on",
    "the",
    "to",
    "with",
}


class RecordingClient:
    """Record normalized usage and enforce an evaluation attempt ceiling."""

    def __init__(self, delegate: LLMClient, *, max_calls: int) -> None:
        self.delegate = delegate
        self.provider = delegate.provider
        self.capabilities = delegate.capabilities
        self.max_calls = max_calls
        self.attempt_count = 0
        self.responses: list[LLMResponse] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        if self.attempt_count >= self.max_calls:
            raise RuntimeError("Chapter 13-K model-call budget exhausted")
        self.attempt_count += 1
        response = self.delegate.complete(request)
        self.responses.append(response)
        return response


def _usage(client: RecordingClient) -> dict[str, int]:
    input_tokens = sum(response.usage.input_tokens for response in client.responses)
    output_tokens = sum(response.usage.output_tokens for response in client.responses)
    return {
        "model_calls": client.attempt_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def _route_telemetry(client: RecordingClient) -> dict[str, Any]:
    """Expose non-content provider identity needed to audit route equivalence."""
    model_counts = Counter(response.model for response in client.responses)
    return {
        "provider": client.provider,
        "actual_model_counts": dict(sorted(model_counts.items())),
        "finish_reason_counts": dict(
            sorted(
                Counter(
                    response.finish_reason or "unreported" for response in client.responses
                ).items()
            )
        ),
    }


def _one_equal_actual_model(
    polya_route: dict[str, Any],
    direct_route: dict[str, Any],
    *,
    polya_attempts: int,
) -> bool:
    """Require observed equality while allowing genuinely model-free Polya."""
    polya_models = set(polya_route["actual_model_counts"])
    direct_models = set(direct_route["actual_model_counts"])
    return bool(
        direct_models
        and (polya_models or polya_attempts == 0)
        and len(polya_models | direct_models) == 1
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _execution_order(case_index: int, repetition: int) -> list[str]:
    return ["direct", "polya"] if (case_index + repetition) % 2 == 0 else ["polya", "direct"]


def _runtime(
    settings: Settings,
    client: RecordingClient,
) -> CognitiveRuntime:
    """Compose the actual kernel with production capabilities used by this gate."""
    model = settings.openrouter_model
    gateway = CognitiveModelGateway(client, model)
    registry = CapabilityRegistry()
    registry.register(
        problem_representation_capability(
            ProblemRepresentationEngine(
                client=client,
                model=model,
                total_timeout_seconds=90,
            )
        )
    )
    registry.register(constraint_discovery_capability(ConstraintDiscoveryEngine()))
    registry.register(
        local_artifact_capability(
            LocalArtifactInspector(
                [FIXTURES_ROOT],
                max_file_bytes=100_000,
                max_candidates=5,
            )
        )
    )
    registry.register(
        evidence_evaluator_capability(
            gateway,
            model_approved_for_sensitive_data=True,
        )
    )
    for capability in on_demand_cognitive_capabilities(
        gateway,
        approved_for_sensitive_data=True,
        max_output_tokens_per_call=MAX_OUTPUT_TOKENS,
        timeout_seconds_per_call=90,
    ):
        registry.register(capability)
    registry.register(
        source_patch_investigator_capability(
            gateway,
            approved_for_sensitive_data=True,
            max_output_tokens=2200,
            timeout_seconds=90,
        )
    )
    registry.register(
        source_patch_sandbox_capability(
            DockerPythonSandbox(
                limits=DockerSandboxLimits(
                    timeout_seconds=5,
                    memory_megabytes=64,
                )
            ),
            [FIXTURES_ROOT],
        )
    )
    return CognitiveRuntime(
        registry,
        controller=CognitiveController(),
        budget=CognitiveResourceBudget(
            max_model_calls=MAX_POLYA_MODEL_CALLS,
            max_external_calls=0,
            max_input_tokens=180_000,
            max_output_tokens=MAX_POLYA_MODEL_CALLS * MAX_OUTPUT_TOKENS,
            max_normalized_cost=8.0,
            max_duration_ms=300_000,
        ),
        procedure_compiler=ProcedureCompiler(),
    )


def _run_polya(
    case: FieldCase,
    preflight: FieldPreflight,
    settings: Settings,
    client: RecordingClient,
) -> tuple[CognitiveRunResult, float]:
    started = perf_counter()
    result = _runtime(settings, client).run_problem(
        polya_problem_input(case, preflight),
        session_id=f"chapter-13k-polya-{case.id}",
        max_cycles=MAX_CYCLES,
    )
    return result, (perf_counter() - started) * 1000


def _direct_state(case: FieldCase, preflight: FieldPreflight) -> PolyaState:
    """Give direct the same visible artifacts as canonical evidence."""
    raw_input = polya_problem_input(case, preflight)
    state = create_initial_state(raw_input, session_id=f"chapter-13k-direct-{case.id}")
    state["structured_problem"] = StructuredProblem(
        core_question=case.problem_statement,
        problem_type="field_derived_technical_investigation",
        domain="software_debugging",
        knowns=["The declared buggy reproduction fails its executable check."],
        unknowns=["The concrete root cause and smallest semantically correct correction."],
        constraints=[
            "Use only supplied visible artifacts.",
            "Do not claim the correction or regression check was executed.",
        ],
        success_criteria=[
            "Identify the concrete failure mechanism.",
            "Name the implicated source artifact or function.",
            "Recommend the smallest semantically correct correction.",
            "Specify an executable regression check.",
        ],
        required_data_sources=["supplied local issue, buggy source, and test artifacts"],
    )
    root = case_root(case)
    state["evidence"] = [
        EvidenceItem(
            source_type=f"field_visible_{artifact.role}",
            source_uri=artifact.resolve(root).as_uri(),
            claim=artifact.resolve(root).read_text(encoding="utf-8"),
            raw_excerpt=artifact.resolve(root).read_text(encoding="utf-8"),
            reliability_score=1.0,
            relevance_score=1.0,
        )
        for artifact in case.visible_artifacts()
    ]
    return state


def _run_direct(
    case: FieldCase,
    preflight: FieldPreflight,
    settings: Settings,
    client: RecordingClient,
) -> tuple[FieldInvestigationOutput, float]:
    gateway = CognitiveModelGateway(client, settings.openrouter_model)
    started = perf_counter()
    result = gateway.complete(
        capability="chapter_13k_direct_field_investigator",
        instructions=(
            "Investigate the executable software defect using only CURRENT_STATE. Return a "
            "diagnosis only if the visible issue, buggy source, test, and failing observation "
            "support it. Identify the exact mechanism and implicated artifact, recommend the "
            "smallest semantic correction, and specify a check that would fail before and pass "
            "after. Cite visible artifact filenames exactly. The fixed implementation and gold "
            "rubric are unavailable. Do not claim to have executed a correction. If evidence is "
            "insufficient, return insufficient_evidence without a guessed cause or correction."
        ),
        output_type=FieldInvestigationOutput,
        state=_direct_state(case, preflight),
        max_output_tokens=MAX_OUTPUT_TOKENS,
        total_timeout_seconds=120,
        context={
            "visible_packet_sha256": hashlib.sha256(
                visible_evidence_packet(case, preflight).encode()
            ).hexdigest()
        },
    )
    return _direct_review_output(result.output), (perf_counter() - started) * 1000


def _direct_review_output(output: FieldInvestigationOutput) -> FieldInvestigationOutput:
    """Keep execution attestation condition-owned, never model-authored."""
    return output.model_copy(update={"execution_attestations": []})


def _polya_review_output(result: CognitiveRunResult) -> FieldInvestigationOutput:
    """Normalize canonical terminal artifacts without scoring rejected ideas."""
    state = result.state
    sources = [
        Path(item.source_uri.split("#", 1)[0].removeprefix("file://")).name
        for item in state["evidence"]
        if item.source_uri and item.source_uri.startswith("file://")
    ]
    verification = state["verification"]
    checks = list(verification.checks_run) if verification is not None else []
    execution_attestations = [
        event.summary
        for event in state["events"]
        if event.event_type == "source_patch_sandbox_completed"
        and event.metadata.get("patch_verified") is True
    ]
    final = state["final_answer"]
    if not final or verification is None or not verification.passed:
        open_items = [gap.description for gap in state["gaps"] if not gap.filled]
        if verification is not None:
            open_items.extend(verification.failed_checks)
        return FieldInvestigationOutput(
            status="insufficient_evidence",
            implicated_artifacts=list(dict.fromkeys(sources)),
            verification_steps=checks,
            evidence_references=list(dict.fromkeys(sources)),
            execution_attestations=execution_attestations,
            remaining_uncertainty=(
                list(dict.fromkeys(open_items))
                or ["The cognitive runtime did not produce a verified field diagnosis."]
            ),
        )
    return FieldInvestigationOutput(
        status="diagnosed",
        root_cause=final,
        implicated_artifacts=list(dict.fromkeys(sources)),
        corrective_action=final,
        verification_steps=checks,
        evidence_references=list(dict.fromkeys(sources)),
        execution_attestations=execution_attestations,
        remaining_uncertainty=list(verification.contradictions),
    )


def _stem(token: str) -> str:
    for suffix in ("ization", "ation", "ments", "ment", "ingly", "edly", "ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _simple_tokens(text: str) -> set[str]:
    return {
        _stem(token)
        for token in _TOKEN.findall(text.casefold())
        if len(token) > 1 and token not in _SCORER_STOP_TOKENS
    }


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw_token in _TOKEN.findall(text):
        compound_parts = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw_token).split()
        variants = [raw_token.casefold()]
        variants.extend(
            part.casefold() for compound_part in compound_parts for part in compound_part.split("_")
        )
        tokens.update(
            _stem(token)
            for token in variants
            if len(token) > 1 and token not in _SCORER_STOP_TOKENS
        )
    return tokens


def _token_support(expected: set[str], observed: set[str]) -> bool:
    if not expected:
        return False
    overlap = expected & observed
    coverage = len(overlap) / len(expected)
    return coverage >= 0.72 or (len(overlap) >= 4 and coverage >= 0.5)


def _phrase_supported(text: str, phrase: str) -> bool:
    return _token_support(_simple_tokens(phrase), _simple_tokens(text)) or _token_support(
        _tokens(phrase), _tokens(text)
    )


def _concepts_pass(text: str, concepts: list[FieldConcept]) -> bool:
    return all(
        any(_phrase_supported(text, phrase) for phrase in concept.any_of) for concept in concepts
    )


def _score_condition(
    case: FieldCase,
    condition: Literal["polya", "direct"],
    output: FieldInvestigationOutput,
    usage: dict[str, int],
    latency_ms: float,
    *,
    executable_verification_passed: bool = False,
) -> FieldConditionScore:
    diagnosis_text = "\n".join(
        part for part in (output.root_cause or "", output.corrective_action or "") if part
    )
    check_text = "\n".join([*output.verification_steps, diagnosis_text])
    references = "\n".join([*output.implicated_artifacts, *output.evidence_references]).casefold()
    visible_names = {artifact.path.casefold() for artifact in case.visible_artifacts()}
    evidence_passed = any(name in references for name in visible_names)
    forbidden_hits = [
        term for term in case.forbidden_conclusions if term.casefold() in diagnosis_text.casefold()
    ]
    mechanism_passed = _concepts_pass(diagnosis_text, case.required_mechanism_concepts)
    correction_passed = _concepts_pass(diagnosis_text, case.required_correction_concepts)
    # Present-case execution of the admitted immutable regression check is
    # stronger evidence of check adequacy than lexical paraphrase matching. The
    # flag is derived by the harness from a criterion-bound sandbox event; model
    # prose alone can never set it. All diagnosis and evidence gates remain
    # independently conjunctive below.
    check_passed = executable_verification_passed or _concepts_pass(
        check_text, case.required_check_concepts
    )
    unsupported = output.status == "diagnosed" and not evidence_passed
    passed = bool(
        output.status == "diagnosed"
        and mechanism_passed
        and correction_passed
        and check_passed
        and evidence_passed
        and not forbidden_hits
        and not unsupported
    )
    return FieldConditionScore(
        condition=condition,
        mechanism_concepts_passed=mechanism_passed,
        correction_concepts_passed=correction_passed,
        check_concepts_passed=check_passed,
        evidence_reference_passed=evidence_passed,
        executable_verification_passed=executable_verification_passed,
        forbidden_conclusion_hits=forbidden_hits,
        unsupported_forced_conclusion=unsupported,
        passed=passed,
        model_calls=usage["model_calls"],
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        latency_ms=latency_ms,
    )


def _state_artifact(result: CognitiveRunResult) -> dict[str, Any]:
    state = result.state
    return {
        "status": result.status.value,
        "structured_problem": (
            state["structured_problem"].model_dump(mode="json")
            if state["structured_problem"] is not None
            else None
        ),
        "gaps": [item.model_dump(mode="json") for item in state["gaps"]],
        "evidence": [item.model_dump(mode="json") for item in state["evidence"]],
        "hypotheses": [item.model_dump(mode="json") for item in state["hypotheses"]],
        "plan": [item.model_dump(mode="json") for item in state["plan"]],
        "execution_outputs": [item.model_dump(mode="json") for item in state["execution_outputs"]],
        "verification": (
            state["verification"].model_dump(mode="json")
            if state["verification"] is not None
            else None
        ),
        "reflection": (
            state["reflection"].model_dump(mode="json") if state["reflection"] is not None else None
        ),
        "final_answer": state["final_answer"],
        "events": [item.model_dump(mode="json") for item in state["events"]],
        "decisions": [item.model_dump(mode="json") for item in result.decisions],
        "observations": [item.model_dump(mode="json") for item in result.observations],
    }


def _aggregate(results: list[dict[str, Any]], condition: str) -> dict[str, Any]:
    scores = [item[condition]["score"] for item in results]
    count = len(scores)
    return {
        "passed": sum(bool(score["passed"]) for score in scores),
        "pass_rate": sum(bool(score["passed"]) for score in scores) / count,
        "mechanism_accuracy": sum(bool(score["mechanism_concepts_passed"]) for score in scores)
        / count,
        "correction_accuracy": sum(bool(score["correction_concepts_passed"]) for score in scores)
        / count,
        "check_accuracy": sum(bool(score["check_concepts_passed"]) for score in scores) / count,
        "executable_verification_rate": sum(
            bool(score["executable_verification_passed"]) for score in scores
        )
        / count,
        "unsupported_forced_conclusions": sum(
            bool(score["unsupported_forced_conclusion"]) for score in scores
        ),
        "forbidden_conclusion_hits": sum(
            len(score["forbidden_conclusion_hits"]) for score in scores
        ),
        "model_calls": sum(int(score["model_calls"]) for score in scores),
        "input_tokens": sum(int(score["input_tokens"]) for score in scores),
        "output_tokens": sum(int(score["output_tokens"]) for score in scores),
        "total_tokens": sum(
            int(score["input_tokens"]) + int(score["output_tokens"]) for score in scores
        ),
        "mean_latency_ms": sum(float(score["latency_ms"]) for score in scores) / count,
    }


def _automated_gate(
    results: list[dict[str, Any]],
    case_count: int,
    repetitions: int,
) -> dict[str, Any]:
    polya = _aggregate(results, "polya")
    direct = _aggregate(results, "direct")
    token_ratio = polya["total_tokens"] / direct["total_tokens"] if direct["total_tokens"] else 0.0
    quality_advantage = polya["pass_rate"] - direct["pass_rate"]
    executable_verification_advantage = bool(
        polya["pass_rate"] == 1.0
        and polya["executable_verification_rate"] == 1.0
        and direct["executable_verification_rate"] == 0.0
        and polya["model_calls"] <= direct["model_calls"]
    )
    quality_cost_win = (
        quality_advantage >= 0.10
        or (polya["pass_rate"] >= direct["pass_rate"] and token_ratio <= 0.80)
        or executable_verification_advantage
    )
    requirements = {
        "minimum_three_repetitions": repetitions >= 3,
        "all_pairs_completed": len(results) == case_count * repetitions,
        "all_preflights_eligible": all(bool(item["preflight"]["eligible"]) for item in results),
        "all_pairs_used_one_equal_actual_model": all(
            bool(item["route_equivalence"]["one_equal_actual_model"]) for item in results
        ),
        "all_polya_cases_passed": polya["passed"] == len(results),
        "all_polya_patches_executably_verified": (polya["executable_verification_rate"] == 1.0),
        "zero_polya_unsupported_forced_conclusions": polya["unsupported_forced_conclusions"] == 0,
        "zero_polya_forbidden_conclusion_hits": polya["forbidden_conclusion_hits"] == 0,
        "quality_cost_frontier_win": quality_cost_win,
    }
    return {
        "passed": all(requirements.values()),
        "requirements": requirements,
        "metrics": {
            "polya": polya,
            "direct": direct,
            "pass_rate_advantage": quality_advantage,
            "token_ratio": token_ratio,
            "executable_verification_advantage": executable_verification_advantage,
        },
        "human_review_status": "pending",
        "fresh_private_field_cases_status": "pending",
        "product_value_claim_ready": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 10:
        raise ValueError("repetitions must be between 1 and 10")
    if os.environ.get(LIVE_EVAL_OPT_IN) != "1":
        raise RuntimeError(
            f"Set {LIVE_EVAL_OPT_IN}=1 only for the public, non-confidential field corpus."
        )

    settings = Settings()
    if not settings.openrouter_api_key.get_secret_value().strip() or not settings.openrouter_model:
        raise RuntimeError("A configured OpenRouter key and model are required")
    cases = load_cases()
    if args.case_id:
        requested = set(args.case_id)
        cases = [case for case in cases if case.id in requested]
        missing = requested - {case.id for case in cases}
        if missing:
            raise ValueError(f"unknown case ids: {', '.join(sorted(missing))}")
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise ValueError("at least one Chapter 13-K case is required")

    started_at = datetime.now(UTC)
    model_fingerprint = hashlib.sha256(settings.openrouter_model.encode()).hexdigest()[:8]
    run_id = f"{started_at.strftime('%H%M%S')}-{model_fingerprint}"
    run_root = EVAL_ROOT / "live_runs" / started_at.date().isoformat() / run_id
    results: list[dict[str, Any]] = []

    for repetition in range(1, args.repetitions + 1):
        for case_index, case in enumerate(cases):
            preflight = preflight_case(case)
            if not preflight.eligible:
                continue
            order = _execution_order(case_index, repetition)
            polya_client = RecordingClient(
                OpenRouterLLMClient.from_settings(settings),
                max_calls=MAX_POLYA_MODEL_CALLS,
            )
            direct_client = RecordingClient(
                OpenRouterLLMClient.from_settings(settings),
                max_calls=MAX_DIRECT_MODEL_CALLS,
            )
            try:
                if order[0] == "direct":
                    direct_output, direct_latency = _run_direct(
                        case, preflight, settings, direct_client
                    )
                polya_result, polya_latency = _run_polya(case, preflight, settings, polya_client)
                if order[0] == "polya":
                    direct_output, direct_latency = _run_direct(
                        case, preflight, settings, direct_client
                    )
            except (LLMClientError, RuntimeError) as exc:
                blocked = {
                    "status": "provider_or_budget_blocked",
                    "run_id": run_id,
                    "model": settings.openrouter_model,
                    "failed_case": case.id,
                    "failed_repetition": repetition,
                    "failure_type": type(exc).__name__,
                    "message": str(exc),
                    "completed_pairs": len(results),
                }
                _write_json(run_root / "blocked.json", blocked)
                print(json.dumps(blocked, indent=2, sort_keys=True))
                return 2

            failed_conditions = [
                condition
                for condition, condition_client in (
                    ("polya", polya_client),
                    ("direct", direct_client),
                )
                if condition_client.attempt_count > 0 and not condition_client.responses
            ]
            if failed_conditions:
                blocked = {
                    "status": "provider_or_budget_blocked",
                    "run_id": run_id,
                    "model": settings.openrouter_model,
                    "failed_case": case.id,
                    "failed_repetition": repetition,
                    "failed_conditions": failed_conditions,
                    "failure_type": "NoSuccessfulProviderResponse",
                    "message": (
                        "At least one condition attempted the configured provider but "
                        "received no successful model response. The pair is invalid for "
                        "cognitive-quality comparison."
                    ),
                    "attempts": {
                        "polya": polya_client.attempt_count,
                        "direct": direct_client.attempt_count,
                    },
                    "completed_pairs": len(results),
                    "polya_runtime": _state_artifact(polya_result),
                }
                _write_json(run_root / "blocked.json", blocked)
                print(json.dumps(blocked, indent=2, sort_keys=True))
                return 2

            polya_output = _polya_review_output(polya_result)
            polya_usage = _usage(polya_client)
            direct_usage = _usage(direct_client)
            polya_score = _score_condition(
                case,
                "polya",
                polya_output,
                polya_usage,
                polya_latency,
                executable_verification_passed=bool(polya_output.execution_attestations),
            )
            direct_score = _score_condition(
                case,
                "direct",
                direct_output,
                direct_usage,
                direct_latency,
            )
            polya_route = _route_telemetry(polya_client)
            direct_route = _route_telemetry(direct_client)
            item = {
                "case_id": case.id,
                "family": case.family,
                "pair_position": case.pair_position,
                "project": case.project,
                "public_historical_case": case.public_historical_case,
                "reduced_reproduction": case.reduced_reproduction,
                "upstream_repository": str(case.upstream_repository),
                "bugsinpy_metadata": str(case.bugsinpy_metadata),
                "buggy_commit": case.buggy_commit,
                "fixed_commit": case.fixed_commit,
                "repetition": repetition,
                "execution_order": order,
                "route_equivalence": {
                    "configured_route": settings.openrouter_model,
                    "polya": polya_route,
                    "direct": direct_route,
                    "one_equal_actual_model": _one_equal_actual_model(
                        polya_route,
                        direct_route,
                        polya_attempts=polya_client.attempt_count,
                    ),
                },
                "preflight": preflight.model_dump(mode="json"),
                "polya": {
                    "output": polya_output.model_dump(mode="json"),
                    "score": polya_score.model_dump(mode="json"),
                    "usage": polya_usage,
                    "runtime": _state_artifact(polya_result),
                },
                "direct": {
                    "output": direct_output.model_dump(mode="json"),
                    "score": direct_score.model_dump(mode="json"),
                    "usage": direct_usage,
                },
            }
            results.append(item)
            _write_json(
                run_root / f"repetition-{repetition}" / case.id / "result.json",
                item,
            )
            print(
                f"rep={repetition} case={case.id} "
                f"polya={polya_score.passed} direct={direct_score.passed} "
                f"calls={polya_usage['model_calls']}/{direct_usage['model_calls']}"
            )

    gate = _automated_gate(results, len(cases), args.repetitions)
    summary = {
        "status": "completed",
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "model": settings.openrouter_model,
        "configured_model_route": settings.openrouter_model,
        "case_count": len(cases),
        "repetitions": args.repetitions,
        "pair_count": len(results),
        "automated_gate": gate,
        "claim_boundary": (
            "Field-derived reduced public historical reproductions; potential model-training "
            "contamination; no full-project, fresh-field, human-review, cross-domain, or "
            "general-intelligence claim."
        ),
        "results": results,
    }
    _write_json(run_root / "summary.json", summary)
    packet, key = build_packet(run_root / "summary.json")
    _write_json(run_root / "blind_review_packet.json", packet)
    _write_json(run_root / "blind_review_condition_key.json", key)
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key != "results"},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
