"""Chapter 5 core Pydantic contract tests."""

import pytest
from pydantic import BaseModel, ValidationError

from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    HypothesisStatus,
    KnowledgeGap,
    PlanTask,
    PriorityLevel,
    Reflection,
    RiskLevel,
    StructuredProblem,
    VerificationReport,
)

ContractBundle = tuple[
    StructuredProblem,
    KnowledgeGap,
    EvidenceItem,
    Hypothesis,
    PlanTask,
    VerificationReport,
    Reflection,
]


def assert_json_round_trip(model: BaseModel) -> None:
    """Assert a contract can serialize and validate back to the same payload."""
    parsed = type(model).model_validate_json(model.model_dump_json())

    assert parsed == model


def valid_structured_problem(**overrides: object) -> StructuredProblem:
    payload: dict[str, object] = {
        "core_question": "What changed after the deployment?",
        "problem_type": "software_debugging",
        "domain": "technical_investigation",
        "knowns": ["p95 latency increased after deploy"],
        "unknowns": ["query path", "cache hit rate"],
        "constraints": ["avoid irreversible production changes"],
        "success_criteria": ["identify the safest next diagnostic check"],
        "affected_entities": ["api", "database"],
        "time_window": {"relative": "after deploy"},
        "required_data_sources": ["deploy diff", "slow query logs"],
    }
    payload.update(overrides)
    return StructuredProblem.model_validate(payload)


def valid_knowledge_gap(**overrides: object) -> KnowledgeGap:
    payload: dict[str, object] = {
        "description": "Need query-level metrics before choosing a fix.",
        "gap_type": "missing_metric",
        "priority": PriorityLevel.HIGH,
        "why_needed": "A cache recommendation is premature without bottleneck evidence.",
        "suggested_source": "database slow query log",
        "filled": False,
        "evidence_ids": [],
    }
    payload.update(overrides)
    return KnowledgeGap.model_validate(payload)


def valid_evidence_item(**overrides: object) -> EvidenceItem:
    payload: dict[str, object] = {
        "source_type": "trace",
        "source_uri": "artifact://trace/request-path",
        "claim": "Database time dominates the changed request path.",
        "raw_excerpt": "db_ms increased while external_api_ms stayed flat",
        "reliability_score": 0.82,
        "relevance_score": 0.91,
        "supports_hypothesis_ids": ["hyp_query_path"],
        "contradicts_hypothesis_ids": [],
    }
    payload.update(overrides)
    return EvidenceItem.model_validate(payload)


def valid_hypothesis(**overrides: object) -> Hypothesis:
    payload: dict[str, object] = {
        "statement": "The deployment changed the query path.",
        "mechanism": "A query-plan or ORM change can increase database work.",
        "origin": HypothesisOrigin.DIRECT_REASONING,
        "analogical_source_ids": [],
        "expected_signals": ["higher query count", "changed query plan"],
        "evidence_for": ["ev_query_path"],
        "evidence_against": [],
        "verification_checks": ["compare slow query logs before and after deploy"],
        "falsification_criteria": ["no query-count or query-plan change"],
        "confidence": 0.74,
        "selection_rationale": "It is cheaper and more falsifiable than adding Redis.",
        "status": HypothesisStatus.SELECTED,
    }
    payload.update(overrides)
    return Hypothesis.model_validate(payload)


def valid_plan_task(**overrides: object) -> PlanTask:
    payload: dict[str, object] = {
        "id": "task_query_diff",
        "action": "Compare slow query logs before and after deploy.",
        "tool_name": "database_metric_review",
        "params": {"window": "post_deploy"},
        "depends_on": [],
        "expected_output": "Evidence for or against query-path regression",
        "risk_level": RiskLevel.LOW,
    }
    payload.update(overrides)
    return PlanTask.model_validate(payload)


def valid_verification_report(**overrides: object) -> VerificationReport:
    payload: dict[str, object] = {
        "passed": True,
        "checks_run": ["query_diff_reviewed", "cache_metric_compared"],
        "failed_checks": [],
        "contradictions": [],
        "confidence_delta": 0.1,
        "recommended_route": "continue",
    }
    payload.update(overrides)
    return VerificationReport.model_validate(payload)


def valid_reflection(**overrides: object) -> Reflection:
    payload: dict[str, object] = {
        "outcome_summary": "The run preserved uncertainty and chose a reversible check.",
        "what_worked": ["Evidence was separated from hypotheses."],
        "what_failed": ["The prompt lacked direct measurement data."],
        "reusable_lessons": ["Measure the bottleneck before recommending infrastructure."],
        "memory_updates": ["Store query-path-before-cache as a procedural lesson."],
        "strategy_notes": ["Prefer low-risk falsification checks first."],
        "follow_up_actions": ["Add this case to the debugging fixture set."],
    }
    payload.update(overrides)
    return Reflection.model_validate(payload)


def contract_bundle_for_category(
    *,
    category: str,
    core_question: str,
    problem_type: str,
    known: str,
    unknown: str,
    constraint: str,
    success_criterion: str,
    evidence_claim: str,
    hypothesis_statement: str,
    plan_action: str,
) -> ContractBundle:
    evidence_id = f"ev_{category}"
    hypothesis_id = f"hyp_{category}"
    task_id = f"task_{category}"

    structured_problem = valid_structured_problem(
        core_question=core_question,
        problem_type=problem_type,
        domain=category,
        knowns=[known],
        unknowns=[unknown],
        constraints=[constraint],
        success_criteria=[success_criterion],
        affected_entities=[category],
        time_window={},
        required_data_sources=[f"{category} source"],
    )
    knowledge_gap = valid_knowledge_gap(
        description=unknown,
        gap_type=f"{category}_gap",
        why_needed=f"Resolving {unknown} is required to verify the answer.",
        evidence_ids=[evidence_id],
    )
    evidence_item = valid_evidence_item(
        source_type=category,
        source_uri=f"fixture://chapter-5/{category}",
        claim=evidence_claim,
        raw_excerpt=f"Fixture evidence for {category}.",
        supports_hypothesis_ids=[hypothesis_id],
    )
    hypothesis = valid_hypothesis(
        statement=hypothesis_statement,
        evidence_for=[evidence_id],
        evidence_against=[],
        verification_checks=[success_criterion],
        falsification_criteria=[f"{hypothesis_statement} is contradicted by source data"],
        status=HypothesisStatus.SELECTED,
    )
    plan_task = valid_plan_task(
        id=task_id,
        action=plan_action,
        depends_on=[],
        expected_output=success_criterion,
    )
    verification_report = valid_verification_report(
        checks_run=[success_criterion],
        recommended_route="continue",
    )
    reflection = valid_reflection(
        outcome_summary=f"{category} fixture completed with explicit checks.",
        what_worked=[success_criterion],
        reusable_lessons=[f"Keep {category} evidence linked to hypotheses."],
    )
    return (
        structured_problem,
        knowledge_gap,
        evidence_item,
        hypothesis,
        plan_task,
        verification_report,
        reflection,
    )


def test_core_contracts_round_trip_through_json() -> None:
    models = [
        valid_structured_problem(),
        valid_knowledge_gap(),
        valid_evidence_item(),
        valid_hypothesis(),
        valid_plan_task(),
        valid_verification_report(),
        valid_reflection(),
    ]

    for model in models:
        assert_json_round_trip(model)


@pytest.mark.parametrize(
    "bundle",
    [
        contract_bundle_for_category(
            category="math",
            core_question="What value maximizes the constrained expression?",
            problem_type="mathematical_reasoning",
            known="x + y = 10",
            unknown="optimal values of x and y",
            constraint="x and y are non-negative",
            success_criterion="check boundary and critical points",
            evidence_claim="The objective must be checked at boundaries and critical points.",
            hypothesis_statement="The maximum is found by evaluating both critical and boundary points.",
            plan_action="Compute critical points and compare boundary values.",
        ),
        contract_bundle_for_category(
            category="technical_research",
            core_question="Which current API behavior matters for the migration?",
            problem_type="technical_research",
            known="the API changed recently",
            unknown="current documented limit",
            constraint="use source metadata",
            success_criterion="cite authoritative docs",
            evidence_claim="Official documentation is required before migration advice is trusted.",
            hypothesis_statement="The migration should follow the documented current API limit.",
            plan_action="Check the official documentation and extract the current limit.",
        ),
        contract_bundle_for_category(
            category="software_debugging",
            core_question="Why did the job start timing out?",
            problem_type="software_debugging",
            known="timeouts began after dependency upgrade",
            unknown="changed dependency behavior",
            constraint="no production mutation",
            success_criterion="find a reversible diagnostic",
            evidence_claim="The first check should compare behavior before and after the upgrade.",
            hypothesis_statement="The dependency upgrade changed runtime behavior under load.",
            plan_action="Compare logs and dependency changelog for timeout-related changes.",
        ),
        contract_bundle_for_category(
            category="data_analysis",
            core_question="Which segment explains the revenue anomaly?",
            problem_type="data_analysis",
            known="total revenue dropped",
            unknown="segment contribution",
            constraint="preserve source table lineage",
            success_criterion="identify largest contributing segment",
            evidence_claim="Segment-level comparison is required before explaining the total anomaly.",
            hypothesis_statement="One segment accounts for most of the revenue anomaly.",
            plan_action="Group revenue by segment and compare current values to baseline.",
        ),
        contract_bundle_for_category(
            category="planning",
            core_question="What should be built next for the MVP?",
            problem_type="planning_strategy",
            known="Chapter 4 is complete",
            unknown="highest-leverage next implementation unit",
            constraint="keep MVP narrow",
            success_criterion="produce a verifiable next chapter",
            evidence_claim="The master plan sequences contracts before graph work.",
            hypothesis_statement="The next MVP step should preserve the chapter sequence.",
            plan_action="Compare candidate next steps against the master plan and verification gate.",
        ),
        contract_bundle_for_category(
            category="ambiguous_problem",
            core_question="What does 'make it faster' specifically mean?",
            problem_type="ambiguous_input",
            known="the user wants improved speed",
            unknown="target workflow, metric, and baseline",
            constraint="ask clarifying questions when confidence is low",
            success_criterion="identify missing clarification",
            evidence_claim="The prompt lacks the metric and baseline needed for a safe recommendation.",
            hypothesis_statement="The correct next action is clarification rather than a premature fix.",
            plan_action="Ask for target workflow, performance metric, and current baseline.",
        ),
    ],
)
def test_contract_bundles_cover_required_benchmark_categories(bundle: ContractBundle) -> None:
    for model in bundle:
        assert_json_round_trip(model)


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        valid_structured_problem(unplanned_field="scope creep")


def test_empty_required_strings_are_rejected() -> None:
    with pytest.raises(ValidationError, match="String should have at least 1 character"):
        valid_evidence_item(claim="   ")


def test_evidence_requires_source_uri_or_raw_excerpt_provenance() -> None:
    with pytest.raises(
        ValidationError,
        match="evidence item requires source_uri or raw_excerpt provenance",
    ):
        valid_evidence_item(source_uri=None, raw_excerpt=None)


def test_invalid_enum_values_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Input should be"):
        valid_plan_task(risk_level="severe")


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_scores_must_be_between_zero_and_one(score: float) -> None:
    with pytest.raises(ValidationError):
        valid_evidence_item(reliability_score=score)


@pytest.mark.parametrize("confidence_delta", [-1.1, 1.1])
def test_confidence_delta_must_be_between_negative_one_and_one(
    confidence_delta: float,
) -> None:
    with pytest.raises(ValidationError):
        valid_verification_report(confidence_delta=confidence_delta)


def test_selected_hypothesis_requires_verification_checks() -> None:
    with pytest.raises(
        ValidationError,
        match="selected hypothesis requires at least one verification check",
    ):
        valid_hypothesis(verification_checks=[])


def test_selected_hypothesis_requires_evidence_for_or_against() -> None:
    with pytest.raises(
        ValidationError,
        match="selected hypothesis requires supporting or contradicting evidence",
    ):
        valid_hypothesis(evidence_for=[], evidence_against=[])


def test_selected_hypothesis_requires_falsification_criteria() -> None:
    with pytest.raises(
        ValidationError,
        match="selected hypothesis requires at least one falsification criterion",
    ):
        valid_hypothesis(falsification_criteria=[])


def test_selected_hypothesis_requires_selection_rationale() -> None:
    with pytest.raises(
        ValidationError,
        match="selected hypothesis requires selection rationale",
    ):
        valid_hypothesis(selection_rationale=None)


def test_verification_report_requires_checks_run() -> None:
    with pytest.raises(
        ValidationError,
        match="verification report requires at least one check run",
    ):
        valid_verification_report(checks_run=[])


def test_passing_verification_report_cannot_include_failed_checks() -> None:
    with pytest.raises(
        ValidationError,
        match="passing verification report cannot include failed checks",
    ):
        valid_verification_report(failed_checks=["source contradiction"])


def test_failing_verification_report_requires_failure_detail_or_route() -> None:
    with pytest.raises(
        ValidationError,
        match="failing verification report requires failed checks",
    ):
        valid_verification_report(
            passed=False,
            failed_checks=[],
            contradictions=[],
            recommended_route=None,
        )
