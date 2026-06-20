"""Chapter 8 LangGraph skeleton tests."""

from collections.abc import Callable

import pytest

from app.engines import (
    EngineResult,
    EngineRoute,
    EngineRunOutput,
    EngineStatus,
    EngineVersion,
)
from app.graph import GraphNodeName, PolyaGraphEngines, build_polya_graph, run_polya_graph
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisOrigin,
    HypothesisStatus,
    KnowledgeGap,
    PlanTask,
    ReasoningMode,
    Reflection,
    RiskLevel,
    StructuredProblem,
    VerificationReport,
)


def engine_version(name: str) -> EngineVersion:
    return EngineVersion(engine=f"{name}@0.1.0", graph="polya_graph@0.1.0")


def ok_result(name: str, summary: str = "Engine completed.") -> EngineResult:
    return EngineResult(
        status=EngineStatus.OK,
        confidence=0.8,
        recommended_route=EngineRoute.CONTINUE,
        versions=engine_version(name),
        summary=summary,
    )


def route_result(
    name: str,
    *,
    status: EngineStatus,
    route: EngineRoute,
    summary: str,
    confidence: float | None = None,
    missing_inputs: list[str] | None = None,
    errors: list[str] | None = None,
) -> EngineResult:
    return EngineResult(
        status=status,
        confidence=confidence,
        missing_inputs=missing_inputs or [],
        recommended_route=route,
        errors=errors or [],
        versions=engine_version(name),
        summary=summary,
    )


class StubEngine:
    def __init__(
        self,
        name: GraphNodeName,
        reasoning_mode: ReasoningMode,
        run_factory: Callable[[PolyaState, int], EngineRunOutput],
    ) -> None:
        self.name = name.value
        self.reasoning_mode = reasoning_mode
        self.version = engine_version(name.value)
        self._run_factory = run_factory
        self.calls = 0

    def run(self, state: PolyaState) -> EngineRunOutput:
        self.calls += 1
        return self._run_factory(state, self.calls)


def representation_engine(
    result_factory: Callable[[str], EngineResult] | None = None,
) -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del calls
        structured_problem = StructuredProblem(
            core_question=state["raw_input"],
            problem_type="math",
            domain="arithmetic",
            knowns=["The input asks for 2+2."],
            unknowns=["The arithmetic result is not yet verified."],
            constraints=["Use exact arithmetic."],
            success_criteria=["Return the verified sum."],
            affected_entities=["answer"],
            required_data_sources=["arithmetic_identity"],
        )
        result = (
            result_factory(GraphNodeName.PROBLEM_REPRESENTATION.value)
            if result_factory is not None
            else ok_result(GraphNodeName.PROBLEM_REPRESENTATION.value, "Represented the problem.")
        )
        return EngineRunOutput(
            state_delta={"structured_problem": structured_problem},
            result=result,
        )

    return StubEngine(GraphNodeName.PROBLEM_REPRESENTATION, ReasoningMode.EXPLORE, run)


def constraint_engine() -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del state, calls
        return EngineRunOutput(
            state_delta={},
            result=ok_result(GraphNodeName.CONSTRAINT_DISCOVERY.value, "Confirmed constraints."),
        )

    return StubEngine(GraphNodeName.CONSTRAINT_DISCOVERY, ReasoningMode.EXPLORE, run)


def gap_engine(needs_evidence: bool = True) -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del state, calls
        if not needs_evidence:
            return EngineRunOutput(
                state_delta={"gaps": []},
                result=ok_result(GraphNodeName.KNOWLEDGE_GAP_DETECTION.value, "No gaps remain."),
            )
        gap = KnowledgeGap(
            description="Need an inspectable arithmetic identity.",
            gap_type="missing_evidence",
            priority="high",
            why_needed="The answer should be backed by evidence even in the skeleton.",
            suggested_source="local_arithmetic_stub",
        )
        return EngineRunOutput(
            state_delta={"gaps": [gap]},
            result=route_result(
                GraphNodeName.KNOWLEDGE_GAP_DETECTION.value,
                status=EngineStatus.NEEDS_EVIDENCE,
                route=EngineRoute.RESEARCH,
                summary="Evidence is required before reasoning.",
            ),
        )

    return StubEngine(GraphNodeName.KNOWLEDGE_GAP_DETECTION, ReasoningMode.EXPLORE, run)


def research_engine() -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del state, calls
        evidence = EvidenceItem(
            source_type="local_stub",
            source_uri="stub://arithmetic/identity",
            claim="2+2 equals 4.",
            raw_excerpt="Exact integer addition gives 2 + 2 = 4.",
            reliability_score=1.0,
            relevance_score=1.0,
        )
        return EngineRunOutput(
            state_delta={"evidence": [evidence]},
            result=ok_result(GraphNodeName.RESEARCH_ACQUISITION.value, "Collected evidence."),
        )

    return StubEngine(GraphNodeName.RESEARCH_ACQUISITION, ReasoningMode.EXPLORE, run)


def evidence_engine() -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del state, calls
        return EngineRunOutput(
            state_delta={},
            result=ok_result(GraphNodeName.EVIDENCE_EVALUATION.value, "Evidence is reliable."),
        )

    return StubEngine(GraphNodeName.EVIDENCE_EVALUATION, ReasoningMode.COMPARE, run)


def hypothesis_engine() -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del calls
        evidence_for = ["stub://arithmetic/identity"] if state["evidence"] else []
        status = HypothesisStatus.SELECTED if evidence_for else HypothesisStatus.CANDIDATE
        hypothesis = Hypothesis(
            statement="The answer is 4.",
            mechanism="Integer addition combines two pairs into four units.",
            origin=HypothesisOrigin.DIRECT_REASONING,
            expected_signals=["2 + 2 = 4"],
            evidence_for=evidence_for,
            verification_checks=["Check exact integer addition."],
            falsification_criteria=["A valid arithmetic check returns a value other than 4."],
            confidence=0.95,
            selection_rationale="It is directly supported by the arithmetic evidence."
            if evidence_for
            else None,
            status=status,
        )
        task = PlanTask(
            id="task_add_2_plus_2",
            action="Compute 2 + 2 exactly.",
            tool_name="local_arithmetic_stub",
            expected_output="4",
            risk_level=RiskLevel.LOW,
        )
        return EngineRunOutput(
            state_delta={"hypotheses": [hypothesis], "plan": [task]},
            result=ok_result(GraphNodeName.HYPOTHESIS_REASONING.value, "Generated hypothesis."),
        )

    return StubEngine(GraphNodeName.HYPOTHESIS_REASONING, ReasoningMode.COMPARE, run)


def execution_engine() -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del state, calls
        output = ExecutionOutput(
            task_id="task_add_2_plus_2",
            summary="Computed exact integer addition.",
            output={"result": 4},
        )
        return EngineRunOutput(
            state_delta={"execution_outputs": [output]},
            result=ok_result(GraphNodeName.EXECUTION.value, "Executed plan."),
        )

    return StubEngine(GraphNodeName.EXECUTION, ReasoningMode.EXECUTE, run)


def verification_engine(
    first_failure_route: EngineRoute | None = None,
    always_fail: bool = False,
) -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del state
        should_fail = always_fail or (first_failure_route is not None and calls == 1)
        if should_fail:
            report = VerificationReport(
                passed=False,
                checks_run=["Check exact integer addition."],
                failed_checks=["The first verification pass was forced to fail."],
                recommended_route=(first_failure_route or EngineRoute.REPLAN).value,
            )
            return EngineRunOutput(
                state_delta={"verification": report},
                result=route_result(
                    GraphNodeName.VERIFICATION.value,
                    status=EngineStatus.LOW_CONFIDENCE,
                    route=first_failure_route or EngineRoute.REPLAN,
                    confidence=0.2,
                    summary="Verification failed and requested recovery.",
                ),
            )
        report = VerificationReport(
            passed=True,
            checks_run=["Check exact integer addition."],
            confidence_delta=0.1,
            recommended_route=EngineRoute.FINALIZE.value,
        )
        return EngineRunOutput(
            state_delta={"verification": report},
            result=ok_result(GraphNodeName.VERIFICATION.value, "Verification passed."),
        )

    return StubEngine(GraphNodeName.VERIFICATION, ReasoningMode.VERIFY, run)


def reflection_engine() -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del calls
        reflection = Reflection(
            outcome_summary="The skeleton completed a traceable arithmetic run.",
            what_worked=["Graph routing reached reflection."],
            reusable_lessons=["Keep arithmetic checks explicit in tests."],
        )
        return EngineRunOutput(
            state_delta={
                "reflection": reflection,
                "final_answer": state["final_answer"] or "4",
            },
            result=ok_result(GraphNodeName.REFLECTION_MEMORY.value, "Reflected on the run."),
        )

    return StubEngine(GraphNodeName.REFLECTION_MEMORY, ReasoningMode.REFLECT, run)


def failing_reflection_engine(
    *,
    status: EngineStatus,
    route: EngineRoute,
    errors: list[str] | None = None,
) -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del state, calls
        return EngineRunOutput(
            state_delta={},
            result=route_result(
                GraphNodeName.REFLECTION_MEMORY.value,
                status=status,
                route=route,
                errors=errors or [],
                summary=f"Reflection reported {status.value}.",
            ),
        )

    return StubEngine(GraphNodeName.REFLECTION_MEMORY, ReasoningMode.REFLECT, run)


def exception_reflection_engine() -> StubEngine:
    def run(state: PolyaState, calls: int) -> EngineRunOutput:
        del state, calls
        raise RuntimeError("reflection store unavailable")

    return StubEngine(GraphNodeName.REFLECTION_MEMORY, ReasoningMode.REFLECT, run)


def graph_engines(
    *,
    problem_representation: StubEngine | None = None,
    knowledge_gap_detection: StubEngine | None = None,
    verification: StubEngine | None = None,
    reflection_memory: StubEngine | None = None,
) -> PolyaGraphEngines:
    return PolyaGraphEngines(
        problem_representation=problem_representation or representation_engine(),
        constraint_discovery=constraint_engine(),
        knowledge_gap_detection=knowledge_gap_detection or gap_engine(),
        research_acquisition=research_engine(),
        evidence_evaluation=evidence_engine(),
        hypothesis_reasoning=hypothesis_engine(),
        execution=execution_engine(),
        verification=verification or verification_engine(),
        reflection_memory=reflection_memory or reflection_engine(),
    )


def terminal_engine_events(state: PolyaState) -> list[StateEvent]:
    return [event for event in state["events"] if event.event_type in {"completed", "failed"}]


def test_graph_skeleton_compiles() -> None:
    app = build_polya_graph(graph_engines())

    assert app is not None


def test_graph_runs_math_problem_through_all_nine_stub_engines() -> None:
    engines = graph_engines()

    result = run_polya_graph("What is 2+2?", engines=engines, session_id="session_math")

    assert result["final_answer"] == "4"
    assert result["verification"] is not None
    assert result["verification"].passed is True
    assert result["reflection"] is not None

    completed_engine_names = [event.engine_name for event in terminal_engine_events(result)]
    for node_name in GraphNodeName:
        assert node_name.value in completed_engine_names


def test_needs_evidence_routes_to_research_before_reasoning() -> None:
    engines = graph_engines()

    result = run_polya_graph("What is 2+2?", engines=engines)

    engine_names = [event.engine_name for event in terminal_engine_events(result)]
    assert engines.research_acquisition.calls == 1
    assert engine_names.index(GraphNodeName.RESEARCH_ACQUISITION.value) < engine_names.index(
        GraphNodeName.HYPOTHESIS_REASONING.value
    )


def test_needs_input_stops_safely_before_downstream_engines() -> None:
    def needs_input(name: str) -> EngineResult:
        return route_result(
            name,
            status=EngineStatus.NEEDS_INPUT,
            route=EngineRoute.CLARIFY,
            summary="Need deployment timestamp.",
            missing_inputs=["deployment timestamp"],
        )

    engines = graph_engines(problem_representation=representation_engine(needs_input))

    result = run_polya_graph("Investigate latency.", engines=engines)

    assert engines.constraint_discovery.calls == 0
    assert engines.reflection_memory.calls == 1
    assert result["final_answer"] is not None
    assert "deployment timestamp" in result["final_answer"]
    assert any(event.event_type == "safe_stop" for event in result["events"])


@pytest.mark.parametrize(
    ("status", "route", "errors"),
    [
        (EngineStatus.LOW_CONFIDENCE, EngineRoute.CLARIFY, []),
        (EngineStatus.BLOCKED, EngineRoute.FINALIZE, []),
        (EngineStatus.FAILED, EngineRoute.FINALIZE, ["forced failure"]),
        (
            EngineStatus.INSUFFICIENT_EVIDENCE,
            EngineRoute.FINALIZE_INSUFFICIENT_EVIDENCE,
            [],
        ),
    ],
)
def test_weak_or_terminal_statuses_do_not_continue_to_next_engine(
    status: EngineStatus,
    route: EngineRoute,
    errors: list[str],
) -> None:
    def weak_result(name: str) -> EngineResult:
        return route_result(
            name,
            status=status,
            route=route,
            confidence=0.2 if status is EngineStatus.LOW_CONFIDENCE else None,
            summary=f"Forced {status.value}.",
            errors=errors,
        )

    engines = graph_engines(problem_representation=representation_engine(weak_result))

    result = run_polya_graph("Investigate weak output.", engines=engines)

    assert engines.constraint_discovery.calls == 0
    assert engines.reflection_memory.calls == 1
    assert result["final_answer"] is not None
    assert status.value in result["final_answer"]


@pytest.mark.parametrize(
    ("route", "expected_engine"),
    [
        (EngineRoute.REPLAN, GraphNodeName.HYPOTHESIS_REASONING),
        (EngineRoute.RESEARCH, GraphNodeName.RESEARCH_ACQUISITION),
        (EngineRoute.RETRY_EXECUTION, GraphNodeName.EXECUTION),
    ],
)
def test_verification_failure_routes_to_recovery_nodes(
    route: EngineRoute,
    expected_engine: GraphNodeName,
) -> None:
    engines = graph_engines(verification=verification_engine(first_failure_route=route))

    result = run_polya_graph("What is 2+2?", engines=engines)

    assert result["final_answer"] == "4"
    assert result["iteration_count"] == 1
    assert getattr(engines, expected_engine.value).calls == 2
    assert any(event.event_type == "iteration_guard" for event in result["events"])


def test_iteration_limit_prevents_infinite_recovery_loop() -> None:
    engines = graph_engines(verification=verification_engine(always_fail=True))

    result = run_polya_graph("What is 2+2?", engines=engines, max_iterations=1)

    assert result["iteration_count"] == 1
    assert engines.verification.calls == 2
    assert result["final_answer"] is not None
    assert "low_confidence" in result["final_answer"]
    assert any(event.event_type == "safe_stop" for event in result["events"])


def test_malformed_engine_output_fails_closed_in_graph() -> None:
    def run_invalid_event(state: PolyaState, calls: int) -> EngineRunOutput:
        del state, calls
        return EngineRunOutput(
            state_delta={
                "events": {
                    "engine_name": GraphNodeName.PROBLEM_REPRESENTATION.value,
                    "event_type": "parsed",
                    "reasoning_mode": ReasoningMode.EXPLORE,
                    "summary": "",
                }
            },
            result=ok_result(GraphNodeName.PROBLEM_REPRESENTATION.value),
        )

    invalid_engine = StubEngine(
        GraphNodeName.PROBLEM_REPRESENTATION,
        ReasoningMode.EXPLORE,
        run_invalid_event,
    )
    engines = graph_engines(problem_representation=invalid_engine)

    result = run_polya_graph("Investigate malformed graph output.", engines=engines)

    assert engines.constraint_discovery.calls == 0
    assert engines.reflection_memory.calls == 1
    assert result["final_answer"] is not None
    assert "ValidationError" in result["final_answer"]
    assert any(event.event_type == "safe_stop" for event in result["events"])


def test_reflection_exception_routes_to_terminal_safe_stop() -> None:
    engines = graph_engines(reflection_memory=exception_reflection_engine())

    result = run_polya_graph("What is 2+2?", engines=engines)

    assert engines.reflection_memory.calls == 1
    assert result["final_answer"] is not None
    assert "reflection_memory reported failed" in result["final_answer"]
    assert "RuntimeError: reflection store unavailable" in result["final_answer"]
    assert any(event.event_type == "terminal_safe_stop" for event in result["events"])


def test_terminal_safe_stop_preserves_prior_answer_and_surfaces_reflection_failure() -> None:
    def needs_input(name: str) -> EngineResult:
        return route_result(
            name,
            status=EngineStatus.NEEDS_INPUT,
            route=EngineRoute.CLARIFY,
            summary="Need deployment timestamp.",
            missing_inputs=["deployment timestamp"],
        )

    engines = graph_engines(
        problem_representation=representation_engine(needs_input),
        reflection_memory=exception_reflection_engine(),
    )

    result = run_polya_graph("Investigate latency.", engines=engines)

    assert result["final_answer"] is not None
    assert "deployment timestamp" in result["final_answer"]
    assert "Additionally, PolyaBrain stopped at the terminal stage" in result["final_answer"]
    assert "reflection_memory reported failed" in result["final_answer"]
    assert "RuntimeError: reflection store unavailable" in result["final_answer"]
    assert any(event.event_type == "safe_stop" for event in result["events"])
    assert any(event.event_type == "terminal_safe_stop" for event in result["events"])


@pytest.mark.parametrize(
    ("status", "route", "expected_text"),
    [
        (EngineStatus.FAILED, EngineRoute.FINALIZE, "forced reflection failure"),
        (EngineStatus.BLOCKED, EngineRoute.FINALIZE, "blocked"),
        (
            EngineStatus.INSUFFICIENT_EVIDENCE,
            EngineRoute.FINALIZE_INSUFFICIENT_EVIDENCE,
            "insufficient_evidence",
        ),
    ],
)
def test_reflection_terminal_weak_outputs_route_to_terminal_safe_stop(
    status: EngineStatus,
    route: EngineRoute,
    expected_text: str,
) -> None:
    errors = ["forced reflection failure"] if status is EngineStatus.FAILED else []
    engines = graph_engines(
        reflection_memory=failing_reflection_engine(
            status=status,
            route=route,
            errors=errors,
        )
    )

    result = run_polya_graph("What is 2+2?", engines=engines)

    assert engines.reflection_memory.calls == 1
    assert result["final_answer"] is not None
    assert expected_text in result["final_answer"]
    assert any(event.event_type == "terminal_safe_stop" for event in result["events"])
