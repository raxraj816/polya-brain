"""Compute-aware capabilities for the Chapter 13-D on-demand cognition proof."""

from __future__ import annotations

import re

from pydantic import JsonValue

from app.cognition.arithmetic_pack import is_simple_arithmetic
from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CapabilityKind,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.cognition.dependency_facts import INSTRUCTIONS, dependency_source_facts
from app.cognition.evidence_closure import (
    TrustedEvidenceAttester,
    attested_evidence_procedure_capability,
)
from app.cognition.measurement_units import VERSION as MEASUREMENT_VERSION
from app.cognition.measurement_units import uncertainty_failures
from app.cognition.model_capabilities import (
    _arithmetic_conclusion_output,
    _arithmetic_deliberation_output,
)
from app.cognition.model_contracts import ConclusionCheckOutput, DeliberationCapabilityOutput
from app.cognition.model_gateway import CognitiveModelGateway
from app.cognition.report_metadata import report_metadata_event
from app.cognition.verification_factory import verifier_factory_capability
from app.cognition.verification_research import (
    ANALYSIS_EVENT,
    needs_recovery_analysis,
    research_update,
)
from app.cognition.verification_research import (
    VERSION as RESEARCH_VERSION,
)
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    KnowledgeGap,
    PlanTask,
    PriorityLevel,
    ReasoningMode,
    Reflection,
    RiskLevel,
    VerificationReport,
)


def _has_terms(text: str, terms: tuple[str, ...]) -> bool:
    # Do not confuse "compatible" with "table" or a username/path with a source kind.
    return any(re.search(r"\b" + re.escape(term) + r"\b", text) for term in terms)


def _source_for_unknown(unknown: str, declared_sources: list[str]) -> str:
    # Source declarations describe where to learn; subject words describe what
    # to learn. Reading a published measurement is not a request to measure it.
    public_only = bool(declared_sources) and all(
        re.search(r"\b(?:official|public|web|online)\b|https?://", source.casefold())
        for source in declared_sources
    )
    explicit_private = re.search(
        r"\b(?:user|human|preference|approval|local|private|confidential)\b|"
        r"(?:^|\s)(?:file://|/Users/|/home/|[A-Za-z]:\\)",
        unknown,
        re.IGNORECASE,
    )
    if public_only:
        if re.search(
            r"\b(?:local|file|artifact|repository)\b|/Users/|/home/", unknown, re.IGNORECASE
        ):
            return "local artifact"
        if _has_terms(unknown.casefold(), ("user", "human", "preference", "approval")):
            return "human input"
        return "human input" if explicit_private else "official web source"
    combined = " ".join([unknown, *declared_sources]).casefold()
    combined = re.sub(r"(?:file://)?(?:[A-Za-z]:)?[/\\][^\s]+", " local artifact ", combined)
    combined = re.sub(
        r"\b[^\s/\\]+\.(?:cfg|conf|csv|ini|json|log|md|py|sql|toml|txt|xml|ya?ml)\b",
        " local artifact ",
        combined,
    )
    if _has_terms(combined, ("calculate", "calculator", "arithmetic", "numeric")):
        return "calculator"
    if _has_terms(
        combined,
        ("dataset", "measurement", "table", "percentile", "median", "average", "row count"),
    ):
        return "dataset measurement"
    if _has_terms(
        combined,
        ("file", "document", "manual", "repository", "artifact", "artifacts", "csv", "json"),
    ):
        # Format does not determine the question: JSON can be a dependency report,
        # configuration or policy document rather than a table to aggregate.
        return "local artifact"
    if _has_terms(combined, ("experiment", "controlled test")):
        return "controlled experiment"
    if _has_terms(combined, ("simulation", "scenario")):
        return "simulation"
    if _has_terms(combined, ("web", "official", "current", "public", "api")):
        return "official web source"
    if _has_terms(combined, ("user", "preference", "intent", "approval")):
        return "human input"
    return declared_sources[0] if declared_sources else "direct observation or human input"


def _gap_type(unknown: str, source: str) -> str:
    del unknown
    return {
        "calculator": "numeric_computation",
        "dataset measurement": "missing_measurement",
        "local artifact": "missing_artifact_knowledge",
        "controlled experiment": "controlled_experiment",
        "simulation": "simulation",
        "official web source": "current_external_fact",
        "human input": "user_owned_information",
    }.get(source, "missing_observation")


def task_gap_detector_capability() -> FunctionCapability:
    """Convert explicit unknowns into actionable gaps without a model call."""
    definition = CapabilityDefinition(
        name="task_gap_detector",
        version="explicit_unknown_gap_detector@0.2.2",
        supported_actions={CognitiveActionType.DETECT_GAPS},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.0,
        kind=CapabilityKind.DETERMINISTIC,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        problem = state["structured_problem"]
        if problem is None:
            raise ValueError("task gap detection requires a structured problem")
        existing = {gap.description.casefold() for gap in state["gaps"]}
        gaps: list[KnowledgeGap] = []
        local_artifact_unknowns: list[str] = []
        public_unknowns: list[str] = []
        unbatched_unknowns: list[str] = []
        for unknown in problem.unknowns:
            if unknown.casefold() in existing:
                unbatched_unknowns.append(unknown)
                continue
            source = _source_for_unknown(unknown, problem.required_data_sources)
            if source == "local artifact":
                local_artifact_unknowns.append(unknown)
                continue
            if source == "official web source" and problem.required_data_sources:
                public_unknowns.append(unknown)
                continue
            unbatched_unknowns.append(unknown)
            gaps.append(
                KnowledgeGap(
                    description=unknown,
                    gap_type=_gap_type(unknown, source),
                    priority=PriorityLevel.HIGH,
                    why_needed=(
                        "This declared unknown blocks at least one verified success criterion."
                    ),
                    suggested_source=source,
                )
            )
        if local_artifact_unknowns:
            local_gap = (
                local_artifact_unknowns[0]
                if len(local_artifact_unknowns) == 1
                else "Resolve these unknowns from one inspection of the explicit local "
                "artifacts: " + " | ".join(local_artifact_unknowns)
            )
            unbatched_unknowns.append(local_gap)
            if local_gap.casefold() not in existing:
                gaps.append(
                    KnowledgeGap(
                        description=local_gap,
                        gap_type="missing_artifact_knowledge",
                        priority=PriorityLevel.HIGH,
                        why_needed=(
                            "These declared unknowns share the same bounded explicit-artifact "
                            "acquisition and block a verified success criterion."
                        ),
                        suggested_source="local artifact",
                    )
                )
        if public_unknowns:
            public_gap = (
                public_unknowns[0]
                if len(public_unknowns) == 1
                else "Resolve these questions from the declared public sources: "
                + " | ".join(public_unknowns)
            )
            unbatched_unknowns.append(public_gap)
            gaps.append(
                KnowledgeGap(
                    description=public_gap,
                    gap_type="current_external_fact",
                    priority=PriorityLevel.HIGH,
                    why_needed="These questions share declared public sources; all require evidence coverage.",
                    suggested_source="official web source",
                )
            )
        normalized_problem = (
            problem.model_copy(update={"unknowns": unbatched_unknowns})
            if unbatched_unknowns != problem.unknowns
            else None
        )
        event = StateEvent(
            engine_name=definition.name,
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary=f"Constructed {len(gaps)} explicit blocking gap(s) deterministically.",
            metadata={
                "status": "ok",
                "gap_count": len(gaps),
                "procedure": "explicit_unknown_to_gap",
                "llm_call_count": 0,
                "batched_local_artifact_unknown_count": len(local_artifact_unknowns),
                "batched_public_source_unknown_count": len(public_unknowns),
                "public_question_groups": {public_gap: [str(q) for q in public_unknowns]}
                if public_unknowns
                else {},
            },
        )
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=event.summary,
            payload={"procedure": "deterministic", "model_calls": 0},
            proposed_update=CognitiveStateUpdate(
                structured_problem=normalized_problem,
                gaps_to_add=gaps,
                trace_events_to_add=[event],
            ),
        )

    return FunctionCapability(definition, execute)


def _authoritative_artifact_evidence(state: PolyaState) -> EvidenceItem | None:
    """Return one provenance-checked fact eligible for exact lookup procedure."""
    eligible = [
        item
        for item in state["evidence"]
        if item.source_type == "evaluated_local_artifact"
        and item.source_uri is not None
        and item.source_uri.startswith("file://")
        and item.raw_excerpt is not None
        and item.claim in item.raw_excerpt
        and (item.reliability_score or 0.0) >= 0.75
        and (item.relevance_score or 0.0) >= 0.2
    ]
    if len(eligible) != 1:
        return None
    return eligible[0]


def artifact_lookup_procedure_capability() -> FunctionCapability:
    """Solve one exact explicit-artifact lookup without semantic model calls."""
    definition = CapabilityDefinition(
        name="artifact_lookup_procedure",
        version="verified_artifact_lookup@0.1.0",
        supported_actions={CognitiveActionType.HYPOTHESIZE, CognitiveActionType.VERIFY},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.01,
        kind=CapabilityKind.DETERMINISTIC,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        problem = state["structured_problem"]
        evidence = _authoritative_artifact_evidence(state)
        if problem is None or problem.problem_type != "explicit_artifact_lookup":
            raise ValueError("artifact lookup procedure requires its exact task shape")
        if evidence is None:
            raise ValueError("artifact lookup procedure requires one admitted local fact")
        source_uri = evidence.source_uri
        if source_uri is None:
            raise ValueError("artifact lookup procedure requires source provenance")
        if action.action_type is CognitiveActionType.HYPOTHESIZE:
            task_id = "verify-explicit-artifact-fact"
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.SUCCEEDED,
                summary="Applied the exact artifact-lookup procedure without a model.",
                payload={"procedure": "deterministic", "model_calls": 0},
                proposed_update=CognitiveStateUpdate(
                    hypotheses_to_add=[
                        Hypothesis(
                            statement=evidence.claim,
                            mechanism="Read the admitted fact from its source-visible excerpt.",
                            origin=HypothesisOrigin.DIRECT_REASONING,
                            expected_signals=[evidence.claim],
                            evidence_for=[source_uri],
                            verification_checks=[
                                "Confirm the extracted fact occurs in the admitted artifact excerpt."
                            ],
                            falsification_criteria=[
                                "The claim is absent from the excerpt or lacks artifact provenance."
                            ],
                        )
                    ],
                    plan_tasks_to_add=[
                        PlanTask(
                            id=task_id,
                            action="Check the extracted fact against its admitted artifact excerpt.",
                            tool_name=definition.name,
                            expected_output="An exact claim/excerpt/provenance match.",
                        )
                    ],
                    execution_outputs_to_add=[
                        ExecutionOutput(
                            task_id=task_id,
                            summary="The extracted fact occurs in the admitted artifact excerpt.",
                            output={
                                "claim": evidence.claim,
                                "source_uri": source_uri,
                                "excerpt_match": True,
                            },
                        )
                    ],
                    trace_events_to_add=[
                        StateEvent(
                            engine_name=definition.name,
                            event_type="deterministic_procedure_applied",
                            reasoning_mode=ReasoningMode.EXECUTE,
                            summary="Used the verified explicit-artifact lookup procedure.",
                            metadata={
                                "procedure": "claim_excerpt_provenance_match",
                                "llm_call_count": 0,
                                "source_uri": source_uri,
                            },
                        )
                    ],
                ),
            )
        if action.action_type is not CognitiveActionType.VERIFY:
            raise ValueError("artifact lookup procedure received an unsupported action")
        excerpt_match = bool(evidence.raw_excerpt and evidence.claim in evidence.raw_excerpt)
        provenance_match = source_uri.startswith("file://")
        checks = [
            f"Checked criterion {index + 1} against the exact admitted claim, excerpt, and file provenance."
            for index, _criterion in enumerate(problem.success_criteria)
        ] or ["Checked the extracted claim against its admitted excerpt and file provenance."]
        passed = excerpt_match and provenance_match
        failures = []
        if not excerpt_match:
            failures.append("The extracted claim is absent from the admitted excerpt.")
        if not provenance_match:
            failures.append("The evidence lacks approved local-file provenance.")
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=(
                "Deterministic artifact verification passed."
                if passed
                else "Deterministic artifact verification failed."
            ),
            payload={"procedure": "deterministic", "model_calls": 0},
            proposed_update=CognitiveStateUpdate(
                verification=VerificationReport(
                    passed=passed,
                    checks_run=checks,
                    failed_checks=failures,
                    confidence_delta=0.2 if passed else -0.5,
                    recommended_route="finalize" if passed else "replan",
                ),
                final_answer=evidence.claim if passed else None,
                reflection=(
                    Reflection(
                        outcome_summary="Resolved an exact lookup from one admitted local artifact.",
                        what_worked=[
                            "Matched the extracted claim to its source-visible excerpt and provenance."
                        ],
                        reusable_lessons=[
                            "Use deterministic claim/excerpt verification for exact explicit-artifact lookups."
                        ],
                        strategy_notes=["explicit_artifact_claim_excerpt_match"],
                    )
                    if passed
                    else None
                ),
            ),
        )

    return FunctionCapability(definition, execute)


def deliberator_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
    max_output_tokens: int = 6000,
    timeout_seconds: float = 90.0,
    deterministic_only: bool = False,
) -> FunctionCapability:
    """Fuse candidate generation, minimal planning, and state-only analysis."""
    if not 512 <= max_output_tokens <= 100_000:
        raise ValueError("deliberator max_output_tokens must be between 512 and 100000")
    if not 1.0 <= timeout_seconds <= 300.0:
        raise ValueError("deliberator timeout_seconds must be between 1 and 300")
    definition = CapabilityDefinition(
        name="arithmetic_deliberator" if deterministic_only else "deliberator",
        version="arithmetic_deliberator@0.1.0"
        if deterministic_only
        else gateway.capability_version("fused_deliberator@0.7.0"),
        supported_actions={CognitiveActionType.HYPOTHESIZE},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=deterministic_only or approved_for_sensitive_data,
        estimated_cost=0.32,
        kind=CapabilityKind.DETERMINISTIC if deterministic_only else CapabilityKind.MODEL,
        max_model_calls=0 if deterministic_only else gateway.max_provider_attempts_per_capability,
        max_output_tokens=0 if deterministic_only else max_output_tokens,
        timeout_seconds=1.0 if deterministic_only else timeout_seconds,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        if is_simple_arithmetic(state):
            output = _arithmetic_deliberation_output(state)
            if deterministic_only:
                output = output.model_copy(
                    update={
                        "tasks": [
                            task.model_copy(update={"tool_name": definition.name})
                            for task in output.tasks
                        ],
                    }
                )
            payload: JsonValue = {"procedure": "deterministic", "model_calls": 0}
        else:
            if deterministic_only:
                raise ValueError("deterministic arithmetic requires its recognized task shape")
            result = gateway.complete(
                capability=definition.name,
                instructions=(
                    "Using only canonical evidence and state, construct distinct falsifiable "
                    "candidate solutions, the smallest set of checks needed for every success "
                    "criterion, and one inspectable state-only analytic output for every task. "
                    "This call combines hypothesis, planning, and bounded analysis; it does not "
                    "verify or finalize. Every task tool_name must be 'deliberator'. Every output "
                    "must distinguish evidence-backed claims from assumptions and must never "
                    "claim new search, measurement, code execution, or external action. "
                    "Keep the response compact: propose two meaningful alternatives and at "
                    "most two grouped analytic tasks covering the success criteria. Use source "
                    "references and concise findings, not repeated evidence quotations. "
                    "Do not fill optional fields with redundant prose. Each execution_output.output "
                    "must contain your actual analytic findings, such as an itemized inventory or "
                    "comparison with source references. Written analysis of supplied evidence is "
                    "allowed; it does not claim external execution. A null output or a statement "
                    "that no tools were run is not a completed analytic task. Cover every requested "
                    "item. When the deliverable is a proposal, keep feasibility conditional on "
                    "the future checks instead of claiming it has been demonstrated. "
                    "If verification_research_requested is present, reassess the earlier failed "
                    "checks using newly admitted evidence. Earlier analytic outputs are history, "
                    "not proof of the revised conclusion. Explicitly identify which earlier "
                    "claims remain supported, change, or remain unresolved. " + INSTRUCTIONS
                ),
                output_type=DeliberationCapabilityOutput,
                state=state,
                max_output_tokens=max_output_tokens,
                total_timeout_seconds=definition.timeout_seconds,
                context=dependency_source_facts(state).context(),
            )
            output = result.output
            payload = {
                "provider": result.provider,
                "model": result.model,
                "usage": result.usage.model_dump(mode="json"),
                "model_calls": result.model_calls,
                "route_attempts": [
                    {
                        "route": item.route,
                        "succeeded": item.succeeded,
                        "duration_ms": item.duration_ms,
                        "provider_attempts": item.provider_attempts,
                        "failure_kind": item.failure_kind,
                    }
                    for item in result.route_attempts
                ],
            }
        if any(task.tool_name != definition.name for task in output.tasks):
            raise ValueError("fused deliberation may use only its state-only analytic boundary")
        recovery_events: list[StateEvent] = []
        if needs_recovery_analysis(state):
            # Preserve prior work and disambiguate every new task/output pair even
            # when a model reuses its original task IDs.
            existing_ids = {task.id for task in state["plan"]}
            existing_ids.update(item.task_id for item in state["execution_outputs"])
            id_map: dict[str, str] = {}
            for index, task in enumerate(output.tasks, start=1):
                new_id = f"verification-research-{index}"
                while new_id in existing_ids:
                    new_id += "-new"
                existing_ids.add(new_id)
                id_map[task.id] = new_id
            output = output.model_copy(
                update={
                    "tasks": [
                        task.model_copy(
                            update={
                                "id": id_map[task.id],
                                "depends_on": [id_map.get(dep, dep) for dep in task.depends_on],
                            }
                        )
                        for task in output.tasks
                    ],
                    "execution_outputs": [
                        item.model_copy(update={"task_id": id_map[item.task_id]})
                        for item in output.execution_outputs
                    ],
                }
            )
            recovery_events.append(
                StateEvent(
                    engine_name=definition.name,
                    event_type=ANALYSIS_EVENT,
                    reasoning_mode=ReasoningMode.COMPARE,
                    summary="Reassessed recovered evidence; independent verification is still required.",
                    metadata={
                        "version": RESEARCH_VERSION,
                        "action_id": action.id,
                        "current_task_ids": list(id_map.values()),
                        "prior_task_ids": [task.id for task in state["plan"]],
                    },
                )
            )
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=(
                f"Constructed {len(output.hypotheses)} candidate(s) and "
                f"{len(output.tasks)} completed analytic check(s) in one bounded pass."
            ),
            payload=payload,
            proposed_update=CognitiveStateUpdate(
                hypotheses_to_add=output.hypotheses,
                plan_tasks_to_add=output.tasks,
                execution_outputs_to_add=output.execution_outputs,
                trace_events_to_add=recovery_events,
            ),
        )

    return FunctionCapability(definition, execute)


def conclusion_checker_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
    max_output_tokens: int = 3200,
    timeout_seconds: float = 90.0,
    deterministic_only: bool = False,
) -> FunctionCapability:
    """Independently falsify, finalize, and reflect in one terminal pass."""
    if not 512 <= max_output_tokens <= 100_000:
        raise ValueError("conclusion checker max_output_tokens must be between 512 and 100000")
    if not 1.0 <= timeout_seconds <= 300.0:
        raise ValueError("conclusion checker timeout_seconds must be between 1 and 300")
    definition = CapabilityDefinition(
        name="arithmetic_conclusion_checker" if deterministic_only else "conclusion_checker",
        version="arithmetic_conclusion_checker@0.1.0"
        if deterministic_only
        else gateway.capability_version("fused_conclusion_checker@0.7.1"),
        supported_actions={CognitiveActionType.VERIFY},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=deterministic_only or approved_for_sensitive_data,
        estimated_cost=0.34,
        kind=CapabilityKind.DETERMINISTIC if deterministic_only else CapabilityKind.MODEL,
        max_model_calls=0 if deterministic_only else gateway.max_provider_attempts_per_capability,
        max_output_tokens=0 if deterministic_only else max_output_tokens,
        timeout_seconds=1.0 if deterministic_only else timeout_seconds,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        source_facts = dependency_source_facts(state)
        source_events: list[StateEvent] = []
        if is_simple_arithmetic(state):
            output = _arithmetic_conclusion_output(state)
            payload: JsonValue = {"procedure": "deterministic", "model_calls": 0}
        else:
            if deterministic_only:
                raise ValueError("deterministic arithmetic requires its recognized task shape")
            result = gateway.complete(
                capability=definition.name,
                instructions=(
                    "Act as an independent conclusion checker. Try to falsify the candidate "
                    "against canonical evidence, constraints, analytic outputs, and every success "
                    "criterion. Name at least one explicit check per criterion. If any check lacks "
                    "support, return a failing report with no answer and no reflection. Only after "
                    "all checks pass, return a concise evidence-bounded answer and reflection. "
                    "Reflection may generalize a procedure only within stated preconditions. "
                    "Verify the deliverable requested in raw_input. For a proposed plan, check "
                    "its factual coverage, constraint consistency, uncertainties, and future "
                    "verification steps; do not require executing those future steps now or "
                    "claim that they passed. Do require observed execution when the user requests "
                    "an implemented or tested outcome. Reject missing requested items and "
                    "unsupported feasibility claims; accurately labeled conditional proposals "
                    "are not claims of demonstrated feasibility. In report_metadata.open_questions, "
                    "list up to eight concrete unresolved questions or conditions remaining after "
                    "this deliverable, including unknown environment choices and unverified future "
                    "feasibility. Keep these consistent with the answer. They do not block a "
                    "requested conditional proposal, but they must remain visible to its reader. "
                    "Use an empty list when none remain. When a failed check requires missing "
                    "PUBLIC reference knowledge, return up to two public_research_needs with "
                    "a zero-based failed_check_index and a specific public-source question. "
                    "This requests research, not a successful check. Do not ask the user for "
                    "public publications the runtime can research. Never classify private logs, "
                    "local state, authorization, or proof of actual execution as public knowledge. "
                    "Public references cannot prove those requirements. Leave the list empty "
                    "for those failures or when verification_research_requested already exists. "
                    "After verification_research_analyzed, use its current_task_ids as the "
                    "revised analysis; the earlier tasks and verdict remain historical. "
                    "Check every reported measurement's value, sign, central-value unit and "
                    "uncertainty unit against raw source excerpts. An uncertainty can have a "
                    "different unit from its central value; never inherit the central unit "
                    "without checking. Do not describe numbers as rounding-compatible until "
                    "their units, observation dates and measurement definitions are aligned. "
                    + INSTRUCTIONS
                ),
                output_type=ConclusionCheckOutput,
                state=state,
                max_output_tokens=max_output_tokens,
                total_timeout_seconds=definition.timeout_seconds,
                context=source_facts.context(),
            )
            output = result.output
            payload = {
                "provider": result.provider,
                "model": result.model,
                "usage": result.usage.model_dump(mode="json"),
                "model_calls": result.model_calls,
                "route_attempts": [
                    {
                        "route": item.route,
                        "succeeded": item.succeeded,
                        "duration_ms": item.duration_ms,
                        "provider_attempts": item.provider_attempts,
                        "failure_kind": item.failure_kind,
                    }
                    for item in result.route_attempts
                ],
            }
        if source_facts.applicable:
            failures = source_facts.failures(output.final_answer or "")
            check = "Checked required dependency source-fact coverage against complete admitted snapshots (necessary coverage only)."
            source_events.append(
                StateEvent(
                    engine_name=definition.name,
                    event_type="dependency_source_fact_coverage_checked",
                    reasoning_mode=ReasoningMode.VERIFY,
                    summary="Source-fact coverage failed."
                    if failures
                    else "Required source facts are present; semantic correctness remains separately checked.",
                    metadata={
                        **source_facts.context(),
                        "passed": not failures,
                        "failures": list(failures),
                    },
                )
            )
            report = output.report
            if failures:
                output = ConclusionCheckOutput(
                    report=VerificationReport(
                        passed=False,
                        checks_run=[*report.checks_run, check],
                        failed_checks=[*report.failed_checks, *failures],
                        contradictions=report.contradictions,
                        confidence_delta=-0.2,
                        recommended_route="revise_analysis",
                    ),
                    public_research_needs=output.public_research_needs,
                )
            else:
                output = output.model_copy(
                    update={
                        "report": report.model_copy(
                            update={"checks_run": [*report.checks_run, check]}
                        )
                    }
                )
        if output.report.passed and output.final_answer:
            unit_failures = uncertainty_failures(state, output.final_answer)
            source_events.append(
                StateEvent(
                    engine_name=definition.name,
                    event_type="time_uncertainty_consistency_checked",
                    reasoning_mode=ReasoningMode.VERIFY,
                    summary="Explicit time uncertainty conflicts with its source."
                    if unit_failures
                    else "No parsed time-uncertainty conflict; broader measurement verification remains required.",
                    metadata={
                        "version": MEASUREMENT_VERSION,
                        "passed": not unit_failures,
                        "failures": list(unit_failures),
                        "rejected_answer": output.final_answer if unit_failures else None,
                    },
                )
            )
            if unit_failures:
                output = ConclusionCheckOutput(
                    report=VerificationReport(
                        passed=False,
                        checks_run=[
                            *output.report.checks_run,
                            "Compared explicit time uncertainty units with admitted source excerpts.",
                        ],
                        failed_checks=unit_failures,
                        contradictions=output.report.contradictions,
                        confidence_delta=-0.2,
                        recommended_route="Revise the analysis using the measurement units in the admitted raw source excerpts.",
                    )
                )
        if output.report.passed and output.final_answer and output.report_metadata is not None:
            source_events.append(
                report_metadata_event(
                    answer=output.final_answer,
                    metadata=output.report_metadata,
                    engine_name=definition.name,
                )
            )
        research_gaps, research_events = research_update(state, output, action_id=action.id)
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=(
                "Conclusion check passed all declared criteria."
                if output.report.passed
                else "Conclusion check found missing support or a failed criterion."
            ),
            payload=payload,
            proposed_update=CognitiveStateUpdate(
                verification=output.report,
                gaps_to_add=research_gaps,
                final_answer=output.final_answer,
                reflection=output.reflection,
                trace_events_to_add=source_events
                + research_events
                + (
                    [
                        StateEvent(
                            engine_name=definition.name,
                            event_type="verified_reflection_recorded",
                            reasoning_mode=ReasoningMode.REFLECT,
                            summary=output.reflection.outcome_summary,
                            metadata=output.reflection.model_dump(mode="json"),
                        )
                    ]
                    if output.reflection is not None
                    else []
                ),
            ),
        )

    return FunctionCapability(definition, execute)


def on_demand_cognitive_capabilities(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
    max_output_tokens_per_call: int | None = None,
    timeout_seconds_per_call: float | None = None,
    trusted_evidence_attesters: tuple[TrustedEvidenceAttester, ...] = (),
) -> tuple[FunctionCapability, ...]:
    """Return the minimum zero/one/two-call Chapter 13-D semantic suite."""
    return (
        task_gap_detector_capability(),
        artifact_lookup_procedure_capability(),
        attested_evidence_procedure_capability(trusted_evidence_attesters),
        verifier_factory_capability(),
        deliberator_capability(gateway, deterministic_only=True),
        conclusion_checker_capability(gateway, deterministic_only=True),
        deliberator_capability(
            gateway,
            approved_for_sensitive_data=approved_for_sensitive_data,
            max_output_tokens=max_output_tokens_per_call or 6000,
            timeout_seconds=timeout_seconds_per_call or 90.0,
        ),
        conclusion_checker_capability(
            gateway,
            approved_for_sensitive_data=approved_for_sensitive_data,
            max_output_tokens=max_output_tokens_per_call or 3200,
            timeout_seconds=timeout_seconds_per_call or 90.0,
        ),
    )
