"""Deterministic Chapter 10 graph runner for the API shell.

These engines prove that the platform can create a session, run the Polya graph,
persist an audit trace, and return a session outcome. They are intentionally not
real intelligence.
"""

from __future__ import annotations

from collections.abc import Callable

from app.engines import (
    EngineResult,
    EngineRoute,
    EngineRunOutput,
    EngineStatus,
    EngineVersion,
)
from app.graph.skeleton import GRAPH_VERSION, GraphNodeName, PolyaGraphEngines, run_polya_graph
from app.graph.state import ExecutionOutput, PolyaState
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

CHAPTER10_STUB_VERSION = "chapter10_stub@0.1.0"


class Chapter10StubEngine:
    """Small synchronous engine adapter used by the Chapter 10 API shell."""

    def __init__(
        self,
        *,
        node_name: GraphNodeName,
        reasoning_mode: ReasoningMode,
        run_factory: Callable[[PolyaState], EngineRunOutput],
    ) -> None:
        self.name = node_name.value
        self.reasoning_mode = reasoning_mode
        self.version = EngineVersion(
            engine=f"{node_name.value}@0.1.0",
            graph=GRAPH_VERSION,
            tool=CHAPTER10_STUB_VERSION,
        )
        self._run_factory = run_factory

    def run(self, state: PolyaState) -> EngineRunOutput:
        return self._run_factory(state)


def _ok_result(name: GraphNodeName, summary: str, confidence: float = 0.82) -> EngineResult:
    return EngineResult(
        status=EngineStatus.OK,
        confidence=confidence,
        recommended_route=EngineRoute.CONTINUE,
        versions=EngineVersion(
            engine=f"{name.value}@0.1.0",
            graph=GRAPH_VERSION,
            tool=CHAPTER10_STUB_VERSION,
        ),
        summary=summary,
    )


def _problem_representation_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        structured_problem = StructuredProblem(
            core_question=state["raw_input"],
            problem_type="technical_investigation_stub",
            domain="technical_investigation",
            knowns=["A user submitted a raw problem statement through the API shell."],
            unknowns=["Real problem semantics are deferred to the problem representation engine."],
            constraints=["Chapter 10 must not claim real investigation intelligence."],
            success_criteria=[
                "Create a session.",
                "Run the graph skeleton.",
                "Persist an ordered trace.",
                "Return an auditable placeholder outcome.",
            ],
            affected_entities=["api_shell", "graph_skeleton", "reasoning_trace"],
            required_data_sources=["chapter10_stub_runner"],
        )
        return EngineRunOutput(
            state_delta={"structured_problem": structured_problem},
            result=_ok_result(
                GraphNodeName.PROBLEM_REPRESENTATION,
                "Captured the raw problem as a Chapter 10 stub representation.",
            ),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.PROBLEM_REPRESENTATION,
        reasoning_mode=ReasoningMode.EXPLORE,
        run_factory=run,
    )


def _constraint_discovery_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        del state
        return EngineRunOutput(
            state_delta={},
            result=_ok_result(
                GraphNodeName.CONSTRAINT_DISCOVERY,
                "Confirmed the Chapter 10 API shell constraints.",
            ),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.CONSTRAINT_DISCOVERY,
        reasoning_mode=ReasoningMode.EXPLORE,
        run_factory=run,
    )


def _knowledge_gap_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        del state
        gap = KnowledgeGap(
            description="Real domain evidence is not available in the Chapter 10 stub runner.",
            gap_type="implementation_boundary",
            priority=PriorityLevel.HIGH,
            why_needed="The API shell should prove workflow wiring without overstating reasoning quality.",
            suggested_source="Chapter 11 prompt/parser and Chapter 12 LLM client",
        )
        return EngineRunOutput(
            state_delta={"gaps": [gap]},
            result=EngineResult(
                status=EngineStatus.NEEDS_EVIDENCE,
                confidence=None,
                recommended_route=EngineRoute.RESEARCH,
                versions=EngineVersion(
                    engine=f"{GraphNodeName.KNOWLEDGE_GAP_DETECTION.value}@0.1.0",
                    graph=GRAPH_VERSION,
                    tool=CHAPTER10_STUB_VERSION,
                ),
                summary="Recorded the implementation boundary before continuing.",
            ),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.KNOWLEDGE_GAP_DETECTION,
        reasoning_mode=ReasoningMode.EXPLORE,
        run_factory=run,
    )


def _research_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        del state
        evidence = EvidenceItem(
            source_type="local_stub",
            source_uri="stub://chapter-10/api-shell",
            claim="The Chapter 10 run is a deterministic platform wiring check, not a real investigation.",
            raw_excerpt="The API shell invokes deterministic stub engines to prove session and trace plumbing.",
            reliability_score=1.0,
            relevance_score=1.0,
        )
        return EngineRunOutput(
            state_delta={"evidence": [evidence]},
            result=_ok_result(
                GraphNodeName.RESEARCH_ACQUISITION,
                "Attached local evidence describing the Chapter 10 stub boundary.",
            ),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.RESEARCH_ACQUISITION,
        reasoning_mode=ReasoningMode.EXPLORE,
        run_factory=run,
    )


def _evidence_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        del state
        return EngineRunOutput(
            state_delta={},
            result=_ok_result(
                GraphNodeName.EVIDENCE_EVALUATION,
                "Verified the stub evidence is local and explicitly labeled.",
            ),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.EVIDENCE_EVALUATION,
        reasoning_mode=ReasoningMode.COMPARE,
        run_factory=run,
    )


def _hypothesis_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        evidence_for = ["stub://chapter-10/api-shell"] if state["evidence"] else []
        hypothesis = Hypothesis(
            statement="The API shell can execute the Polya graph and persist an audit trace.",
            mechanism="A synchronous request runs deterministic engines and appends their events.",
            origin=HypothesisOrigin.DIRECT_REASONING,
            expected_signals=["A completed session exists.", "Persisted trace events are ordered."],
            evidence_for=evidence_for,
            verification_checks=[
                "Run the graph skeleton.",
                "Persist trace events.",
                "Read the session and events through API responses.",
            ],
            falsification_criteria=[
                "The graph fails to complete.",
                "No events are persisted.",
                "The session cannot be read after running.",
            ],
            confidence=0.9,
            selection_rationale="This is the only Chapter 10 claim the stub runner is allowed to make.",
            status=HypothesisStatus.SELECTED,
        )
        task = PlanTask(
            id="chapter10_api_shell_smoke",
            action="Run the deterministic Chapter 10 graph and persist the resulting trace.",
            tool_name="chapter10_stub_runner",
            expected_output="A completed session with ordered trace events.",
            risk_level=RiskLevel.LOW,
        )
        return EngineRunOutput(
            state_delta={"hypotheses": [hypothesis], "plan": [task]},
            result=_ok_result(
                GraphNodeName.HYPOTHESIS_REASONING,
                "Selected the API-shell wiring hypothesis for verification.",
            ),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.HYPOTHESIS_REASONING,
        reasoning_mode=ReasoningMode.COMPARE,
        run_factory=run,
    )


def _execution_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        del state
        output = ExecutionOutput(
            task_id="chapter10_api_shell_smoke",
            summary="Executed the synchronous Chapter 10 API shell smoke run.",
            output={"runner": CHAPTER10_STUB_VERSION, "result": "completed"},
        )
        return EngineRunOutput(
            state_delta={"execution_outputs": [output]},
            result=_ok_result(GraphNodeName.EXECUTION, "Executed the stub run task."),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.EXECUTION,
        reasoning_mode=ReasoningMode.EXECUTE,
        run_factory=run,
    )


def _verification_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        checks = [
            "Session state reached verification.",
            "Execution output exists.",
            "Chapter 10 boundary remains explicit.",
        ]
        report = VerificationReport(
            passed=bool(state["execution_outputs"]),
            checks_run=checks,
            failed_checks=[] if state["execution_outputs"] else ["Execution output exists."],
            confidence_delta=0.0,
            recommended_route=EngineRoute.FINALIZE.value,
        )
        return EngineRunOutput(
            state_delta={"verification": report},
            result=_ok_result(
                GraphNodeName.VERIFICATION,
                "Verified the Chapter 10 platform wiring run.",
            ),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.VERIFICATION,
        reasoning_mode=ReasoningMode.VERIFY,
        run_factory=run,
    )


def _reflection_engine() -> Chapter10StubEngine:
    def run(state: PolyaState) -> EngineRunOutput:
        del state
        final_answer = (
            "Chapter 10 API shell completed a deterministic stub Polya loop. "
            "This proves session creation, graph execution, trace persistence, "
            "and session readback wiring; it is not a real investigation result yet. "
            "Next action: implement the Chapter 11 prompt/parser layer and Chapter 12 "
            "LLM client before trusting problem-specific conclusions."
        )
        reflection = Reflection(
            outcome_summary="The API shell can run the Polya graph through a stub workflow.",
            what_worked=[
                "The session reached reflection.",
                "The run preserved an explicit audit boundary.",
            ],
            reusable_lessons=[
                "Keep platform smoke runs distinct from intelligence claims.",
            ],
            follow_up_actions=[
                "Implement Chapter 11 prompt/parser design.",
                "Implement Chapter 12 provider-neutral LLM client.",
            ],
        )
        return EngineRunOutput(
            state_delta={"reflection": reflection, "final_answer": final_answer},
            result=_ok_result(
                GraphNodeName.REFLECTION_MEMORY,
                "Reflected on the Chapter 10 API shell run.",
            ),
        )

    return Chapter10StubEngine(
        node_name=GraphNodeName.REFLECTION_MEMORY,
        reasoning_mode=ReasoningMode.REFLECT,
        run_factory=run,
    )


def build_chapter10_stub_engines() -> PolyaGraphEngines:
    """Return deterministic engines for the Chapter 10 API shell."""
    return PolyaGraphEngines(
        problem_representation=_problem_representation_engine(),
        constraint_discovery=_constraint_discovery_engine(),
        knowledge_gap_detection=_knowledge_gap_engine(),
        research_acquisition=_research_engine(),
        evidence_evaluation=_evidence_engine(),
        hypothesis_reasoning=_hypothesis_engine(),
        execution=_execution_engine(),
        verification=_verification_engine(),
        reflection_memory=_reflection_engine(),
    )


def run_chapter10_stub_graph(
    raw_input: str,
    *,
    session_id: str,
) -> PolyaState:
    """Run the Chapter 10 deterministic graph for one persisted session."""
    return run_polya_graph(
        raw_input,
        engines=build_chapter10_stub_engines(),
        session_id=session_id,
    )
