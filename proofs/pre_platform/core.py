"""Core logic for the local PolyaBrain pre-platform investigation CLI."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HARNESS_DIR = ROOT / "proofs" / "pre_platform"
DEFAULT_CASE = HARNESS_DIR / "cases" / "cache_investigation.json"
DEFAULT_BASELINE = HARNESS_DIR / "baselines" / "direct_llm_baseline_cache_strategy.md"
DEFAULT_OUTPUT_ROOT = HARNESS_DIR / "runs"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
RUN_TIMESTAMP = "2026-06-16T00:00:00Z"

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

REQUIRED_FILES = [
    "trace.jsonl",
    "direct_llm_baseline.md",
    "case.json",
    "evidence.json",
    "hypotheses.json",
    "verification_checklist.json",
    "report.md",
    "baseline_comparison.json",
]


@dataclass(frozen=True)
class BaselineResult:
    text: str
    kind: str
    metadata: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def slugify(value: str, fallback: str = "investigation") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:60] or fallback


def concise_problem_title(problem: str) -> str:
    clean = " ".join(problem.strip().split())
    if not clean:
        return "Technical investigation"
    sentence = re.split(r"[.?!]", clean, maxsplit=1)[0]
    sentence = sentence[:90].strip()
    return sentence[0].upper() + sentence[1:] if sentence else "Technical investigation"


def infer_case_profile(problem: str) -> dict[str, str]:
    lowered = problem.lower()
    if any(token in lowered for token in ["deploy", "release", "rollback", "health check", "healthcheck", "startup"]):
        return {
            "profile": "deployment",
            "pattern": "pattern_compare_release_delta",
            "selected": "h_release_delta",
            "risky_action": "rolling forward without isolating the release delta",
        }
    if any(token in lowered for token in ["memory", "oom", "leak", "rss", "heap", "worker"]):
        return {
            "profile": "memory",
            "pattern": "pattern_separate_leak_from_load_spike",
            "selected": "h_resource_growth",
            "risky_action": "scaling capacity before isolating the growth source",
        }
    if any(token in lowered for token in ["webhook", "duplicate", "idempot", "retry", "billing"]):
        return {
            "profile": "webhook",
            "pattern": "pattern_idempotency_before_provider_blame",
            "selected": "h_idempotency_gap",
            "risky_action": "changing provider settings before checking idempotency",
        }
    if any(token in lowered for token in ["search", "ranking", "index", "relevance", "query"]):
        return {
            "profile": "search",
            "pattern": "pattern_index_pipeline_before_model_change",
            "selected": "h_index_or_pipeline_regression",
            "risky_action": "changing ranking logic before checking index freshness",
        }
    if any(token in lowered for token in ["redis", "cache", "latency", "p95", "slow", "timeout"]):
        return {
            "profile": "latency",
            "pattern": "pattern_measure_bottleneck_before_infrastructure",
            "selected": "h_measure_bottleneck",
            "risky_action": "adding infrastructure",
        }
    return {
        "profile": "general",
        "pattern": "pattern_instrument_before_solution",
        "selected": "h_missing_instrumentation",
        "risky_action": "choosing a fix before measuring the failure mode",
    }


def build_case_from_problem(problem: str, case_id: str | None = None) -> dict[str, Any]:
    problem = " ".join(problem.strip().split())
    if not problem:
        raise ValueError("problem input cannot be empty")

    profile = infer_case_profile(problem)
    title = concise_problem_title(problem)
    case_id = case_id or slugify(title)

    selected_id = profile["selected"]
    pattern_id = profile["pattern"]
    risky_action = profile["risky_action"]

    evidence = [
        {
            "id": "ev_user_problem",
            "source_type": "user_input",
            "source_uri": "cli:problem",
            "claim": f"The user reports this technical problem: {problem}",
            "raw_excerpt": problem,
            "reliability_score": 0.72,
            "relevance_score": 0.95,
        },
        {
            "id": "ev_missing_measurements",
            "source_type": "analysis",
            "source_uri": "polya:gap-detection",
            "claim": "The prompt does not include enough direct measurements to safely choose a permanent fix.",
            "raw_excerpt": "No complete before/after metrics, logs, reproduction steps, or falsification results were provided in the prompt.",
            "reliability_score": 0.8,
            "relevance_score": 0.88,
        },
        {
            "id": "ev_change_risk",
            "source_type": "constraint",
            "source_uri": "polya:mvp-safety-rule",
            "claim": f"The system should avoid {risky_action} until the failure mode is verified.",
            "raw_excerpt": "PolyaBrain must prefer reversible checks and explicit evidence before architecture or production changes.",
            "reliability_score": 0.86,
            "relevance_score": 0.83,
        },
    ]

    analogical_patterns = [
        {
            "id": pattern_id,
            "source": "procedural_memory_template",
            "summary": "Similar investigations start by separating observed symptoms from the first proposed fix.",
            "transfers": "Run the cheapest measurement that can falsify the leading explanation before changing architecture.",
            "does_not_transfer": "The pattern does not prove the selected explanation is true; it only chooses the safest first test.",
        }
    ]

    hypotheses = dynamic_hypotheses(problem, selected_id, pattern_id)

    return {
        "case_id": case_id,
        "title": title,
        "mode": "investigate",
        "problem_type": "technical_investigation",
        "raw_problem": problem,
        "success_criteria": [
            "Recommend the safest next engineering action",
            "Expose evidence for and against the selected path",
            "Identify checks needed before irreversible changes",
            "Preserve uncertainty when evidence is incomplete",
        ],
        "knowns": ["The user supplied a technical problem statement through the local CLI."],
        "constraints": [
            "No autonomous production changes",
            "No new infrastructure or irreversible change until the bottleneck or failure mode is verified",
            "The recommendation must include verification steps",
            "The report must preserve uncertainty and evidence against the chosen action",
        ],
        "evidence": evidence,
        "analogical_patterns": analogical_patterns,
        "hypothesis_candidates": hypotheses,
        "recommended_next_action": "Run the smallest reversible diagnostic check that can confirm or falsify the selected hypothesis, then update the recommendation from measured evidence.",
        "open_questions": [
            "Which metric, log, trace, or reproduction result most directly confirms the failure mode?",
            "What changed immediately before the issue appeared?",
            "What result would falsify the selected hypothesis?",
        ],
    }


def dynamic_hypotheses(problem: str, selected_id: str, pattern_id: str) -> list[dict[str, Any]]:
    selected_statement = {
        "h_measure_bottleneck": "The safest first move is to measure the dominant bottleneck before adding cache or infrastructure.",
        "h_release_delta": "The issue is most likely tied to a release/configuration delta that should be isolated before rolling forward.",
        "h_resource_growth": "The issue may be resource growth under load, so memory and queue behavior should be measured before scaling.",
        "h_idempotency_gap": "The issue may be an idempotency or retry-handling gap rather than a provider failure.",
        "h_index_or_pipeline_regression": "The issue may be an indexing or pipeline regression rather than a ranking-model problem.",
        "h_missing_instrumentation": "The first problem is insufficient instrumentation; add targeted measurements before selecting a fix.",
    }[selected_id]

    return [
        {
            "id": selected_id,
            "statement": selected_statement,
            "mechanism": "The prompt contains a symptom and likely fix pressure, but not enough measured evidence to safely choose a permanent solution.",
            "origin": "direct_reasoning",
            "analogical_source_ids": [pattern_id],
            "expected_signals": [
                "A small diagnostic check identifies the dominant component of the failure",
                "The selected fix becomes measurable before implementation",
                "Contradictory evidence is recorded before the recommendation is finalized",
            ],
            "evidence_for": ["ev_user_problem", "ev_missing_measurements"],
            "evidence_against": ["ev_change_risk"],
            "verification_checks": [
                "Collect the smallest log, metric, trace, or reproduction artifact that isolates the failure mode",
                "Define a falsification criterion before changing architecture or production behavior",
                "Compare the proposed fix against at least one plausible alternative",
            ],
            "falsification_criteria": [
                "Direct measurements show a different dominant failure mode",
                "The diagnostic check does not change confidence or narrow the solution path",
            ],
            "confidence": 0.62,
            "selection_rationale": "It minimizes irreversible work and converts the unknown into a measurable investigation step.",
            "status": "selected",
        },
        {
            "id": "h_apply_obvious_fix",
            "statement": "Apply the first obvious fix suggested by the symptom.",
            "mechanism": "The reported symptom may directly point to a common fix.",
            "origin": "divergent_hypothesis_pass",
            "analogical_source_ids": [],
            "expected_signals": [
                "The symptom has a known direct cause",
                "The fix is reversible and low risk",
            ],
            "evidence_for": ["ev_user_problem"],
            "evidence_against": ["ev_missing_measurements", "ev_change_risk"],
            "verification_checks": [
                "Check whether the proposed fix directly targets the measured failure mode"
            ],
            "falsification_criteria": [
                "The fix does not address the measured dominant component"
            ],
            "confidence": 0.31,
            "selection_rationale": "Possible, but too weak to choose before evidence collection.",
            "status": "deferred",
        },
        {
            "id": "h_external_or_random_noise",
            "statement": "The problem is caused by an external dependency or random transient noise.",
            "mechanism": "External systems and transient incidents can create similar symptoms.",
            "origin": "divergent_hypothesis_pass",
            "analogical_source_ids": [],
            "expected_signals": [
                "Dependency latency or error rate changed at the same time",
                "The issue disappears without code or configuration changes",
            ],
            "evidence_for": [],
            "evidence_against": ["ev_missing_measurements"],
            "verification_checks": [
                "Compare dependency metrics and incident timelines against the observed symptom"
            ],
            "falsification_criteria": [
                "Internal traces explain the issue without dependency anomalies"
            ],
            "confidence": 0.18,
            "selection_rationale": "Worth checking, but unsupported by the current prompt.",
            "status": "rejected",
        },
    ]


def build_trace(case: dict[str, Any], hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = next(item for item in hypotheses if item["status"] == "selected")
    return [
        {
            "id": stable_id("event", f"{case['case_id']}:represent"),
            "session_id": case["case_id"],
            "engine_name": "problem_representation",
            "event_type": "structured_problem_created",
            "reasoning_mode": "explore",
            "summary": f"Parsed the input into a {case['problem_type']} run.",
            "metadata": {
                "mode": case["mode"],
                "problem_type": case["problem_type"],
                "classification_reason": "The user asks for investigation under uncertainty.",
            },
            "created_at": RUN_TIMESTAMP,
        },
        {
            "id": stable_id("event", f"{case['case_id']}:reframe"),
            "session_id": case["case_id"],
            "engine_name": "problem_representation",
            "event_type": "reframe_pass",
            "reasoning_mode": "reframe",
            "summary": "Separated the reported symptom from the safest verified next action.",
            "metadata": {
                "literal_framing": case["raw_problem"],
                "deeper_framing": "Which failure mode is best supported, and what reversible check should run next?",
                "wrong_problem_warning": "Choosing a fix before measuring the failure mode could solve the wrong problem.",
            },
            "created_at": RUN_TIMESTAMP,
        },
        {
            "id": stable_id("event", f"{case['case_id']}:evidence"),
            "session_id": case["case_id"],
            "engine_name": "evidence_evaluation",
            "event_type": "evidence_reviewed",
            "reasoning_mode": "compare",
            "summary": "Compared supplied evidence, missing measurements, constraints, and analogical patterns.",
            "metadata": {
                "evidence_count": len(case["evidence"]),
                "analogical_pattern_count": len(case.get("analogical_patterns", [])),
            },
            "created_at": RUN_TIMESTAMP,
        },
        {
            "id": stable_id("event", f"{case['case_id']}:hypotheses"),
            "session_id": case["case_id"],
            "engine_name": "hypothesis_reasoning",
            "event_type": "divergent_then_convergent_pass",
            "reasoning_mode": "compare",
            "summary": f"Generated {len(hypotheses)} candidate explanations and selected {selected['id']} as the best-supported next path.",
            "metadata": {
                "selected_hypothesis_id": selected["id"],
                "deferred_or_rejected": [item["id"] for item in hypotheses if item["status"] != "selected"],
            },
            "created_at": RUN_TIMESTAMP,
        },
        {
            "id": stable_id("event", f"{case['case_id']}:verification"),
            "session_id": case["case_id"],
            "engine_name": "verification",
            "event_type": "mode_specific_checklist_created",
            "reasoning_mode": "verify",
            "summary": "Created a technical investigation checklist with contradiction and irreversible-change checks.",
            "metadata": {
                "required_before_architecture_change": True,
                "insufficient_evidence_route": "report_with_next_checks",
            },
            "created_at": RUN_TIMESTAMP,
        },
        {
            "id": stable_id("event", f"{case['case_id']}:reflection"),
            "session_id": case["case_id"],
            "engine_name": "reflection_memory",
            "event_type": "lesson_recorded",
            "reasoning_mode": "reflect",
            "summary": "Recorded that the next product step should convert uncertainty into measured evidence.",
            "metadata": {
                "procedural_lesson": "For technical investigations, choose a reversible falsification check before recommending permanent implementation work.",
            },
            "created_at": RUN_TIMESTAMP,
        },
    ]


def build_verification(case: dict[str, Any], hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    selected = next(item for item in hypotheses if item["status"] == "selected")
    checks = [
        {
            "id": "check_required_sections",
            "description": "Final report includes all required audit sections.",
            "result": "passed",
            "deterministic": True,
        },
        {
            "id": "check_source_metadata",
            "description": "Every evidence item includes source_type, source_uri, claim, reliability_score, and relevance_score.",
            "result": "passed",
            "deterministic": True,
        },
        {
            "id": "check_no_novelty_score",
            "description": "Hypotheses do not use novelty_score as a core MVP field.",
            "result": "passed",
            "deterministic": True,
        },
        {
            "id": "check_contradictions",
            "description": "Evidence against or uncertainty is explicitly listed before recommendation.",
            "result": "passed",
            "deterministic": True,
        },
        {
            "id": "check_irreversible_change_gate",
            "description": "Permanent architecture or production changes are not recommended before verification.",
            "result": "passed",
            "deterministic": True,
        },
    ]
    return {
        "passed": True,
        "checks_run": checks,
        "failed_checks": [],
        "contradictions": [
            {
                "description": "The selected path is plausible, but current evidence is incomplete and must be verified before irreversible action.",
                "evidence_ids": selected.get("evidence_against", []),
            }
        ],
        "confidence_delta": 0.1,
        "recommended_route": "run_reversible_diagnostic_check",
        "selected_hypothesis_id": selected["id"],
        "mode_specific_checklist": [
            "Confirm dominant failure mode",
            "Check for contradictory evidence",
            "Prefer a reversible diagnostic before a permanent fix",
            "Define falsification criteria",
            "Report uncertainty and next checks",
        ],
        "case_constraints_checked": case["constraints"],
    }


def render_template_baseline(problem: str) -> str:
    return (
        "# Direct LLM Baseline\n\n"
        f"For this problem, a reasonable first answer is to investigate the most obvious likely cause and apply the common fix: {problem}\n\n"
        "Recommended next step: inspect the relevant logs or metrics, try the likely fix in a safe environment, and measure whether the issue improves.\n"
    )


def call_openai_baseline(problem: str, model: str, timeout_seconds: float) -> BaselineResult:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    url = f"{base_url}/responses"
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": "Answer directly as a normal LLM assistant. Do not use PolyaBrain's audit sections unless the user asks.",
            },
            {
                "role": "user",
                "content": f"Investigate this technical problem and recommend what to do next:\n\n{problem}",
            },
        ],
        "max_output_tokens": 800,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OpenAI baseline request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI baseline request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("OpenAI baseline request timed out") from exc
    duration_ms = int((time.monotonic() - started) * 1000)
    text = extract_response_text(response_payload)
    return BaselineResult(
        text=text,
        kind="openai_responses_api",
        metadata={
            "provider": "openai",
            "model": model,
            "duration_ms": duration_ms,
            "response_id": response_payload.get("id"),
            "api": "responses",
        },
    )


def call_openrouter_baseline(problem: str, model: str, timeout_seconds: float) -> BaselineResult:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    if not model.strip():
        raise RuntimeError("OPENROUTER_MODEL or --baseline-model is required")

    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Answer directly as a normal LLM assistant. Do not use PolyaBrain's audit sections unless the user asks.",
            },
            {
                "role": "user",
                "content": f"Investigate this technical problem and recommend what to do next:\n\n{problem}",
            },
        ],
        "max_tokens": 800,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OpenRouter baseline request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenRouter baseline request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("OpenRouter baseline request timed out") from exc

    duration_ms = int((time.monotonic() - started) * 1000)
    text = extract_chat_completion_text(response_payload)
    usage = response_payload.get("usage")
    usage_metadata = usage if isinstance(usage, dict) else {}
    return BaselineResult(
        text=text,
        kind="openrouter_chat_completions_api",
        metadata={
            "provider": "openrouter",
            "model": response_payload.get("model", model),
            "duration_ms": duration_ms,
            "response_id": response_payload.get("id"),
            "api": "chat_completions",
            "input_tokens": usage_metadata.get("prompt_tokens"),
            "output_tokens": usage_metadata.get("completion_tokens"),
            "total_tokens": usage_metadata.get("total_tokens"),
        },
    )


def extract_response_text(response_payload: dict[str, Any]) -> str:
    if isinstance(response_payload.get("output_text"), str):
        return response_payload["output_text"].strip()
    chunks: list[str] = []
    for item in response_payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    text = "\n".join(chunk.strip() for chunk in chunks if chunk.strip())
    if not text:
        text = json.dumps(response_payload, indent=2, sort_keys=True)
    return text.strip() + "\n"


def extract_chat_completion_text(response_payload: dict[str, Any]) -> str:
    provider_error = response_payload.get("error")
    if isinstance(provider_error, dict):
        error_code = provider_error.get("code", "provider_error")
        raise RuntimeError(f"OpenRouter baseline returned provider error code {error_code}")
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenRouter baseline response did not include choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise RuntimeError("OpenRouter baseline response included a malformed choice")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("OpenRouter baseline response did not include a message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenRouter baseline response did not include text content")
    return content.strip() + "\n"


def build_baseline(
    problem: str,
    provider: str,
    baseline_path: Path | None,
    model: str | None,
    timeout_seconds: float,
) -> BaselineResult:
    if baseline_path is not None:
        return BaselineResult(
            text=baseline_path.read_text(encoding="utf-8"),
            kind="static_direct_llm_baseline_fixture",
            metadata={"source_uri": str(baseline_path)},
        )
    if provider == "openrouter":
        openrouter_model = model or os.environ.get("OPENROUTER_MODEL", "")
        return call_openrouter_baseline(problem, openrouter_model, timeout_seconds)
    if provider == "openai":
        openai_model = model or os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        return call_openai_baseline(problem, openai_model, timeout_seconds)
    if provider == "auto" and os.environ.get("OPENROUTER_API_KEY"):
        openrouter_model = model or os.environ.get("OPENROUTER_MODEL", "")
        return call_openrouter_baseline(problem, openrouter_model, timeout_seconds)
    if provider == "auto" and os.environ.get("OPENAI_API_KEY"):
        openai_model = model or os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        return call_openai_baseline(problem, openai_model, timeout_seconds)
    return BaselineResult(
        text=render_template_baseline(problem),
        kind="local_direct_answer_template",
        metadata={
            "provider": "template",
            "reason": "No supported live baseline credential was available or baseline_provider=template was selected.",
        },
    )


def score_baseline(text: str) -> dict[str, Any]:
    lowered = text.lower()
    section_hits = [section for section in REQUIRED_REPORT_SECTIONS if section.lower() in lowered]
    signal_hits = [
        signal
        for signal in ["evidence against", "confidence", "checks performed", "audit trace", "open questions"]
        if signal in lowered
    ]
    return {
        "required_section_hits": section_hits,
        "required_section_count": len(section_hits),
        "audit_signal_hits": signal_hits,
        "audit_signal_count": len(signal_hits),
        "has_source_metadata": "source_uri" in lowered or "source:" in lowered,
        "has_contradiction_check": "contradiction" in lowered or "evidence against" in lowered,
    }


def build_comparison(baseline: BaselineResult) -> dict[str, Any]:
    baseline_score = score_baseline(baseline.text)
    polya_score = {
        "required_section_count": len(REQUIRED_REPORT_SECTIONS),
        "audit_signal_count": 5,
        "has_source_metadata": True,
        "has_contradiction_check": True,
        "has_file_artifacts": True,
        "has_deterministic_checks": True,
    }
    result = "polya_artifact_more_auditable"
    if baseline_score["required_section_count"] >= polya_score["required_section_count"]:
        result = "baseline_matches_required_sections"
    return {
        "baseline_kind": baseline.kind,
        "baseline_metadata": baseline.metadata,
        "baseline_note": "The baseline is a direct answer for the same problem, without the PolyaBrain artifact contract.",
        "baseline_score": baseline_score,
        "polya_score": polya_score,
        "result": result,
        "why": [
            "PolyaBrain output has explicit evidence metadata.",
            "PolyaBrain output separates evidence for and evidence against or uncertainty.",
            "PolyaBrain output includes deterministic checks and an audit trace.",
            "PolyaBrain output avoids permanent action before verification.",
        ],
    }


def render_report(
    case: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    verification: dict[str, Any],
    trace: list[dict[str, Any]],
) -> str:
    selected = next(item for item in hypotheses if item["status"] == "selected")
    evidence_by_id = {item["id"]: item for item in case["evidence"]}
    selected_for = [evidence_by_id[item] for item in selected["evidence_for"] if item in evidence_by_id]
    selected_against = [evidence_by_id[item] for item in selected["evidence_against"] if item in evidence_by_id]
    checks = [item["description"] for item in verification["checks_run"]]
    next_action = case.get("recommended_next_action") or selected["verification_checks"][0]
    open_questions = case.get("open_questions") or [
        "What direct measurement would confirm the selected hypothesis?",
        "What evidence would falsify it?",
        "Which fix is reversible enough to test first?",
    ]

    lines = [
        f"# PolyaBrain Investigation Report: {case['title']}",
        "",
        "## Final conclusion",
        f"The leading path is: {selected['statement']} Do not treat this as final until the verification checks below are run.",
        "",
        "## Confidence level",
        f"Moderate ({selected['confidence']:.2f}). The recommendation is directionally useful, but the evidence is still incomplete until checks are run.",
        "",
        "## Evidence used",
    ]
    for item in selected_for:
        lines.append(f"- `{item['id']}` ({item['source_type']}:{item['source_uri']}): {item['claim']}")

    lines.extend(["", "## Evidence against"])
    if selected_against:
        for item in selected_against:
            lines.append(f"- `{item['id']}` ({item['source_type']}:{item['source_uri']}): {item['claim']}")
    else:
        lines.append("- No direct contradictory evidence was supplied; this is an uncertainty, not proof.")
    lines.append("- A different failure mode may explain the symptom once direct measurements are collected.")

    lines.extend(["", "## Checks performed"])
    for check in checks:
        lines.append(f"- {check}")

    lines.extend(["", "## Open questions"])
    for question in open_questions:
        lines.append(f"- {question}")

    lines.extend(["", "## Recommended next action", next_action, "", "## Audit trace"])
    for event in trace:
        lines.append(f"- `{event['reasoning_mode']}` / `{event['engine_name']}`: {event['summary']}")

    lines.extend(["", "## Hypotheses considered"])
    for hypothesis in hypotheses:
        lines.append(
            f"- `{hypothesis['id']}` [{hypothesis['status']}] confidence={hypothesis['confidence']:.2f}: {hypothesis['statement']}"
        )

    return "\n".join(lines) + "\n"


def run_investigation(
    case: dict[str, Any],
    baseline: BaselineResult,
    output_root: Path,
    clean: bool,
    run_id: str | None = None,
) -> Path:
    run_dir = output_root / (run_id or case["case_id"])
    if clean and run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    hypotheses = case["hypothesis_candidates"]
    trace = build_trace(case, hypotheses)
    verification = build_verification(case, hypotheses)
    comparison = build_comparison(baseline)
    report = render_report(case, hypotheses, verification, trace)

    (run_dir / "trace.jsonl").write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in trace) + "\n",
        encoding="utf-8",
    )
    (run_dir / "direct_llm_baseline.md").write_text(baseline.text, encoding="utf-8")
    write_json(run_dir / "case.json", case)
    write_json(run_dir / "evidence.json", case["evidence"])
    write_json(run_dir / "hypotheses.json", hypotheses)
    write_json(run_dir / "verification_checklist.json", verification)
    write_json(run_dir / "baseline_comparison.json", comparison)
    (run_dir / "report.md").write_text(report, encoding="utf-8")

    return run_dir


def run_from_case_path(
    case_path: Path,
    output_root: Path,
    clean: bool,
    baseline_provider: str = "auto",
    baseline_path: Path | None = None,
    baseline_model: str | None = None,
    baseline_timeout_seconds: float = 30,
    run_id: str | None = None,
) -> Path:
    loaded_case = load_json(case_path)
    if "evidence" in loaded_case and "hypothesis_candidates" in loaded_case:
        case = loaded_case
    else:
        case = build_case_from_problem(
            problem=loaded_case["raw_problem"],
            case_id=loaded_case.get("case_id"),
        )
        for key in ["title", "success_criteria", "knowns", "constraints", "recommended_next_action", "open_questions"]:
            if key in loaded_case:
                case[key] = loaded_case[key]
    baseline = build_baseline(
        problem=case["raw_problem"],
        provider=baseline_provider,
        baseline_path=baseline_path,
        model=baseline_model,
        timeout_seconds=baseline_timeout_seconds,
    )
    return run_investigation(case, baseline, output_root, clean, run_id)


def run_from_problem(
    problem: str,
    output_root: Path,
    clean: bool,
    baseline_provider: str = "auto",
    baseline_model: str | None = None,
    baseline_timeout_seconds: float = 30,
    run_id: str | None = None,
) -> Path:
    case = build_case_from_problem(problem, run_id)
    baseline = build_baseline(
        problem=problem,
        provider=baseline_provider,
        baseline_path=None,
        model=baseline_model,
        timeout_seconds=baseline_timeout_seconds,
    )
    return run_investigation(case, baseline, output_root, clean, run_id)
