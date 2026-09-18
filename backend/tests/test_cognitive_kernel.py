"""End-to-end tests for the bounded cognitive control cycle."""

from __future__ import annotations

from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveKernel,
    CognitiveObservation,
    CognitiveRunStatus,
    CognitiveRuntime,
    CognitiveSessionRunner,
    CognitiveStateUpdate,
    FunctionCapability,
    ObservationStatus,
    constraint_discovery_capability,
    problem_representation_capability,
)
from app.engines import ConstraintDiscoveryEngine, ProblemRepresentationEngine
from app.graph.state import ExecutionOutput, PolyaState, StateEvent, create_initial_state
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    KnowledgeGap,
    PlanTask,
    PriorityLevel,
    ProductMode,
    ReasoningMode,
    Reflection,
    RiskLevel,
    StructuredProblem,
    VerificationReport,
)
from app.problem_understanding import ProblemUnderstandingOutput


def _math_state() -> PolyaState:
    state = create_initial_state(
        "Solve 2x + 4 = 10 and verify the result.",
        session_id="math-control-proof",
        max_iterations=10,
    )
    state["structured_problem"] = StructuredProblem(
        core_question="What value of x satisfies 2x + 4 = 10?",
        problem_type="mathematical_reasoning",
        knowns=["The equation is 2x + 4 = 10."],
        unknowns=["the value of x"],
        constraints=["Use exact arithmetic."],
        success_criteria=["Substitution makes both sides equal."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description="the value of x",
            gap_type="numeric_computation",
            priority=PriorityLevel.CRITICAL,
            why_needed="The requested solution cannot be verified without the value.",
            suggested_source="calculator",
        )
    ]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints were discovered before this focused kernel state.",
            metadata={"status": "ok"},
        )
    ]
    return state


def _definition(
    name: str,
    *actions: CognitiveActionType,
) -> CapabilityDefinition:
    return CapabilityDefinition(
        name=name,
        version="proof-v1",
        supported_actions=set(actions),
        estimated_cost=0.05,
    )


def _mark_constraint_discovery_complete(state: PolyaState) -> None:
    state["events"] = [
        *state["events"],
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints were discovered before this focused test state.",
            metadata={"status": "ok"},
        ),
    ]


def _successful_observation(
    definition: CapabilityDefinition,
    action: CognitiveActionCandidate,
    *,
    summary: str,
    update: CognitiveStateUpdate,
    evidence: list[EvidenceItem] | None = None,
) -> CognitiveObservation:
    return CognitiveObservation(
        action_id=action.id,
        capability=definition.name,
        capability_version=definition.version,
        status=ObservationStatus.SUCCEEDED,
        summary=summary,
        evidence=evidence or [],
        proposed_update=update,
    )


def _complete_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    calculator = _definition("calculator", CognitiveActionType.CALCULATE)

    def calculate(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return _successful_observation(
            calculator,
            action,
            summary="Solved the equation exactly and exposed the arithmetic.",
            evidence=[
                EvidenceItem(
                    source_type="deterministic_calculator",
                    source_uri="calculator://2x-plus-4-equals-10",
                    claim="Solving 2x + 4 = 10 gives x = 3.",
                    raw_excerpt="2x = 6; x = 3",
                    reliability_score=1.0,
                    relevance_score=1.0,
                )
            ],
            update=CognitiveStateUpdate(
                knowns_to_add=["Exact arithmetic gives x = 3."],
                unknowns_to_resolve=["the value of x"],
                resolved_gap_targets=["the value of x"],
            ),
        )

    registry.register(FunctionCapability(calculator, calculate))

    reasoner = _definition(
        "reasoner",
        CognitiveActionType.DECOMPOSE,
        CognitiveActionType.HYPOTHESIZE,
    )

    def hypothesize(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        if action.action_type is CognitiveActionType.DECOMPOSE:
            return _successful_observation(
                reasoner,
                action,
                summary="Converted the unknown into a calculator-ready gap.",
                update=CognitiveStateUpdate(
                    gaps_to_add=[
                        KnowledgeGap(
                            description="the value of x",
                            gap_type="numeric_computation",
                            priority=PriorityLevel.CRITICAL,
                            why_needed="The exact value is required for the solution.",
                            suggested_source="calculator",
                        )
                    ]
                ),
            )
        return _successful_observation(
            reasoner,
            action,
            summary="Generated a falsifiable candidate solution.",
            update=CognitiveStateUpdate(
                hypotheses_to_add=[
                    Hypothesis(
                        statement="x = 3 satisfies the equation.",
                        mechanism="Isolate x and substitute the result.",
                        origin=HypothesisOrigin.DIRECT_REASONING,
                        expected_signals=["2(3) + 4 equals 10"],
                        verification_checks=["Substitute x = 3."],
                        falsification_criteria=["The substituted sides differ."],
                    )
                ]
            ),
        )

    registry.register(FunctionCapability(reasoner, hypothesize))

    planner = _definition("planner", CognitiveActionType.PLAN)

    def plan(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return _successful_observation(
            planner,
            action,
            summary="Planned an independent substitution check.",
            update=CognitiveStateUpdate(
                plan_tasks_to_add=[
                    PlanTask(
                        id="substitute-x",
                        action="Evaluate 2(3) + 4 and compare it with 10.",
                        tool_name="executor",
                        expected_output="Both sides evaluate to 10.",
                        risk_level=RiskLevel.LOW,
                    )
                ]
            ),
        )

    registry.register(FunctionCapability(planner, plan))

    executor = _definition("executor", CognitiveActionType.EXECUTE)

    def execute(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return _successful_observation(
            executor,
            action,
            summary="Executed the planned substitution check.",
            update=CognitiveStateUpdate(
                execution_outputs_to_add=[
                    ExecutionOutput(
                        task_id="substitute-x",
                        summary="2(3) + 4 = 10.",
                        output={"left": 10, "right": 10},
                    )
                ]
            ),
        )

    registry.register(FunctionCapability(executor, execute))

    verifier = _definition("verifier", CognitiveActionType.VERIFY)

    def verify(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        output = state["execution_outputs"][0].output
        passed = output == {"left": 10, "right": 10}
        return _successful_observation(
            verifier,
            action,
            summary="Verified the solution independently by substitution.",
            update=CognitiveStateUpdate(
                verification=VerificationReport(
                    passed=passed,
                    checks_run=["Compared the substituted left side with the right side."],
                    failed_checks=[] if passed else ["The sides did not match."],
                    confidence_delta=0.2 if passed else -0.5,
                ),
                final_answer="x = 3" if passed else None,
            ),
        )

    registry.register(FunctionCapability(verifier, verify))

    reflector = _definition("reflector", CognitiveActionType.REFLECT)

    def reflect(
        action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        return _successful_observation(
            reflector,
            action,
            summary="Recorded the verified solve-and-substitute strategy.",
            update=CognitiveStateUpdate(
                reflection=Reflection(
                    outcome_summary="The equation was solved and independently verified.",
                    what_worked=["Isolate the variable, then substitute."],
                    reusable_lessons=["Verify algebraic solutions by substitution."],
                    strategy_notes=["solve_then_substitute"],
                )
            ),
        )

    registry.register(FunctionCapability(reflector, reflect))
    return registry


def test_kernel_runs_observe_decide_act_update_verify_reflect_end_to_end() -> None:
    result = CognitiveKernel(_complete_registry()).run(_math_state(), max_cycles=10)

    assert result.status is CognitiveRunStatus.COMPLETED
    assert result.state["final_answer"] == "x = 3"
    assert result.state["verification"] is not None
    assert result.state["verification"].passed
    assert result.state["reflection"] is not None
    assert result.state["gaps"][0].filled
    assert result.state["structured_problem"] is not None
    assert result.state["structured_problem"].unknowns == []
    assert [decision.selected.action_type for decision in result.decisions] == [
        CognitiveActionType.CALCULATE,
        CognitiveActionType.HYPOTHESIZE,
        CognitiveActionType.PLAN,
        CognitiveActionType.EXECUTE,
        CognitiveActionType.VERIFY,
        CognitiveActionType.REFLECT,
        CognitiveActionType.STOP,
    ]
    assert any(event.event_type == "cognitive_action_decision" for event in result.state["events"])
    observation_events = [
        event for event in result.state["events"] if event.event_type == "capability_observation"
    ]
    assert observation_events
    assert all(
        isinstance(event.metadata.get("duration_ms"), int | float)
        and event.metadata["duration_ms"] >= 0
        for event in observation_events
    )


def test_raw_input_runs_through_real_representation_adapter_and_kernel() -> None:
    representation = ProblemUnderstandingOutput(
        literal_framing="Solve 2x + 4 = 10 and verify the result.",
        deeper_framing="Find the exact value and independently check it.",
        goal="Find and verify the value of x.",
        problem_type="mathematical_reasoning",
        domain="mathematics",
        selected_mode=ProductMode.EXPLORE,
        mode_confidence=1.0,
        mode_selection_reason="This is a fully specified exact equation.",
        given=["The equation is 2x + 4 = 10."],
        unknown=["the value of x"],
        constraints=["Use exact arithmetic."],
        success_criteria=["Substitution makes both sides equal."],
        required_data_sources=["deterministic calculator"],
    )
    client = FakeLLMClient(
        [
            LLMResponse(
                provider="fake",
                model="fake-representation-model",
                text=representation.model_dump_json(),
                finish_reason="stop",
                usage=LLMTokenUsage(input_tokens=80, output_tokens=40),
            )
        ]
    )
    engine = ProblemRepresentationEngine(
        client=client,
        model="fake-representation-model",
        fallback=lambda *args, **kwargs: None,
    )
    registry = _complete_registry()
    registry.register(problem_representation_capability(engine))
    registry.register(constraint_discovery_capability(ConstraintDiscoveryEngine()))

    result = CognitiveRuntime(registry).run_problem(
        "Solve 2x + 4 = 10 and verify the result.",
        session_id="raw-input-cognitive-runtime",
        max_cycles=12,
    )

    assert result.status is CognitiveRunStatus.COMPLETED
    assert result.state["final_answer"] == "x = 3"
    assert [decision.selected.action_type for decision in result.decisions] == [
        CognitiveActionType.INTERPRET,
        CognitiveActionType.DISCOVER_CONSTRAINTS,
        CognitiveActionType.DECOMPOSE,
        CognitiveActionType.CALCULATE,
        CognitiveActionType.HYPOTHESIZE,
        CognitiveActionType.PLAN,
        CognitiveActionType.EXECUTE,
        CognitiveActionType.VERIFY,
        CognitiveActionType.REFLECT,
        CognitiveActionType.STOP,
    ]
    assert len(client.requests) == 1
    assert any(event.event_type == "framing_selected" for event in result.state["events"])


def test_representation_adapter_preserves_clarification_and_needs_input() -> None:
    engine = ProblemRepresentationEngine(
        client=FakeLLMClient([]),
        model="fake-representation-model",
    )
    registry = CapabilityRegistry()
    registry.register(problem_representation_capability(engine))

    result = CognitiveRuntime(registry).run_problem(
        "Fix it.",
        session_id="raw-input-needs-clarification",
        max_cycles=3,
    )

    assert result.status is CognitiveRunStatus.NEEDS_INPUT
    assert result.state["structured_problem"] is None
    assert result.state["final_answer"] is None
    assert result.observations[0].failure_kind == "human_input_required"
    assert any(event.event_type == "framing_selected" for event in result.state["events"])


def test_cognitive_session_runner_exports_engine_questions_for_persistence() -> None:
    engine = ProblemRepresentationEngine(
        client=FakeLLMClient([]),
        model="fake-representation-model",
    )
    registry = CapabilityRegistry()
    registry.register(problem_representation_capability(engine))
    runner = CognitiveSessionRunner(CognitiveRuntime(registry), max_cycles=3)

    execution = runner("Fix it.", session_id="persisted-clarification")

    assert execution.awaiting_user_input
    assert execution.clarifying_questions == (
        "Which system, artifact, or decision should PolyaBrain investigate?",
        "What observed result and measurable success condition should guide the investigation?",
    )
    assert execution.state["final_answer"] is None


def test_cognitive_session_runner_rehydrates_prior_evidence_on_resume() -> None:
    engine = ProblemRepresentationEngine(
        client=FakeLLMClient([]),
        model="fake-representation-model",
    )
    registry = CapabilityRegistry()
    registry.register(problem_representation_capability(engine))
    prior = EvidenceItem(
        source_type="evaluated_web_source",
        source_uri="https://example.com/prior",
        claim="The earlier source established a relevant constraint.",
        raw_excerpt="A relevant constraint was established.",
        reliability_score=0.8,
        relevance_score=0.9,
    )
    loaded_sessions: list[str] = []

    def load_evidence(session_id: str) -> list[EvidenceItem]:
        loaded_sessions.append(session_id)
        return [prior]

    runner = CognitiveSessionRunner(
        CognitiveRuntime(registry),
        max_cycles=3,
        evidence_loader=load_evidence,
    )

    execution = runner("Fix it.", session_id="resume-with-evidence")

    assert loaded_sessions == ["resume-with-evidence"]
    assert execution.state["evidence"] == [prior]


def test_failed_search_changes_the_next_action_instead_of_repeating() -> None:
    state = create_initial_state(
        "Find the current behavior from an authoritative source.",
        session_id="recovery-proof",
        max_iterations=3,
    )
    state["structured_problem"] = StructuredProblem(
        core_question="What is the current supported behavior?",
        problem_type="technical_research",
        unknowns=["the current supported behavior"],
        success_criteria=["Use an authoritative source."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description="the current supported behavior",
            gap_type="current_external_fact",
            priority=PriorityLevel.HIGH,
            why_needed="The answer changes over time.",
            suggested_source="official web source",
        )
    ]
    _mark_constraint_discovery_complete(state)
    registry = CapabilityRegistry()
    web = _definition("web_search", CognitiveActionType.SEARCH)
    registry.register(
        FunctionCapability(
            web,
            lambda action, _state: CognitiveObservation(
                action_id=action.id,
                capability=web.name,
                capability_version=web.version,
                status=ObservationStatus.FAILED,
                summary="The search provider returned no usable result.",
                failure_kind="no_results",
            ),
        )
    )
    inspector = _definition("inspector", CognitiveActionType.INSPECT)
    registry.register(
        FunctionCapability(
            inspector,
            lambda action, _state: _successful_observation(
                inspector,
                action,
                summary="Found the authoritative bundled specification.",
                update=CognitiveStateUpdate(
                    knowns_to_add=["The bundled specification states the current behavior."],
                    unknowns_to_resolve=["the current supported behavior"],
                    resolved_gap_targets=["the current supported behavior"],
                ),
            ),
        )
    )

    result = CognitiveKernel(registry).run(state, max_cycles=2)

    assert [decision.selected.action_type for decision in result.decisions] == [
        CognitiveActionType.SEARCH,
        CognitiveActionType.INSPECT,
    ]
    assert result.observations[0].status is ObservationStatus.FAILED
    assert result.observations[1].status is ObservationStatus.SUCCEEDED
    assert result.state["gaps"][0].filled


def test_blocked_clarification_returns_needs_input_without_fake_progress() -> None:
    state = create_initial_state(
        "Choose the best option.",
        session_id="clarification-proof",
    )
    state["structured_problem"] = StructuredProblem(
        core_question="Which option is best?",
        problem_type="ambiguous_input",
        unknowns=["the user's success criterion"],
        success_criteria=["Use the user's actual preference."],
    )
    state["gaps"] = [
        KnowledgeGap(
            description="the user's success criterion",
            gap_type="missing_user_input",
            priority=PriorityLevel.CRITICAL,
            why_needed="Different preferences produce different correct answers.",
            suggested_source="human input",
        )
    ]
    _mark_constraint_discovery_complete(state)
    human = _definition("human_input", CognitiveActionType.CLARIFY)
    registry = CapabilityRegistry()
    registry.register(
        FunctionCapability(
            human,
            lambda action, _state: CognitiveObservation(
                action_id=action.id,
                capability=human.name,
                capability_version=human.version,
                status=ObservationStatus.BLOCKED,
                summary="A user answer is required before continuing.",
                failure_kind="human_input_required",
            ),
        )
    )

    result = CognitiveKernel(registry).run(state)

    assert result.status is CognitiveRunStatus.NEEDS_INPUT
    assert result.state["final_answer"] is None
    assert not result.state["gaps"][0].filled


def test_capability_exception_is_sanitized_and_does_not_mutate_state() -> None:
    state = _math_state()
    calculator = _definition("calculator", CognitiveActionType.CALCULATE)
    registry = CapabilityRegistry()

    def fail(
        _action: CognitiveActionCandidate,
        _state: PolyaState,
    ) -> CognitiveObservation:
        raise RuntimeError("secret detail must not enter the trace")

    registry.register(FunctionCapability(calculator, fail))

    result = CognitiveKernel(registry).run(state, max_cycles=1)

    assert result.observations[0].status is ObservationStatus.FAILED
    assert result.observations[0].failure_kind == "capability_exception"
    assert "secret detail" not in result.observations[0].summary
    assert not result.state["gaps"][0].filled


def test_failed_verification_is_invalidated_then_rerun_after_replan() -> None:
    state = _math_state()
    state["structured_problem"] = state["structured_problem"].model_copy(
        update={"knowns": ["Candidate x = 3."], "unknowns": []}
    )
    state["gaps"] = [state["gaps"][0].model_copy(update={"filled": True})]
    state["hypotheses"] = [
        Hypothesis(
            statement="x = 3 satisfies the equation.",
            mechanism="Isolate x.",
            origin=HypothesisOrigin.DIRECT_REASONING,
            expected_signals=["Substitution succeeds."],
            verification_checks=["Substitute x = 3."],
            falsification_criteria=["The two sides differ."],
        )
    ]
    state["plan"] = [
        PlanTask(
            id="initial-check",
            action="Run the initial substitution check.",
            tool_name="executor",
            expected_output="A pass or contradiction.",
        )
    ]
    state["execution_outputs"] = [
        ExecutionOutput(
            task_id="initial-check",
            summary="The initial check exposed a contradiction.",
            output={"passed": False},
        )
    ]

    registry = CapabilityRegistry()
    verifier = _definition("verifier", CognitiveActionType.VERIFY)

    def verify(
        action: CognitiveActionCandidate,
        current: PolyaState,
    ) -> CognitiveObservation:
        passed = current["execution_outputs"][-1].output == {"passed": True}
        return _successful_observation(
            verifier,
            action,
            summary="Ran an independent substitution check.",
            update=CognitiveStateUpdate(
                verification=VerificationReport(
                    passed=passed,
                    checks_run=["Compared both sides."],
                    failed_checks=[] if passed else ["The two sides differed."],
                    confidence_delta=0.2 if passed else -0.5,
                ),
                final_answer="x = 3" if passed else None,
            ),
        )

    registry.register(FunctionCapability(verifier, verify))
    planner = _definition("planner", CognitiveActionType.REPLAN)
    registry.register(
        FunctionCapability(
            planner,
            lambda action, _state: _successful_observation(
                planner,
                action,
                summary="Created a materially different verification task.",
                update=CognitiveStateUpdate(
                    plan_tasks_to_add=[
                        PlanTask(
                            id="corrected-check",
                            action="Recompute and substitute using exact arithmetic.",
                            tool_name="executor",
                            expected_output="The corrected independent result.",
                        )
                    ]
                ),
            ),
        )
    )
    executor = _definition("executor", CognitiveActionType.EXECUTE)
    registry.register(
        FunctionCapability(
            executor,
            lambda action, _state: _successful_observation(
                executor,
                action,
                summary="Executed the corrected independent check.",
                update=CognitiveStateUpdate(
                    execution_outputs_to_add=[
                        ExecutionOutput(
                            task_id=action.target,
                            summary="The corrected check passed.",
                            output={"passed": True},
                        )
                    ]
                ),
            ),
        )
    )
    reflector = _definition("reflector", CognitiveActionType.REFLECT)
    registry.register(
        FunctionCapability(
            reflector,
            lambda action, _state: _successful_observation(
                reflector,
                action,
                summary="Recorded why the first check failed.",
                update=CognitiveStateUpdate(
                    reflection=Reflection(
                        outcome_summary="Replanning corrected the failed check.",
                        what_worked=["Invalidate stale verification after changing the plan."],
                        reusable_lessons=["A revised state requires fresh verification."],
                    )
                ),
            ),
        )
    )

    result = CognitiveKernel(registry).run(state, max_cycles=6)

    assert result.status is CognitiveRunStatus.COMPLETED
    assert [decision.selected.action_type for decision in result.decisions] == [
        CognitiveActionType.VERIFY,
        CognitiveActionType.REPLAN,
        CognitiveActionType.EXECUTE,
        CognitiveActionType.VERIFY,
        CognitiveActionType.REFLECT,
        CognitiveActionType.STOP,
    ]
    assert result.state["verification"] is not None
    assert result.state["verification"].passed
    assert result.state["final_answer"] == "x = 3"

    invalidations = [
        event for event in result.state["events"] if event.event_type == "verification_invalidated"
    ]
    assert len(invalidations) == 1
    assert invalidations[0].metadata["report"]["failed_checks"] == ["The two sides differed."]


def test_passing_verification_without_success_criteria_coverage_is_rejected() -> None:
    state = _math_state()
    problem = state["structured_problem"]
    assert problem is not None
    state["structured_problem"] = problem.model_copy(
        update={
            "unknowns": [],
            "success_criteria": [
                "Substitution makes both sides equal.",
                "The reported answer uses exact arithmetic.",
            ],
        }
    )
    state["gaps"] = [state["gaps"][0].model_copy(update={"filled": True})]
    state["hypotheses"] = [
        Hypothesis(
            statement="x = 3 satisfies the equation.",
            origin=HypothesisOrigin.DIRECT_REASONING,
            expected_signals=["The two sides are equal."],
            verification_checks=["Substitute x = 3."],
            falsification_criteria=["The two sides differ."],
        )
    ]
    state["plan"] = [
        PlanTask(
            id="single-check",
            action="Substitute x = 3.",
            expected_output="The two sides are equal.",
        )
    ]
    state["execution_outputs"] = [
        ExecutionOutput(
            task_id="single-check",
            summary="The substitution check passed.",
            output={"left": 10, "right": 10},
        )
    ]
    verifier = _definition("verifier", CognitiveActionType.VERIFY)
    registry = CapabilityRegistry()
    registry.register(
        FunctionCapability(
            verifier,
            lambda action, _state: _successful_observation(
                verifier,
                action,
                summary="Claimed success after only one check.",
                update=CognitiveStateUpdate(
                    verification=VerificationReport(
                        passed=True,
                        checks_run=["Substituted x = 3."],
                        confidence_delta=0.2,
                    ),
                    final_answer="x = 3",
                ),
            ),
        )
    )

    result = CognitiveKernel(registry).run(state, max_cycles=1)

    assert result.status is CognitiveRunStatus.MAX_CYCLES
    assert result.state["verification"] is not None
    assert not result.state["verification"].passed
    assert result.state["final_answer"] is None
    assert any(
        event.event_type == "success_criteria_verification_failed"
        for event in result.state["events"]
    )
