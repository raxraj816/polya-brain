"""Tests for deterministic read-only table measurement."""

from pathlib import Path

from app.cognition import CapabilityRegistry, CognitiveActionCandidate, CognitiveActionType
from app.cognition.kernel import CognitiveKernel
from app.execution import TableMeasurementTool, table_measurement_capability
from app.graph.state import StateEvent, create_initial_state
from app.models.contracts import (
    KnowledgeGap,
    PlanTask,
    PriorityLevel,
    ReasoningMode,
    StructuredProblem,
)


def _action() -> CognitiveActionCandidate:
    return CognitiveActionCandidate(
        id="measure-table",
        action_type=CognitiveActionType.MEASURE,
        target="Latency distribution and regional contributors",
        purpose="Measure the supplied data rather than estimate it.",
        expected_observation="Exact numeric and categorical summaries.",
        expected_usefulness=0.9,
        estimated_cost=0.04,
        capability="measurement",
        success_condition="The table is summarized with provenance.",
        failure_condition="The table cannot be read safely.",
    )


def test_csv_measurement_returns_exact_distribution_and_frequencies(tmp_path: Path) -> None:
    table = tmp_path / "latency.csv"
    table.write_text(
        "region,latency_ms,status\nus,100,ok\nus,200,ok\neu,300,error\neu,400,ok\n",
        encoding="utf-8",
    )
    tool = TableMeasurementTool([tmp_path])

    result = tool.measure(f'Analyze "{table}".', "Latency distribution by region")

    assert result is not None
    assert result.row_count == 4
    latency = next(item for item in result.numeric if item.column == "latency_ms")
    assert latency.minimum == "100"
    assert latency.maximum == "400"
    assert latency.mean == "250"
    assert latency.median == "250"
    assert latency.p95 == "400"
    assert latency.percent_change == "300"
    assert latency.first == "100"
    assert latency.last == "400"
    assert latency.anomaly_count == 0
    region = next(item for item in result.categorical if item.column == "region")
    assert region.top_values == {"us": 2, "eu": 2}
    assert region.top_value_rates == {"us": "50", "eu": "50"}
    assert [(item.group_value, item.row_count) for item in result.grouped] == [
        ("eu", 2),
        ("us", 2),
    ]
    eu_latency = next(item for item in result.grouped[0].numeric if item.column == "latency_ms")
    assert eu_latency.mean == "350"


def test_read_only_sql_query_groups_an_in_memory_table(tmp_path: Path) -> None:
    table = tmp_path / "latency.csv"
    table.write_text(
        "region,latency_ms\nus,100\nus,200\neu,300\neu,500\n",
        encoding="utf-8",
    )
    tool = TableMeasurementTool([tmp_path])

    result = tool.query(
        f'Query "{table}".',
        "Average latency by region",
        (
            "SELECT region, AVG(CAST(latency_ms AS REAL)) AS average_latency "
            "FROM data GROUP BY region ORDER BY region"
        ),
    )

    assert result is not None
    assert result.columns == ["region", "average_latency"]
    assert result.rows == [["eu", 400.0], ["us", 150.0]]


def test_sql_boundary_rejects_mutation_external_files_and_large_results(tmp_path: Path) -> None:
    table = tmp_path / "values.json"
    table.write_text(
        "[" + ",".join(f'{{"value": {index}}}' for index in range(1001)) + "]",
        encoding="utf-8",
    )
    tool = TableMeasurementTool([tmp_path], max_rows=2_000)

    for statement in (
        "ATTACH DATABASE '/tmp/unsafe.db' AS unsafe",
        "DELETE FROM data",
        "SELECT load_extension('/tmp/unsafe') FROM data",
        "SELECT missing_column FROM data",
        "SELECT * FROM data",
    ):
        try:
            tool.query(f'Query "{table}".', "values", statement)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe or unbounded statement was accepted: {statement}")

    too_large = tmp_path / "too-large.csv"
    too_large.write_text("value\n" + ("1234567890\n" * 100), encoding="utf-8")
    small_tool = TableMeasurementTool([tmp_path], max_file_bytes=100)
    assert small_tool.measure(f'Measure "{too_large}".', "value") is None


def test_measurement_capability_executes_explicit_read_only_query_task(tmp_path: Path) -> None:
    table = tmp_path / "metrics.csv"
    table.write_text("region,value\nus,10\neu,30\n", encoding="utf-8")
    state = create_initial_state("Analyze the supplied metrics.")
    state["plan"] = [
        PlanTask(
            id="query-task",
            action="Find the largest value.",
            tool_name="measurement",
            params={
                "source": str(table),
                "sql": "SELECT region, value FROM data ORDER BY CAST(value AS REAL) DESC LIMIT 1",
            },
        )
    ]
    capability = table_measurement_capability(TableMeasurementTool([tmp_path]))
    action = _action().model_copy(
        update={
            "id": "execute-query",
            "action_type": CognitiveActionType.EXECUTE,
            "target": "query-task",
        }
    )

    observation = capability.execute(action, state)

    assert observation.status.value == "succeeded"
    assert observation.proposed_update.execution_outputs_to_add[0].task_id == "query-task"
    assert observation.payload["rows"] == [["eu", "30"]]


def test_measurement_refuses_out_of_root_and_malformed_tables(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("value\n42\n", encoding="utf-8")
    malformed = allowed / "bad.json"
    malformed.write_text('{"value": 42}', encoding="utf-8")
    tool = TableMeasurementTool([allowed])

    assert tool.measure(f'Analyze "{outside}".', "value") is None
    capability = table_measurement_capability(tool)
    state = create_initial_state(f'Analyze "{malformed}".')
    observation = capability.execute(_action(), state)

    assert observation.status.value == "failed"
    assert observation.failure_kind == "measurement_invalid_input"


def test_controller_uses_measurement_to_fill_data_gap(tmp_path: Path) -> None:
    table = tmp_path / "metrics.json"
    table.write_text(
        '[{"latency": 10, "region": "us"}, {"latency": 30, "region": "eu"}]',
        encoding="utf-8",
    )
    state = create_initial_state(f'Measure latency in "{table}".', max_iterations=2)
    state["structured_problem"] = StructuredProblem(
        core_question="What is the observed latency distribution?",
        problem_type="data_analysis",
        knowns=["A local metrics table was supplied."],
        constraints=["Use observed data."],
        success_criteria=["Report deterministic distribution measurements."],
    )
    gap = KnowledgeGap(
        description="Latency distribution in the supplied metrics dataset",
        gap_type="missing_dataset_measurement",
        priority=PriorityLevel.HIGH,
        why_needed="The distribution must be measured before explaining it.",
        suggested_source="measure the supplied dataset",
    )
    state["gaps"] = [gap]
    state["events"] = [
        StateEvent(
            engine_name="constraint_discovery",
            event_type="completed",
            reasoning_mode=ReasoningMode.COMPARE,
            summary="Constraints completed.",
            metadata={"status": "ok"},
        ),
        StateEvent(
            engine_name="gap_detector",
            event_type="gap_detection_completed",
            reasoning_mode=ReasoningMode.EXPLORE,
            summary="Gap detection completed.",
            metadata={"status": "ok"},
        ),
    ]
    registry = CapabilityRegistry()
    registry.register(table_measurement_capability(TableMeasurementTool([tmp_path])))

    result = CognitiveKernel(registry).run(state, max_cycles=2)

    assert result.decisions[0].selected.action_type is CognitiveActionType.MEASURE
    assert result.state["gaps"][0].filled
    assert len(result.state["evidence"]) == 1
    assert result.state["evidence"][0].source_type == "deterministic_table_measurement"
    assert '"mean":"20"' in result.state["evidence"][0].claim
