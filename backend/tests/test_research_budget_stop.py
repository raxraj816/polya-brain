"""Public acquisition limits must not invent a need for user-owned information."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_cognitive_controller import _state_with_gap

from app.cognition import (
    CapabilityDefinition,
    CapabilityRegistry,
    CognitiveActionType,
    CognitiveController,
    CognitiveKernel,
    CognitiveRunStatus,
    CognitiveRuntime,
    CognitiveSessionRunner,
    FunctionCapability,
)
from app.cognition.contracts import CapabilityKind
from app.cognition.local_capabilities import human_input_capability
from app.cognition.research_stop import RESEARCH_BUDGET_NEXT_ACTION, research_stop_next_action
from app.cognition.task_model import CognitiveResourceBudget, accumulated_usage, budget_event
from app.config import get_settings
from app.db.models import ClarificationRequest, EpisodicMemory
from app.db.session import create_database_engine, create_session_factory
from app.graph.state import StateEvent
from app.investigator.artifacts import report_from_result
from app.memory import SQLAlchemyMemoryRepository
from app.models.contracts import EvidenceItem, ProductMode, ReasoningMode, VerificationReport
from app.sessions.service import PolyaSessionService


def public_state(*, used=3, limit=3):
    state = _state_with_gap(
        problem_type="research",
        gap_type="current_external_fact",
        description="Which public observations support the proposed explanation?",
        source="official public sources",
    )
    state["session_id"] = str(uuid4())
    state["events"].extend(
        [
            budget_event(CognitiveResourceBudget(max_external_calls=limit)),
            StateEvent(
                engine_name="cognitive_kernel",
                event_type="cognitive_resource_usage",
                reasoning_mode=ReasoningMode.EXECUTE,
                summary="Recorded preceding acquisition usage.",
                metadata={"external_calls": used, "model_calls": 7, "input_tokens": 26910},
            ),
        ]
    )
    state["evidence"] = [
        EvidenceItem(
            source_type="evaluated_web_source",
            source_uri="https://source.example/observations",
            claim="A relevant observation was retained, but coverage is incomplete.",
        )
    ]
    return state


def registry(*, search=True, inspect=False):
    def never_dispatch(*_args):
        raise AssertionError("Routing probe must not dispatch acquisition")

    result = CapabilityRegistry()
    result.register(human_input_capability())
    if search:
        result.register(
            FunctionCapability(
                CapabilityDefinition(
                    name="web_search",
                    version="no-dispatch-test",
                    kind=CapabilityKind.EXTERNAL,
                    supported_actions={CognitiveActionType.SEARCH},
                    max_external_calls=1,
                    estimated_cost=0.12,
                ),
                never_dispatch,
            )
        )
    if inspect:
        result.register(
            FunctionCapability(
                CapabilityDefinition(
                    name="inspector",
                    version="no-dispatch-test",
                    supported_actions={CognitiveActionType.INSPECT},
                    estimated_cost=0.01,
                ),
                never_dispatch,
            )
        )
    return result


@pytest.mark.parametrize("used,limit", [(0, 0), (3, 3)])
def test_public_budget_stop_preserves_evidence_usage_and_has_no_human_request(used, limit):
    state = public_state(used=used, limit=limit)
    result = CognitiveKernel(registry()).run(state)
    assert result.status is CognitiveRunStatus.INSUFFICIENT_EVIDENCE
    assert not result.observations
    assert result.state["evidence"] == state["evidence"]
    assert result.state["gaps"] == state["gaps"]
    assert result.state["verification"] is None
    assert result.state["final_answer"] is None
    assert result.state["reflection"] is None
    usage = accumulated_usage(result.state)
    assert (usage.external_calls, usage.model_calls, usage.input_tokens) == (used, 7, 26910)
    assert any("remaining 0" in r.rationale for r in result.decisions[-1].rejected)
    report = report_from_result(result)
    assert report.recommended_next_action == RESEARCH_BUDGET_NEXT_ACTION
    assert report.verification_status == "insufficient_evidence"
    assert report.open_questions == [state["gaps"][0].description]
    assert report.checks_performed == report.failed_checks == []


@pytest.mark.parametrize(
    "used,search,inspect,expected",
    [
        (2, True, False, CognitiveActionType.SEARCH),
        (3, True, True, CognitiveActionType.INSPECT),
    ],
)
def test_budget_stop_does_not_displace_affordable_routes_or_reclassify_unavailability(
    used, search, inspect, expected
):
    decision = CognitiveController().decide(
        public_state(used=used), registry(search=search, inspect=inspect)
    )
    assert decision.selected.action_type is expected
    assert research_stop_next_action(decision.model_dump()) is None


@pytest.mark.parametrize("mixed", [False, True])
def test_user_owned_information_remains_a_genuine_clarification(mixed):
    state = public_state()
    private_gap = state["gaps"][0].model_copy(
        update={"gap_type": "user_owned_information", "description": "Which private log applies?"}
    )
    state["gaps"] = [*state["gaps"], private_gap] if mixed else [private_gap]
    result = CognitiveKernel(registry()).run(state)
    assert result.status is CognitiveRunStatus.NEEDS_INPUT
    assert result.decisions[-1].selected.action_type is CognitiveActionType.CLARIFY
    assert result.observations[-1].proposed_update.questions_to_ask == [
        "Please provide the missing information: Which private log applies?"
    ]


def test_public_word_in_untyped_gap_does_not_promote_classification():
    state = public_state()
    state["gaps"][0].gap_type = "unspecified"
    assert CognitiveController().decide(state, registry()).selected.action_type is (
        CognitiveActionType.ASK_HUMAN
    )


def test_affordable_memory_remains_available_after_search_budget_is_consumed():
    class RelevantMemory:
        def has_relevant_memory(self, query, domain=None):
            return True

    capabilities = registry()
    capabilities.register(
        FunctionCapability(
            CapabilityDefinition(
                name="memory",
                version="test",
                kind=CapabilityKind.MEMORY,
                supported_actions={CognitiveActionType.RETRIEVE_MEMORY},
                estimated_cost=0.01,
            ),
            lambda *_: pytest.fail("Routing must not dispatch memory"),
        )
    )
    decision = CognitiveController(semantic_memory=RelevantMemory()).decide(
        public_state(), capabilities
    )
    assert decision.selected.action_type is CognitiveActionType.RETRIEVE_MEMORY


@pytest.mark.parametrize(
    "budget_fields,reservation_fields",
    [
        ({"max_model_calls": 7}, {"max_model_calls": 1}),
        ({"max_output_tokens": 0}, {"max_output_tokens": 100}),
        ({"max_normalized_cost": 0}, {}),
    ],
)
def test_other_acquisition_reservation_limits_also_stop_truthfully(
    budget_fields, reservation_fields
):
    state = public_state(used=2)
    state["events"][1] = budget_event(CognitiveResourceBudget(**budget_fields))
    capabilities = registry(search=False)
    capabilities.register(
        FunctionCapability(
            CapabilityDefinition(
                name="web_search",
                version="test",
                kind=CapabilityKind.EXTERNAL,
                supported_actions={CognitiveActionType.SEARCH},
                max_external_calls=1,
                estimated_cost=0.12,
                **reservation_fields,
            ),
            lambda *_: pytest.fail("Budget-rejected search must not execute"),
        )
    )
    decision = CognitiveController().decide(state, capabilities)
    assert decision.selected.action_type is CognitiveActionType.STOP
    assert research_stop_next_action(decision.model_dump()) == RESEARCH_BUDGET_NEXT_ACTION


def test_research_stop_preserves_prior_failed_checks_without_claiming_new_verification():
    state = public_state()
    state["verification"] = VerificationReport(
        passed=False,
        checks_run=["Prior source comparison"],
        failed_checks=["Missing supporting passage"],
        confidence_delta=-0.1,
        recommended_route="Acquire the missing passage.",
    )
    result = CognitiveKernel(registry()).run(state)
    report = report_from_result(result)
    assert report.failed_checks == ["Missing supporting passage"]
    assert report.checks_performed == ["Prior source comparison"]
    assert report.recommended_next_action == RESEARCH_BUDGET_NEXT_ACTION
    assert not result.observations


@pytest.mark.parametrize("metadata", [None, {}, {"selected": {"action_type": "stop"}}])
def test_malformed_stop_metadata_cannot_supply_recovery_guidance(metadata):
    assert research_stop_next_action(metadata) is None


def test_later_decision_supersedes_old_budget_stop_guidance():
    result = CognitiveKernel(registry()).run(public_state())
    newer = CognitiveController().decide(public_state(used=2), registry())
    result.state["events"].append(
        StateEvent(
            engine_name="cognitive_controller",
            event_type="cognitive_action_decision",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="A later decision supersedes the old stop.",
            metadata=newer.model_dump(mode="json"),
        )
    )
    assert report_from_result(result).recommended_next_action != RESEARCH_BUDGET_NEXT_ACTION


@pytest.mark.skipif(
    os.getenv("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)
@pytest.mark.parametrize("cause", ["budget", "missing", "failed", "privacy"])
def test_persisted_research_stop_keeps_report_and_usage_without_clarification_or_learning(cause):
    from test_research_unavailable_stop import blocked_research

    from app.cognition.research_stop import RESEARCH_UNAVAILABLE_NEXT_ACTION

    engine = create_database_engine(get_settings().database_url)
    factory = create_session_factory(engine)
    if cause == "budget":
        state, capabilities = public_state(), registry()
    else:
        state, capabilities, _ = blocked_research(cause)
    expected = (
        RESEARCH_BUDGET_NEXT_ACTION if cause == "budget" else RESEARCH_UNAVAILABLE_NEXT_ACTION
    )

    def run(raw_input, *, session_id):
        state["session_id"] = session_id
        state["raw_input"] = raw_input
        return CognitiveSessionRunner(CognitiveRuntime(capabilities), initial_state=state)(
            raw_input, session_id=session_id
        )

    with factory() as db:
        service = PolyaSessionService(
            db, runner=run, memory_repository=SQLAlchemyMemoryRepository(db)
        )
        session = service.create_session(
            raw_input="Investigate the public evidence.", mode=ProductMode.INVESTIGATE, domain=None
        )
        service.run_session(session.id)
        session_id = session.id
    with factory() as db:
        service = PolyaSessionService(db)
        saved = service.get_session(session_id)
        report = service.get_report(session_id)
        assert saved.status == "completed"  # Execution finished, not verified success.
        assert report.verification_status != "passed"
        assert "without a verified conclusion" in report.final_conclusion
        assert report.recommended_next_action == expected
        assert len(report.evidence_used) == len(report.open_questions) == 1
        assert report.reflection is None
        for model in [ClarificationRequest, EpisodicMemory]:
            field = model.session_id if model is ClarificationRequest else model.source_session_id
            assert (
                db.scalar(select(func.count()).select_from(model).where(field == session_id)) == 0
            )
    engine.dispose()
