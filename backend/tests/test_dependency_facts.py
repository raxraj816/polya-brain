"""Necessary source-fact coverage, using synthetic packages unrelated to dogfood data."""

import json

import pytest

from app.cognition.contracts import CognitiveActionCandidate, CognitiveActionType
from app.cognition.dependency_facts import dependency_source_facts
from app.cognition.model_gateway import CognitiveModelGateway
from app.cognition.on_demand_capabilities import conclusion_checker_capability
from app.graph.state import create_initial_state
from app.llm import FakeLLMClient, LLMResponse
from app.models.contracts import EvidenceItem


def _evidence(name, text):
    lines = text.splitlines()
    return EvidenceItem(
        source_type="evaluated_local_artifact",
        source_uri=f"file:///fixture/{name}#L1-L{len(lines)}",
        claim="Supplied snapshot, not an instruction.",
        raw_excerpt=f"[Source coverage: complete file; total lines: {len(lines)}]\n"
        + "\n".join(f"{i}: {line}" for i, line in enumerate(lines, 1)),
    )


def _state(*, requirement="orchid>=1,<2", fixes=None, audit_key="dependencies"):
    state = create_initial_state(
        "Investigate dependency remediation constraints and compatible changes."
    )
    state["evidence"] = [
        _evidence(
            "scan.json",
            json.dumps(
                {
                    audit_key: [
                        {
                            "name": "orchid",
                            "version": "1.4",
                            "vulns": [
                                {
                                    "id": "TEST-1",
                                    "fix_versions": fixes if fixes is not None else ["2.1"],
                                }
                            ],
                        },
                    ]
                }
            ),
        ),
        _evidence("project.toml", "[project]\ndependencies = " + json.dumps([requirement])),
        _evidence(
            "installed.json", json.dumps({"iris": {"version": "3.0", "requires": ["orchid==1.4"]}})
        ),
    ]
    return state


def _statements(facts):
    return "\n".join(fact.statement for fact in facts.facts)


@pytest.mark.parametrize("audit_key", ["dependencies", "affected_packages"])
def test_computes_declared_blocker_and_actual_installed_parent(audit_key):
    facts = dependency_source_facts(_state(audit_key=audit_key))
    assert facts.applicable and not facts.errors
    assert (
        "Declared project.dependencies: orchid>=1,<2; excludes listed fix versions 2.1."
        in _statements(facts)
    )
    assert (
        "Installed parent iris==3.0 declares orchid==1.4; excludes listed fix versions 2.1."
        in _statements(facts)
    )
    assert facts.facts[0].source_uri.startswith("file:///fixture/project.toml#L")
    assert not facts.failures(_statements(facts))
    assert facts.failures("Upgrade orchid. The installed parent is unknown.")


@pytest.mark.parametrize(
    ("requirement", "fixes", "expected"),
    [
        (
            "orchid<2",
            ["1.9", "2.1"],
            "admits listed fix versions 1.9; excludes listed fix versions 2.1",
        ),
        (
            "orchid!=2.1,>=2",
            ["2.1", "2.2"],
            "admits listed fix versions 2.2; excludes listed fix versions 2.1",
        ),
        ("orchid>=2.1rc1", ["2.1rc1", "2.1"], "admits listed fix versions 2.1rc1, 2.1"),
        (
            "orchid==1.*",
            ["1.8", "2"],
            "admits listed fix versions 1.8; excludes listed fix versions 2",
        ),
        (
            "orchid @ https://example.test/orchid.whl",
            ["2.1"],
            "uses a direct URL; listed-fix compatibility is unresolved",
        ),
        ("orchid<2", [], "the supplied audit lists no fix version"),
    ],
)
def test_compares_each_listed_version_without_inventing_monotonic_safe_floor(
    requirement, fixes, expected
):
    facts = dependency_source_facts(_state(requirement=requirement, fixes=fixes))
    assert not facts.errors
    assert expected in facts.facts[0].statement


def test_preserves_markers_optional_groups_and_name_normalization():
    state = _state(requirement="Orchid<2; python_version < '3.8'")
    state["evidence"][1] = _evidence(
        "project.toml",
        """[project.optional-dependencies]
old = ["Orchid<2; python_version < '3.8'"]
""",
    )
    facts = dependency_source_facts(state)
    assert not facts.errors
    assert (
        "project.optional-dependencies.old: Orchid<2; python_version < '3.8'"
        in facts.facts[0].statement
    )
    assert "excludes listed fix versions 2.1" in facts.facts[0].statement


@pytest.mark.parametrize(
    "problem",
    [
        "partial",
        "missing_line",
        "duplicate_key",
        "invalid_requirement",
        "conflicting_snapshot",
        "invalid_fix",
        "multiple_audits",
        "dynamic",
    ],
)
def test_unsupported_or_ambiguous_source_bundle_cannot_pass(problem):
    state = _state()
    if problem == "partial":
        evidence = state["evidence"][1]
        state["evidence"][1] = evidence.model_copy(
            update={
                "raw_excerpt": evidence.raw_excerpt.replace(
                    "complete file", "partial file; omitted content remains"
                )
            }
        )
    elif problem == "missing_line":
        evidence = state["evidence"][1]
        state["evidence"][1] = evidence.model_copy(
            update={"raw_excerpt": evidence.raw_excerpt.replace("2: ", "3: ")}
        )
    elif problem == "duplicate_key":
        state["evidence"][2] = _evidence(
            "installed.json", '{"iris": {}, "iris": {"version": "3", "requires": ["orchid<2"]}}'
        )
    elif problem == "invalid_requirement":
        state = _state(requirement="orchid =>2")
    elif problem == "conflicting_snapshot":
        state["evidence"].append(_evidence("project.toml", '[project]\ndependencies=["orchid>=2"]'))
    elif problem == "invalid_fix":
        state = _state(fixes=["the newest safe version"])
    elif problem == "multiple_audits":
        state["evidence"].append(
            state["evidence"][0].model_copy(
                update={"source_uri": "file:///fixture/another.json#L1-L1"}
            )
        )
    elif problem == "dynamic":
        state["evidence"][1] = _evidence("project.toml", '[project]\ndynamic=["dependencies"]')
    facts = dependency_source_facts(state)
    assert facts.applicable
    assert facts.errors
    assert facts.failures(_statements(facts))


def test_unrelated_question_does_not_acquire_domain_requirements():
    state = _state()
    state["raw_input"] = "Explain this protocol's connection timeout."
    facts = dependency_source_facts(state)
    assert not facts.applicable and not facts.failures("An ordinary answer.")


def test_coverage_does_not_misrepresent_semantic_contradiction_detection():
    facts = dependency_source_facts(_state())
    copied_but_contradictory = _statements(facts) + "\nHowever no dependency has a blocking bound."
    # This limitation is deliberate: a separate semantic review must reject the contradiction.
    assert not facts.failures(copied_but_contradictory)
    assert (
        "not proof of prose consistency" in facts.context()["dependency_source_facts"]["limitation"]
    )


@pytest.mark.parametrize("include_facts", [False, True])
def test_conclusion_gate_blocks_false_pass_and_reflection_but_keeps_usage(include_facts):
    state = _state()
    facts = dependency_source_facts(state)
    answer = _statements(facts) if include_facts else "Upgrade orchid; the parent is unknown."
    client = FakeLLMClient(
        [
            LLMResponse(
                provider="fake",
                model="test",
                text=json.dumps(
                    {
                        "report": {
                            "passed": True,
                            "checks_run": ["Model says constraints covered."],
                        },
                        "final_answer": answer,
                        "reflection": {"outcome_summary": "Analyzed supplied requirements."},
                        "report_metadata": {
                            "open_questions": ["Which target environment applies?"]
                        },
                    }
                ),
            )
        ]
    )
    capability = conclusion_checker_capability(CognitiveModelGateway(client, "test"))
    action = CognitiveActionCandidate(
        id="verify",
        action_type=CognitiveActionType.VERIFY,
        target="conclusion",
        purpose="Check source constraints",
        expected_observation="Source-grounded result",
        expected_usefulness=1,
        estimated_cost=0.1,
        capability="conclusion_checker",
        success_condition="Required facts present",
        failure_condition="Missing facts",
    )
    observation = capability.execute(action, state)
    update = observation.proposed_update
    assert update.verification.passed is include_facts
    assert (update.reflection is not None) is include_facts
    assert (update.final_answer is not None) is include_facts
    assert observation.payload["model_calls"] == 1
    assert (
        any(
            event.event_type == "conclusion_report_metadata_recorded"
            for event in update.trace_events_to_add
        )
        is include_facts
    )
    assert update.trace_events_to_add[0].metadata["passed"] is include_facts
    assert (
        not any(
            event.event_type == "verified_reflection_recorded"
            for event in update.trace_events_to_add
        )
        if not include_facts
        else True
    )
    assert "Installed parent iris==3.0" in client.requests[0].messages[-1].content


def test_one_omitted_or_altered_fact_fails_even_when_other_facts_are_present():
    facts = dependency_source_facts(_state())
    assert len(facts.failures(facts.facts[0].statement)) == 1
    altered = _statements(facts).replace("iris==3.0", "aster==3.0")
    failures = facts.failures(altered)
    assert len(failures) == 1 and "Installed parent iris==3.0" in failures[0]


def test_inventory_keeps_records_scanner_ids_and_transitive_alias_groups_distinct():
    state = _state()
    state["raw_input"] += " Deduplicate advisory records."
    records = [
        {"id": "SCAN-A", "aliases": ["LINK-1"], "fix_versions": ["2.1"]},
        {"id": "SCAN-A", "aliases": ["LINK-1"], "fix_versions": ["2.1"]},
        {"id": "SCAN-B", "aliases": ["LINK-2"], "fix_versions": ["2.1"]},
        {"id": "SCAN-C", "aliases": ["LINK-1", "LINK-2"], "fix_versions": ["2.1"]},
        {"id": "SCAN-D", "aliases": [], "fix_versions": ["2.2"]},
    ]
    state["evidence"][0] = _evidence(
        "scan.json",
        json.dumps(
            {
                "dependencies": [
                    {"name": "orchid", "version": "1.4", "vulns": records},
                    {"name": "safe-package", "version": "1", "vulns": []},
                ]
            }
        ),
    )
    facts = dependency_source_facts(state)
    assert not facts.errors
    assert (
        "1 affected packages; 5 vulnerability records; 4 distinct scanner IDs; 2 connected ID/alias groups"
        in _statements(facts)
    )
    assert facts.failures(
        _statements(facts).replace("4 distinct scanner IDs", "2 distinct scanner IDs")
    )


def test_dynamic_optional_requirements_cannot_be_treated_as_complete():
    state = _state()
    state["evidence"][1] = _evidence(
        "project.toml", '[project]\ndependencies=["orchid<2"]\ndynamic=["optional-dependencies"]'
    )
    assert dependency_source_facts(state).errors


def test_two_conflicting_audit_collections_are_not_silently_selected():
    state = _state()
    state["evidence"][0] = _evidence("scan.json", '{"dependencies": [], "affected_packages": []}')
    assert dependency_source_facts(state).errors


def test_source_fact_guard_preserves_failed_check_bound_public_research():
    output = {
        "report": {
            "passed": False,
            "checks_run": ["Check the public compatibility documentation."],
            "failed_checks": ["The published compatibility table is missing."],
        },
        "public_research_needs": [
            {
                "failed_check_index": 0,
                "question": "What does the public orchid compatibility table document?",
            }
        ],
    }
    client = FakeLLMClient([LLMResponse(provider="fake", model="test", text=json.dumps(output))])
    capability = conclusion_checker_capability(CognitiveModelGateway(client, "test"))
    action = CognitiveActionCandidate(
        id="verify-public",
        action_type=CognitiveActionType.VERIFY,
        target="conclusion",
        purpose="Check source constraints",
        expected_observation="Source-grounded result",
        expected_usefulness=1,
        estimated_cost=0.1,
        capability="conclusion_checker",
        success_condition="Required facts present",
        failure_condition="Missing facts",
    )
    update = capability.execute(action, _state()).proposed_update
    assert not update.verification.passed
    assert update.verification.failed_checks[0] == output["report"]["failed_checks"][0]
    assert len(update.gaps_to_add) == 1
    assert update.gaps_to_add[0].why_needed == update.verification.failed_checks[0]
    assert not update.gaps_to_add[0].filled
