"""Production model-backed proposals governed by the cognitive controller."""

from __future__ import annotations

from pydantic import JsonValue

from app.cognition.arithmetic_pack import (
    arithmetic_gap_output,
    arithmetic_hypothesis_output,
    arithmetic_plan_output,
    arithmetic_reflection_output,
    arithmetic_verification_output,
    is_simple_arithmetic,
)
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
from app.cognition.model_contracts import (
    AnalysisExecutionOutput,
    ConclusionCheckOutput,
    DeliberationCapabilityOutput,
    GapDetectionOutput,
    HypothesisGenerationOutput,
    PlanGenerationOutput,
    ReflectionCapabilityOutput,
    VerificationCapabilityOutput,
)
from app.cognition.model_gateway import CognitiveModelGateway, ModelCapabilityResult
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import ContractModel, ReasoningMode, RiskLevel


def _arithmetic_deliberation_output(state: PolyaState) -> DeliberationCapabilityOutput:
    from app.cognition.local_capabilities import calculate_binary_expression

    hypothesis = arithmetic_hypothesis_output(state)
    plan = arithmetic_plan_output(state)
    tasks = [task.model_copy(update={"tool_name": "deliberator"}) for task in plan.tasks]
    outputs: list[ExecutionOutput] = []
    for task in tasks:
        expression = str(task.params.get("expression", state["raw_input"]))
        normalized, result = calculate_binary_expression(expression)
        outputs.append(
            ExecutionOutput(
                task_id=task.id,
                summary=f"Independently recalculated {normalized} = {result}.",
                output={"expression": normalized, "result": result},
            )
        )
    return DeliberationCapabilityOutput(
        hypotheses=hypothesis.hypotheses,
        tasks=tasks,
        execution_outputs=outputs,
    )


def _arithmetic_conclusion_output(state: PolyaState) -> ConclusionCheckOutput:
    verified = arithmetic_verification_output(state)
    reflected = arithmetic_reflection_output(state)
    return ConclusionCheckOutput(
        report=verified.report,
        final_answer=verified.final_answer,
        reflection=reflected.reflection if verified.report.passed else None,
    )


def _payload[PayloadT: ContractModel](
    result: ModelCapabilityResult[PayloadT],
) -> JsonValue:
    return {
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


def gap_detector_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
    available_sources: str | None = None,
) -> FunctionCapability:
    """Identify blocking missing knowledge without selecting an acquisition action."""
    definition = CapabilityDefinition(
        name="gap_detector",
        version=gateway.capability_version("model_gap_detector@0.1.0"),
        supported_actions={CognitiveActionType.DETECT_GAPS},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=approved_for_sensitive_data,
        timeout_seconds=90.0,
        estimated_cost=0.15,
        kind=CapabilityKind.MODEL,
        max_model_calls=gateway.max_provider_attempts_per_capability,
        max_output_tokens=1800,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        result: ModelCapabilityResult[GapDetectionOutput] | None = None
        if is_simple_arithmetic(state):
            output = arithmetic_gap_output(state)
        else:
            result = gateway.complete(
                capability=definition.name,
                instructions=(
                    "Compare the goal and every success criterion with knowns, evidence, and "
                    "available outputs. Return only missing knowledge that blocks verification. "
                    "Do not create optional curiosity. Each gap must explain why it matters and "
                    "name a suggested source such as calculator, human input, local artifact, "
                    "measurement, experiment, memory, or official web source. Only suggest a "
                    "source that exists in AVAILABLE_SOURCES. If the structured problem contains "
                    "unknowns, cover each material unknown.\nAVAILABLE_SOURCES:\n"
                    f"{available_sources or 'calculator; human input; model analysis'}"
                ),
                output_type=GapDetectionOutput,
                state=state,
                total_timeout_seconds=definition.timeout_seconds,
            )
            output = result.output
        problem = state["structured_problem"]
        if problem is not None and problem.unknowns and not output.gaps:
            raise ValueError("gap detector omitted unresolved structured unknowns")
        event = StateEvent(
            engine_name=definition.name,
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary=f"Identified {len(output.gaps)} blocking knowledge gap(s).",
            metadata={"status": "ok", "gap_count": len(output.gaps)},
        )
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=event.summary,
            payload=_payload(result) if result is not None else {"procedure": "deterministic"},
            proposed_update=CognitiveStateUpdate(
                gaps_to_add=output.gaps,
                trace_events_to_add=[event],
            ),
        )

    return FunctionCapability(definition, execute)


def hypothesis_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
) -> FunctionCapability:
    """Generate falsifiable alternatives after blocking gaps are resolved."""
    definition = CapabilityDefinition(
        name="reasoner",
        version=gateway.capability_version("model_hypothesis_reasoner@0.1.0"),
        supported_actions={CognitiveActionType.HYPOTHESIZE},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=approved_for_sensitive_data,
        timeout_seconds=90.0,
        estimated_cost=0.2,
        kind=CapabilityKind.MODEL,
        max_model_calls=gateway.max_provider_attempts_per_capability,
        max_output_tokens=2400,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        result: ModelCapabilityResult[HypothesisGenerationOutput] | None = None
        if is_simple_arithmetic(state):
            output = arithmetic_hypothesis_output(state)
        else:
            result = gateway.complete(
                capability=definition.name,
                instructions=(
                    "Generate distinct candidate explanations or solution paths. For a uniquely "
                    "determined calculation one candidate is enough; otherwise provide at least "
                    "two materially different candidates. Every candidate must state expected "
                    "signals, verification checks, and falsification criteria. Do not mark a "
                    "candidate verified. Evidence may suggest; it does not decide without checks."
                ),
                output_type=HypothesisGenerationOutput,
                state=state,
                max_output_tokens=2400,
                total_timeout_seconds=definition.timeout_seconds,
            )
            output = result.output
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=f"Generated {len(output.hypotheses)} testable candidate(s).",
            payload=_payload(result) if result is not None else {"procedure": "deterministic"},
            proposed_update=CognitiveStateUpdate(hypotheses_to_add=output.hypotheses),
        )

    return FunctionCapability(definition, execute)


def planner_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
    available_execution_tools: tuple[str, ...] = ("calculator", "executor"),
    max_plan_tasks: int = 6,
) -> FunctionCapability:
    """Translate hypotheses into bounded executable checks."""
    definition = CapabilityDefinition(
        name="planner",
        version=gateway.capability_version("model_planner@0.1.0"),
        supported_actions={CognitiveActionType.PLAN, CognitiveActionType.REPLAN},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=approved_for_sensitive_data,
        timeout_seconds=90.0,
        estimated_cost=0.15,
        kind=CapabilityKind.MODEL,
        max_model_calls=gateway.max_provider_attempts_per_capability,
        max_output_tokens=2200,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        result: ModelCapabilityResult[PlanGenerationOutput] | None = None
        if is_simple_arithmetic(state):
            output = arithmetic_plan_output(state)
        else:
            result = gateway.complete(
                capability=definition.name,
                instructions=(
                    "Create the smallest plan that can test the surviving candidates and every "
                    f"success criterion using at most {max_plan_tasks} task(s). "
                    "success criterion. tool_name MUST be one of AVAILABLE_EXECUTION_TOOLS. "
                    "Use calculator for binary arithmetic only when calculator appears in that "
                    "list, and put the expression in params. When arithmetic evidence was already "
                    "acquired but calculator is not an execution tool, use executor to check the "
                    "recorded evidence; do not name calculator. Use python_sandbox only for bounded "
                    "Python execution; params must contain code and may contain a list of assert "
                    "tests. Use measurement only for a supplied CSV/JSON table; params must "
                    "contain source and one read-only SELECT statement in sql. Otherwise "
                    "use simulator only with simulation_spec containing explicit initial_value, "
                    "periods, scenario_rates, optional threshold, and unit. Use experiment only "
                    "with experiment_spec containing explicit randomized independent control and "
                    "treatment observations, metric, desired_direction, and minimum_effect. "
                    "Otherwise use executor. Do not plan external side effects or select an "
                    "acquisition tool merely because it appears in prior evidence. Select only "
                    "from AVAILABLE_EXECUTION_TOOLS: "
                    f"{', '.join(available_execution_tools)}."
                ),
                output_type=PlanGenerationOutput,
                state=state,
                max_output_tokens=2200,
                total_timeout_seconds=definition.timeout_seconds,
            )
            output = result.output
        unsupported = [
            task.tool_name
            for task in output.tasks
            if task.tool_name not in set(available_execution_tools)
        ]
        if unsupported:
            raise ValueError("planner selected an undeclared execution capability")
        if len(output.tasks) > max_plan_tasks:
            raise ValueError("planner exceeded the declared plan-task budget")
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=f"Created {len(output.tasks)} bounded plan task(s).",
            payload=_payload(result) if result is not None else {"procedure": "deterministic"},
            proposed_update=CognitiveStateUpdate(plan_tasks_to_add=output.tasks),
        )

    return FunctionCapability(definition, execute)


def analysis_executor_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
) -> FunctionCapability:
    """Execute one low-risk analytic plan task against recorded state only."""
    definition = CapabilityDefinition(
        name="executor",
        version=gateway.capability_version("model_analysis_executor@0.1.0"),
        supported_actions={CognitiveActionType.EXECUTE},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=approved_for_sensitive_data,
        timeout_seconds=90.0,
        estimated_cost=0.15,
        kind=CapabilityKind.MODEL,
        max_model_calls=gateway.max_provider_attempts_per_capability,
        max_output_tokens=1800,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        result = gateway.complete(
            capability=definition.name,
            instructions=(
                f"Execute only the plan task whose id is {action.target!r}, using recorded "
                "state. Produce an inspectable analytic output. Do not claim external actions, "
                "search, measurements, tests, or observations that are not already present."
            ),
            output_type=AnalysisExecutionOutput,
            state=state,
            total_timeout_seconds=definition.timeout_seconds,
        )
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=result.output.summary,
            payload=_payload(result),
            proposed_update=CognitiveStateUpdate(
                execution_outputs_to_add=[
                    ExecutionOutput(
                        task_id=action.target,
                        summary=result.output.summary,
                        output=result.output.output,
                    )
                ]
            ),
        )

    return FunctionCapability(definition, execute)


def verifier_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
) -> FunctionCapability:
    """Try to falsify the proposed result against evidence and success criteria."""
    definition = CapabilityDefinition(
        name="verifier",
        version=gateway.capability_version("model_verifier@0.1.0"),
        supported_actions={CognitiveActionType.VERIFY},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=approved_for_sensitive_data,
        timeout_seconds=90.0,
        estimated_cost=0.2,
        kind=CapabilityKind.MODEL,
        max_model_calls=gateway.max_provider_attempts_per_capability,
        max_output_tokens=2200,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        result: ModelCapabilityResult[VerificationCapabilityOutput] | None = None
        if is_simple_arithmetic(state):
            output = arithmetic_verification_output(state)
        else:
            result = gateway.complete(
                capability=definition.name,
                instructions=(
                    "Try to disprove the candidate outcome. Run and name at least one explicit "
                    "check for every success criterion. A check may use only recorded evidence or "
                    "execution outputs. If any criterion lacks support, a contradiction remains, "
                    "or a claimed external observation was not performed, passed must be false and "
                    "final_answer must be null. Otherwise return a concise conclusion that separates "
                    "what is established from remaining limits."
                ),
                output_type=VerificationCapabilityOutput,
                state=state,
                max_output_tokens=2200,
                total_timeout_seconds=definition.timeout_seconds,
            )
            output = result.output
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=(
                "Verification passed all declared checks."
                if output.report.passed
                else "Verification found missing support or a failed check."
            ),
            payload=_payload(result) if result is not None else {"procedure": "deterministic"},
            proposed_update=CognitiveStateUpdate(
                verification=output.report,
                final_answer=output.final_answer,
            ),
        )

    return FunctionCapability(definition, execute)


def reflector_capability(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
) -> FunctionCapability:
    """Extract reusable lessons only from an accepted verified run."""
    definition = CapabilityDefinition(
        name="reflector",
        version=gateway.capability_version("model_reflector@0.1.0"),
        supported_actions={CognitiveActionType.REFLECT},
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=approved_for_sensitive_data,
        timeout_seconds=90.0,
        estimated_cost=0.1,
        kind=CapabilityKind.MODEL,
        max_model_calls=gateway.max_provider_attempts_per_capability,
        max_output_tokens=1800,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        verification = state["verification"]
        if verification is None or not verification.passed:
            raise ValueError("reflection requires accepted passing verification")
        result: ModelCapabilityResult[ReflectionCapabilityOutput] | None = None
        if is_simple_arithmetic(state):
            output = arithmetic_reflection_output(state)
        else:
            result = gateway.complete(
                capability=definition.name,
                instructions=(
                    "Reflect only on the verified run. Record specific successes, failures, "
                    "reusable lessons, and follow-up limits. Do not generalize beyond the evidence."
                ),
                output_type=ReflectionCapabilityOutput,
                state=state,
                total_timeout_seconds=definition.timeout_seconds,
            )
            output = result.output
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary="Extracted bounded lessons from the verified run.",
            payload=_payload(result) if result is not None else {"procedure": "deterministic"},
            proposed_update=CognitiveStateUpdate(
                reflection=output.reflection,
                trace_events_to_add=[
                    StateEvent(
                        engine_name=definition.name,
                        event_type="reflection_recorded",
                        reasoning_mode=ReasoningMode.REFLECT,
                        summary=output.reflection.outcome_summary,
                        metadata=output.reflection.model_dump(mode="json"),
                    )
                ],
            ),
        )

    return FunctionCapability(definition, execute)


def model_reasoning_capabilities(
    gateway: CognitiveModelGateway,
    *,
    approved_for_sensitive_data: bool = False,
    available_sources: str | None = None,
    available_execution_tools: tuple[str, ...] = ("calculator", "executor"),
    max_plan_tasks: int = 6,
) -> tuple[FunctionCapability, ...]:
    """Return the minimum controller-governed model capability suite."""
    return (
        gap_detector_capability(
            gateway,
            approved_for_sensitive_data=approved_for_sensitive_data,
            available_sources=available_sources,
        ),
        hypothesis_capability(
            gateway,
            approved_for_sensitive_data=approved_for_sensitive_data,
        ),
        planner_capability(
            gateway,
            approved_for_sensitive_data=approved_for_sensitive_data,
            available_execution_tools=available_execution_tools,
            max_plan_tasks=max_plan_tasks,
        ),
        analysis_executor_capability(
            gateway,
            approved_for_sensitive_data=approved_for_sensitive_data,
        ),
        verifier_capability(
            gateway,
            approved_for_sensitive_data=approved_for_sensitive_data,
        ),
        reflector_capability(
            gateway,
            approved_for_sensitive_data=approved_for_sensitive_data,
        ),
    )
