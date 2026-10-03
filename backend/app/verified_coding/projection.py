"""Project a verified-coding outcome into the existing PolyaState contracts."""

from __future__ import annotations

import hashlib
import re

from app.cognition.contracts import CognitiveRunStatus
from app.graph.state import ExecutionOutput, PolyaState, StateEvent, create_initial_state
from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    HypothesisStatus,
    KnowledgeGap,
    PlanTask,
    PriorityLevel,
    ReasoningMode,
    Reflection,
    RiskLevel,
    StructuredProblem,
    VerificationReport,
)
from app.verified_coding.contracts import Certificate, CertificateStatus, Finding
from app.verified_coding.pipeline import VerifiedOutcome
from app.verified_coding.prompts import PROMPT_VERSION

DRAFT_ID = "draft-implementation"
DELIVERED_ID = "delivered-implementation"

HEADLINES = {
    CertificateStatus.VERIFIED: "Verified against an independent reference",
    CertificateStatus.REPAIRED: "Repaired and verified: the first draft contradicted your problem statement",
    CertificateStatus.DISPUTED: "Not verified: an unresolved disagreement remains",
    CertificateStatus.AMBIGUOUS: "Not verified: your problem statement is ambiguous on a concrete input",
    CertificateStatus.UNVERIFIED: "Not verified: no independent check could be established",
    CertificateStatus.NO_CANDIDATE: "No implementation was produced",
}


def _prose(text: str) -> str:
    """Keep model prose from opening extra fenced blocks in the delivered answer."""
    return text.replace("```", "'''").strip()


def _inline(text: str, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", text).replace("`", "'")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _sizes(certificate: Certificate) -> str:
    sizes = certificate.sizes_covered
    return f"sizes {min(sizes)}–{max(sizes)}" if sizes else "no sizes"


DRAFT_DEFECT_VERDICTS = {"candidate_wrong", "both_wrong", "performance_repair"}


def draft_defect(finding: Finding) -> bool:
    """True when the finding exposed the delivered draft, not the verifier's own reference."""
    return finding.verdict in DRAFT_DEFECT_VERDICTS or (
        finding.source == "mutation" and finding.resolved and finding.verdict != "both_acceptable"
    )


def _finding_line(finding: Finding) -> str:
    where = "an example stated in your problem" if finding.source == "stated_example" else "input"
    head = f"On {where} `{_inline(finding.args)}`"
    if finding.source == "scale":
        return f"At the stated input limits ({_inline(finding.args)}) the draft exceeded its time limit; it was optimized and re-verified."
    if finding.source == "mutation":
        return f"{head} the draft modified its input arguments."
    rule = (
        f' Your requirement: "{_inline(finding.governing_requirement, 220)}".'
        if finding.governing_requirement
        else ""
    )
    expected = f" The correct result is `{_inline(finding.expected)}`." if finding.expected else ""
    return (
        f"{head} the draft returned `{_inline(finding.candidate_output)}` and the independent "
        f"reference returned `{_inline(finding.reference_output)}`.{rule}{expected} "
        f"Ruling: {finding.verdict.replace('_', ' ')}."
    )


def checks_run(outcome: VerifiedOutcome) -> list[str]:
    certificate = outcome.certificate
    checks: list[str] = []
    if certificate.own_test_count:
        state = "passed" if certificate.own_tests_passed else "did not all pass"
        checks.append(
            f"Solver's own {certificate.own_test_count} assertions executed in the sandbox: {state}."
        )
    if certificate.examples_sourced:
        checks.append(
            f"{certificate.examples_sourced} examples quoted from the problem executed against the delivered code."
        )
    if certificate.cases_compared:
        checks.append(
            f"Differential test: delivered code vs an independently written brute-force reference on "
            f"{certificate.cases_compared} generated inputs ({_sizes(certificate)})."
        )
    if certificate.scale_seconds or certificate.scale_timeouts:
        timings = ", ".join(f"{seconds:.3g}s" for seconds in certificate.scale_seconds)
        checks.append(
            f"Timed at the stated input limits: {timings or 'no completed run'}"
            + (f"; {certificate.scale_timeouts} timed out." if certificate.scale_timeouts else ".")
        )
    for finding in certificate.findings:
        if finding.resolved:
            checks.append(
                f"Round {finding.round}: adjudicated and re-verified a {finding.source.replace('_', ' ')} disagreement."
            )
    return checks or ["Lean solver attempt recorded; no independent verification ran."]


def final_answer(outcome: VerifiedOutcome) -> str | None:
    certificate = outcome.certificate
    if outcome.code is None:
        return None
    lines = [f"**{HEADLINES[certificate.status]}.**", ""]
    if certificate.status in {CertificateStatus.VERIFIED, CertificateStatus.REPAIRED}:
        lines.append(
            f"PolyaBrain compared this code with an independent brute-force reference on "
            f"{certificate.cases_compared} generated inputs and every example stated in your "
            "problem; all agree."
        )
    elif certificate.status is CertificateStatus.DISPUTED:
        lines.append(
            "Treat this code as unverified. Independent checking found an input where it may "
            "contradict your problem statement and the disagreement could not be resolved."
        )
    elif certificate.status is CertificateStatus.AMBIGUOUS:
        lines.append(
            f"Treat this code as unverified until you answer: {_prose(certificate.open_question)}"
        )
    else:
        lines.append(
            "Treat this code as unverified. It passed only the solver's own assertions."
            if certificate.own_tests_passed
            else "Treat this code as unverified. It did not pass the solver's own assertions."
        )
    lines += ["", "```python", outcome.code.rstrip(), "```", "", _prose(outcome.explanation), ""]
    defects = [item for item in certificate.findings if draft_defect(item) or not item.resolved]
    corrections = [item for item in certificate.findings if item not in defects]
    if defects:
        lines += ["**What independent verification found in the draft**", ""]
        lines += [f"- {_finding_line(item)}" for item in defects]
        lines.append("")
    if corrections:
        lines += ["**Verifier self-corrections (the draft was right)**", ""]
        lines += [f"- {_finding_line(item)}" for item in corrections]
        lines.append("")
    lines += ["**Checks performed**", ""]
    lines += [f"- {item}" for item in checks_run(outcome)]
    if certificate.assumptions:
        lines += ["", "**Interpretations the verifier assumed**", ""]
        lines += [f"- {_prose(item)}" for item in certificate.assumptions]
    lines += ["", "**Limits**", ""]
    lines += [f"- {item}" for item in certificate.limitations]
    return "\n".join(lines).strip()


def _evidence(outcome: VerifiedOutcome) -> list[EvidenceItem]:
    certificate = outcome.certificate
    final = certificate.final_differential
    items: list[EvidenceItem] = []
    delivered = [DELIVERED_ID]
    if certificate.own_test_count:
        items.append(
            EvidenceItem(
                source_type="sandbox_execution",
                source_uri="sandbox://verified-coding/solver-self-tests",
                claim=(
                    f"The solver's own {certificate.own_test_count} assertions "
                    + ("passed." if certificate.own_tests_passed else "did not all pass.")
                ),
                reliability_score=0.6,
                relevance_score=0.6,
                supports_hypothesis_ids=[DRAFT_ID] if certificate.own_tests_passed else [],
                contradicts_hypothesis_ids=[] if certificate.own_tests_passed else [DRAFT_ID],
            )
        )
    if final is not None and final.examples:
        passed = sum(item.candidate_ok for item in final.examples)
        items.append(
            EvidenceItem(
                source_type="problem_statement_examples",
                source_uri="problem://stated-examples",
                claim=f"{passed} of {len(final.examples)} examples stated in the problem pass on the delivered code.",
                raw_excerpt="; ".join(f"{item.call} == {item.expected}" for item in final.examples)[
                    :2000
                ],
                reliability_score=0.95,
                relevance_score=1.0,
                supports_hypothesis_ids=delivered if passed == len(final.examples) else [],
                contradicts_hypothesis_ids=[] if passed == len(final.examples) else delivered,
            )
        )
    if final is not None and final.cases_compared:
        agrees = final.agrees
        items.append(
            EvidenceItem(
                source_type="differential_execution",
                source_uri="sandbox://verified-coding/differential",
                claim=(
                    f"The delivered code agreed with an independently written brute-force reference on all "
                    f"{final.cases_compared} generated inputs ({_sizes(certificate)})."
                    if agrees
                    else f"The delivered code disagreed with the independent reference on {final.disagreements} "
                    f"of {final.cases_compared} generated inputs."
                ),
                reliability_score=0.85,
                relevance_score=0.9,
                supports_hypothesis_ids=delivered if agrees else [],
                contradicts_hypothesis_ids=[] if agrees else delivered,
            )
        )
    if certificate.scale_seconds:
        items.append(
            EvidenceItem(
                source_type="sandbox_measurement",
                source_uri="sandbox://verified-coding/scale",
                claim=(
                    "At the stated input limits the delivered code ran in "
                    + ", ".join(f"{seconds:.3g}s" for seconds in certificate.scale_seconds)
                    + " in a constrained sandbox."
                ),
                reliability_score=0.8,
                relevance_score=0.6,
                supports_hypothesis_ids=delivered if not certificate.scale_timeouts else [],
            )
        )
    for finding in certificate.findings:
        items.append(
            EvidenceItem(
                source_type="adjudicated_counterexample",
                source_uri=f"sandbox://verified-coding/finding/{finding.round}",
                claim=_finding_line(finding).replace("`", ""),
                raw_excerpt=finding.governing_requirement or None,
                reliability_score=0.8,
                relevance_score=1.0,
                contradicts_hypothesis_ids=(
                    [DRAFT_ID] if draft_defect(finding) else [] if finding.resolved else delivered
                ),
                supports_hypothesis_ids=[DRAFT_ID]
                if finding.resolved and not draft_defect(finding)
                else [],
            )
        )
    return items


def _hypotheses(outcome: VerifiedOutcome) -> list[Hypothesis]:
    status = outcome.certificate.status
    repaired = status is CertificateStatus.REPAIRED
    draft_status = (
        HypothesisStatus.VERIFIED
        if status is CertificateStatus.VERIFIED
        else HypothesisStatus.FALSIFIED
        if repaired
        else HypothesisStatus.CANDIDATE
    )
    hypotheses = [
        Hypothesis(
            statement="The lean solver's first draft satisfies every requirement of the problem.",
            origin=HypothesisOrigin.DIRECT_REASONING,
            verification_checks=[
                "Differential comparison with an independent brute-force reference."
            ],
            falsification_criteria=[
                "Any generated or stated input where the draft contradicts the problem text."
            ],
            status=draft_status,
        )
    ]
    if repaired:
        hypotheses.append(
            Hypothesis(
                statement="The repaired implementation satisfies every requirement of the problem.",
                origin=HypothesisOrigin.REFRAME,
                verification_checks=[
                    "Re-run of the full differential comparison and pinned counterexamples."
                ],
                falsification_criteria=["Any disagreement after repair."],
                status=HypothesisStatus.VERIFIED,
            )
        )
    return hypotheses


def _verification(outcome: VerifiedOutcome) -> VerificationReport:
    certificate = outcome.certificate
    checks = checks_run(outcome)
    if certificate.status in {CertificateStatus.VERIFIED, CertificateStatus.REPAIRED}:
        return VerificationReport(passed=True, checks_run=checks)
    unresolved = [item for item in certificate.findings if not item.resolved]
    failed = [_finding_line(item).replace("`", "") for item in unresolved]
    if certificate.status is CertificateStatus.AMBIGUOUS:
        failed.append(
            "The problem statement does not determine the output for at least one concrete input."
        )
        route = certificate.open_question or "Clarify the requirement and run again."
    elif certificate.status is CertificateStatus.UNVERIFIED:
        failed.append("No usable independent reference could be established.")
        route = "Supply reference examples or acceptance tests, then run again."
    elif certificate.status is CertificateStatus.NO_CANDIDATE:
        failed.append("The solver produced no implementation within its budget.")
        route = "Simplify or split the task, then run again."
    else:
        if not failed:
            failed.append("The delivered code and the independent reference still disagree.")
        route = "Review the disputed input against your requirement before relying on this code."
    return VerificationReport(
        passed=False, checks_run=checks, failed_checks=failed, recommended_route=route
    )


def _reflection(outcome: VerifiedOutcome) -> Reflection:
    certificate = outcome.certificate
    lessons = [
        f'Requirement easy to misread: "{_inline(item.governing_requirement, 200)}"'
        for item in certificate.findings
        if item.resolved and item.governing_requirement and draft_defect(item)
    ]
    follow_up = {
        CertificateStatus.VERIFIED: "Review the code and the interpretations listed in the report before using it.",
        CertificateStatus.REPAIRED: "Read the finding first: it shows exactly where a typical implementation misreads your requirement.",
        CertificateStatus.DISPUTED: "Check the disputed input against your requirement before relying on this code.",
        CertificateStatus.AMBIGUOUS: certificate.open_question
        or "Clarify the ambiguous requirement and run again.",
        CertificateStatus.UNVERIFIED: "Add acceptance examples to the problem statement and run again.",
        CertificateStatus.NO_CANDIDATE: "Simplify or split the task and run again.",
    }[certificate.status]
    return Reflection(
        outcome_summary=f"{HEADLINES[certificate.status]}.",
        what_worked=[item for item in checks_run(outcome)][:4],
        what_failed=[
            _finding_line(item).replace("`", "")
            for item in certificate.findings
            if not item.resolved
        ],
        reusable_lessons=lessons,
        strategy_notes=[f"Lean-first differential verification ({PROMPT_VERSION})."],
        follow_up_actions=[follow_up],
    )


def _plan_and_outputs(outcome: VerifiedOutcome) -> tuple[list[PlanTask], list[ExecutionOutput]]:
    tasks: list[PlanTask] = []
    outputs: list[ExecutionOutput] = []
    for index, run in enumerate(outcome.sandbox_runs, start=1):
        task_id = f"verified-coding-{index}-{run.purpose}"
        tasks.append(
            PlanTask(
                id=task_id,
                action=(
                    "Run the solver's implementation against its own assertions."
                    if run.purpose == "solver_self_tests"
                    else "Run the deterministic differential harness: candidate vs independent reference."
                ),
                tool_name="verified_coding_sandbox",
                params={"purpose": run.purpose},
                depends_on=[tasks[-1].id] if tasks else [],
                expected_output="Bounded sandbox execution summary.",
                risk_level=RiskLevel.MEDIUM,
            )
        )
        outputs.append(
            ExecutionOutput(
                task_id=task_id,
                summary=f"{run.purpose.replace('_', ' ')}: exit {run.exit_code}"
                + (" (timed out)" if run.timed_out else "")
                + f", {run.runtime_ms / 1000:.2f}s.",
                output=run.model_dump(mode="json"),
            )
        )
    return tasks, outputs


def project(
    outcome: VerifiedOutcome,
    *,
    raw_input: str,
    session_id: str | None = None,
    prior_events: list[StateEvent] | None = None,
) -> tuple[CognitiveRunStatus, PolyaState]:
    """Return a terminal run status and a complete, contract-valid state."""
    state = create_initial_state(raw_input, session_id=session_id)
    certificate = outcome.certificate
    first_sentence = re.split(r"(?<=[.!?])\s", raw_input.strip(), maxsplit=1)[0]
    state["structured_problem"] = StructuredProblem(
        core_question=_inline(first_sentence, 300),
        problem_type="implementation",
        domain="software",
        constraints=["Python standard library only; networkless sandbox execution."],
        success_criteria=[
            "Delivered code agrees with an independent reference on generated inputs.",
            "Delivered code satisfies every example stated in the problem.",
        ],
    )
    if certificate.status is CertificateStatus.AMBIGUOUS:
        state["gaps"] = [
            KnowledgeGap(
                description=certificate.open_question or "Clarify the ambiguous requirement.",
                gap_type="specification",
                priority=PriorityLevel.HIGH,
                why_needed="The problem text does not determine the correct output for a concrete input.",
                suggested_source="user",
            )
        ]
    state["evidence"] = _evidence(outcome)
    state["hypotheses"] = _hypotheses(outcome)
    state["plan"], state["execution_outputs"] = _plan_and_outputs(outcome)
    state["verification"] = _verification(outcome)
    state["reflection"] = _reflection(outcome)
    state["final_answer"] = final_answer(outcome)
    events = list(prior_events or [])
    events += [StateEvent.model_validate(item) for item in outcome.events]
    code_hash = hashlib.sha256(outcome.code.encode()).hexdigest() if outcome.code else None
    events.append(
        StateEvent(
            engine_name="verified_coding",
            event_type="verified_coding_certificate",
            reasoning_mode=ReasoningMode.VERIFY,
            summary=f"{HEADLINES[certificate.status]}.",
            metadata={
                "prompt_version": PROMPT_VERSION,
                "delivered_code_sha256": code_hash,
                "certificate": certificate.model_dump(mode="json"),
                "model_calls": [call.model_dump(mode="json") for call in outcome.model_calls],
            },
        )
    )
    state["events"] = events
    status = (
        CognitiveRunStatus.COMPLETED
        if certificate.status in {CertificateStatus.VERIFIED, CertificateStatus.REPAIRED}
        else CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    )
    return status, state
