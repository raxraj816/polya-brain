"""Read-only bounded measurement over explicit local CSV and JSON tables."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import Field, JsonValue

from app.cognition.capabilities import FunctionCapability
from app.cognition.contracts import (
    CapabilityDefinition,
    CognitiveActionCandidate,
    CognitiveActionType,
    CognitiveObservation,
    CognitiveStateUpdate,
    ObservationStatus,
)
from app.graph.state import ExecutionOutput, PolyaState, StateEvent
from app.models.contracts import ContractModel, EvidenceItem, NonEmptyStr, ReasoningMode, RiskLevel

_PATH = re.compile(r"[`\"']?(?P<path>[A-Za-z0-9_./\\-]+\.(?:csv|json))[`\"']?", re.I)


class NumericColumnSummary(ContractModel):
    """Exact decimal summary for one numeric column."""

    column: NonEmptyStr
    count: int = Field(ge=1)
    missing_count: int = Field(ge=0)
    minimum: NonEmptyStr
    maximum: NonEmptyStr
    mean: NonEmptyStr
    median: NonEmptyStr
    p95: NonEmptyStr
    standard_deviation: NonEmptyStr
    first: NonEmptyStr
    last: NonEmptyStr
    percent_change: NonEmptyStr | None = None
    anomaly_count: int = Field(ge=0)


class CategoricalColumnSummary(ContractModel):
    """Bounded frequency summary for one non-numeric column."""

    column: NonEmptyStr
    count: int = Field(ge=1)
    missing_count: int = Field(ge=0)
    distinct_count: int = Field(ge=1)
    top_values: dict[str, int]
    top_value_rates: dict[str, NonEmptyStr]


class TableMeasurement(ContractModel):
    """Auditable result of one read-only table measurement."""

    source_uri: NonEmptyStr
    row_count: int = Field(ge=1)
    columns: list[NonEmptyStr]
    numeric: list[NumericColumnSummary]
    categorical: list[CategoricalColumnSummary]
    grouped: list[GroupedTableSummary] = Field(default_factory=list)


class GroupedTableSummary(ContractModel):
    """Numeric summaries for one value of an explicit grouping dimension."""

    group_by: NonEmptyStr
    group_value: NonEmptyStr
    row_count: int = Field(ge=1)
    numeric: list[NumericColumnSummary]


class TableQueryResult(ContractModel):
    """Bounded rows returned by a read-only in-memory SQL query."""

    source_uri: NonEmptyStr
    query: NonEmptyStr
    columns: list[NonEmptyStr]
    rows: list[list[JsonValue]]


def _decimal_text(value: Decimal) -> str:
    normalized = format(value.normalize(), "f")
    return "0" if normalized in {"-0", ""} else normalized


def _percentile(values: list[Decimal], percentile: Decimal) -> Decimal:
    ordered = sorted(values)
    rank = max(1, int((percentile * Decimal(len(ordered))).to_integral_value()))
    return ordered[min(rank, len(ordered)) - 1]


class TableMeasurementTool:
    """Measure only explicitly referenced tables inside configured roots."""

    def __init__(
        self,
        allowed_roots: list[Path],
        *,
        max_file_bytes: int = 2_000_000,
        max_rows: int = 50_000,
    ) -> None:
        self._roots = tuple(dict.fromkeys(root.resolve(strict=True) for root in allowed_roots))
        if not self._roots or any(not root.is_dir() for root in self._roots):
            raise ValueError("table measurement requires valid allowed directories")
        self._max_file_bytes = max_file_bytes
        self._max_rows = max_rows

    def measure(self, raw_input: str, target: str) -> TableMeasurement | None:
        """Resolve one explicit table and return deterministic column summaries."""
        path = self._resolve_path(f"{raw_input}\n{target}")
        if path is None:
            return None
        rows = self._load_rows(path)
        if not rows:
            raise ValueError("table contains no data rows")
        columns = list(dict.fromkeys(key for row in rows for key in row))
        if not columns:
            raise ValueError("table contains no columns")
        numeric, categorical = self._summaries(rows, columns)
        grouped: list[GroupedTableSummary] = []
        group_column = self._requested_group_column(columns, f"{raw_input}\n{target}")
        if group_column is not None:
            groups: dict[str, list[dict[str, JsonValue]]] = {}
            for row in rows:
                value = row.get(group_column)
                key = "(missing)" if value in (None, "") else str(value)
                groups.setdefault(key, []).append(row)
            if len(groups) > 50:
                raise ValueError("grouping exceeds the configured group limit")
            for group_value, group_rows in sorted(groups.items()):
                group_numeric, _ = self._summaries(group_rows, columns)
                grouped.append(
                    GroupedTableSummary(
                        group_by=group_column,
                        group_value=group_value,
                        row_count=len(group_rows),
                        numeric=group_numeric,
                    )
                )
        return TableMeasurement(
            source_uri=path.as_uri(),
            row_count=len(rows),
            columns=columns,
            numeric=numeric,
            categorical=categorical,
            grouped=grouped,
        )

    @staticmethod
    def _summaries(
        rows: list[dict[str, JsonValue]],
        columns: list[str],
    ) -> tuple[list[NumericColumnSummary], list[CategoricalColumnSummary]]:
        numeric: list[NumericColumnSummary] = []
        categorical: list[CategoricalColumnSummary] = []
        for column in columns:
            raw_values = [row.get(column) for row in rows]
            present = [str(value).strip() for value in raw_values if value not in (None, "")]
            missing = len(raw_values) - len(present)
            decimals: list[Decimal] = []
            numeric_column = bool(present)
            for value in present:
                try:
                    decimals.append(Decimal(value))
                except InvalidOperation:
                    numeric_column = False
                    break
            if numeric_column and decimals:
                ordered = sorted(decimals)
                mean = sum(decimals) / Decimal(len(decimals))
                variance = sum((value - mean) ** 2 for value in decimals) / Decimal(len(decimals))
                standard_deviation = variance.sqrt()
                midpoint = len(ordered) // 2
                median = (
                    ordered[midpoint]
                    if len(ordered) % 2
                    else (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)
                )
                percent_change = (
                    _decimal_text(((decimals[-1] - decimals[0]) / abs(decimals[0])) * 100)
                    if decimals[0] != 0
                    else None
                )
                anomaly_count = (
                    sum(
                        1
                        for value in decimals
                        if abs(value - mean) > Decimal(3) * standard_deviation
                    )
                    if standard_deviation != 0
                    else 0
                )
                numeric.append(
                    NumericColumnSummary(
                        column=column,
                        count=len(decimals),
                        missing_count=missing,
                        minimum=_decimal_text(min(decimals)),
                        maximum=_decimal_text(max(decimals)),
                        mean=_decimal_text(mean),
                        median=_decimal_text(median),
                        p95=_decimal_text(_percentile(decimals, Decimal("0.95"))),
                        standard_deviation=_decimal_text(standard_deviation),
                        first=_decimal_text(decimals[0]),
                        last=_decimal_text(decimals[-1]),
                        percent_change=percent_change,
                        anomaly_count=anomaly_count,
                    )
                )
            elif present:
                counts = Counter(present)
                categorical.append(
                    CategoricalColumnSummary(
                        column=column,
                        count=len(present),
                        missing_count=missing,
                        distinct_count=len(counts),
                        top_values=dict(counts.most_common(10)),
                        top_value_rates={
                            value: _decimal_text(
                                (Decimal(count) / Decimal(len(present))) * Decimal(100)
                            )
                            for value, count in counts.most_common(10)
                        },
                    )
                )
        return numeric, categorical

    @staticmethod
    def _requested_group_column(columns: list[str], text: str) -> str | None:
        normalized_text = re.sub(r"[^a-z0-9]+", " ", text.casefold())
        for column in columns:
            normalized_column = re.sub(r"[^a-z0-9]+", " ", column.casefold()).strip()
            if normalized_column and f" by {normalized_column}" in f" {normalized_text}":
                return column
        return None

    def query(self, raw_input: str, target: str, sql: str) -> TableQueryResult | None:
        """Execute one read-only query over an in-memory copy named ``data``."""
        path = self._resolve_path(f"{raw_input}\n{target}")
        if path is None:
            return None
        statement = sql.strip().removesuffix(";").strip()
        if (
            not statement
            or len(statement) > 2_000
            or ";" in statement
            or not statement.casefold().startswith(("select ", "with "))
        ):
            raise ValueError("table query must be one bounded SELECT statement")
        rows = self._load_rows(path)
        if not rows:
            raise ValueError("table contains no data rows")
        columns = list(dict.fromkeys(key for row in rows for key in row))
        connection = sqlite3.connect(":memory:")
        try:
            quoted_columns = ", ".join(
                f'"{item.replace(chr(34), chr(34) * 2)}" TEXT' for item in columns
            )
            connection.execute(f"CREATE TABLE data ({quoted_columns})")
            placeholders = ", ".join("?" for _ in columns)
            connection.executemany(
                f"INSERT INTO data VALUES ({placeholders})",
                [[row.get(column) for column in columns] for row in rows],
            )
            allowed_actions = {
                sqlite3.SQLITE_SELECT,
                sqlite3.SQLITE_READ,
                sqlite3.SQLITE_FUNCTION,
                sqlite3.SQLITE_RECURSIVE,
            }

            def authorize(action: int, *args: object) -> int:
                return sqlite3.SQLITE_OK if action in allowed_actions else sqlite3.SQLITE_DENY

            connection.set_authorizer(authorize)
            steps = 0

            def limit_steps() -> int:
                nonlocal steps
                steps += 1
                return 1 if steps > 200 else 0

            connection.set_progress_handler(limit_steps, 1_000)
            cursor = connection.execute(statement)
            result_rows = cursor.fetchmany(1_001)
            if len(result_rows) > 1_000:
                raise ValueError("table query exceeds the result-row limit")
            result_columns = [item[0] for item in cursor.description or []]
            return TableQueryResult(
                source_uri=path.as_uri(),
                query=statement,
                columns=result_columns,
                rows=[list(row) for row in result_rows],
            )
        except sqlite3.Error as exc:
            raise ValueError("read-only table query was rejected") from exc
        finally:
            connection.close()

    def _resolve_path(self, text: str) -> Path | None:
        for match in _PATH.finditer(text):
            raw = match.group("path")
            candidate = Path(raw).expanduser()
            attempts = (
                [candidate]
                if candidate.is_absolute()
                else [root / candidate for root in self._roots]
            )
            for attempt in attempts:
                try:
                    resolved = attempt.resolve(strict=True)
                except OSError:
                    continue
                if (
                    resolved.is_file()
                    and resolved.suffix.casefold() in {".csv", ".json"}
                    and resolved.stat().st_size <= self._max_file_bytes
                    and any(resolved.is_relative_to(root) for root in self._roots)
                ):
                    return resolved
        return None

    def _load_rows(self, path: Path) -> list[dict[str, JsonValue]]:
        if path.suffix.casefold() == ".csv":
            with path.open(encoding="utf-8", newline="") as handle:
                rows = [dict(row) for row in csv.DictReader(handle)]
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
                raise ValueError("JSON table must be a list of objects")
            rows = [
                {str(key): value for key, value in row.items() if isinstance(key, str)}
                for row in payload
            ]
        if len(rows) > self._max_rows:
            raise ValueError("table exceeds the configured row limit")
        return rows


def table_measurement_capability(tool: TableMeasurementTool) -> FunctionCapability:
    """Expose deterministic table measurement to the cognitive controller."""
    definition = CapabilityDefinition(
        name="measurement",
        version="local_table_measurement@0.1.0",
        supported_actions={
            CognitiveActionType.MEASURE,
            CognitiveActionType.OBSERVE,
            CognitiveActionType.EXECUTE,
        },
        risk_level=RiskLevel.LOW,
        approved_for_sensitive_data=True,
        estimated_cost=0.04,
    )

    def execute(
        action: CognitiveActionCandidate,
        state: PolyaState,
    ) -> CognitiveObservation:
        try:
            task = next((item for item in state["plan"] if item.id == action.target), None)
            sql = task.params.get("sql") if task is not None else None
            source = task.params.get("source") if task is not None else None
            source_context = (
                f"{state['raw_input']}\n{source}" if isinstance(source, str) else state["raw_input"]
            )
            result = (
                tool.query(source_context, action.target, sql)
                if action.action_type is CognitiveActionType.EXECUTE and isinstance(sql, str)
                else tool.measure(source_context, action.target)
            )
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.FAILED,
                summary=f"Table measurement rejected invalid input ({type(exc).__name__}).",
                failure_kind="measurement_invalid_input",
            )
        if result is None:
            return CognitiveObservation(
                action_id=action.id,
                capability=definition.name,
                capability_version=definition.version,
                status=ObservationStatus.BLOCKED,
                summary="No explicit permitted CSV or JSON table reference was found.",
                failure_kind="measurement_artifact_required",
            )
        serialized = result.model_dump_json()
        is_query = isinstance(result, TableQueryResult)
        if isinstance(result, TableQueryResult):
            observed_row_count = len(result.rows)
            numeric_column_count = 0
            categorical_column_count = 0
            event_summary = f"Returned {observed_row_count} row(s) from a read-only query."
        else:
            observed_row_count = result.row_count
            numeric_column_count = len(result.numeric)
            categorical_column_count = len(result.categorical)
            event_summary = (
                f"Measured {result.row_count} row(s) across {len(result.columns)} column(s)."
            )
        evidence = EvidenceItem(
            source_type="deterministic_table_measurement",
            source_uri=result.source_uri,
            claim=serialized,
            raw_excerpt=serialized,
            reliability_score=1.0,
            relevance_score=1.0,
        )
        event = StateEvent(
            engine_name=definition.name,
            event_type="table_query_completed" if is_query else "measurement_completed",
            reasoning_mode=ReasoningMode.EXECUTE,
            summary=event_summary,
            metadata={
                "source_uri": result.source_uri,
                "row_count": observed_row_count,
                "numeric_column_count": numeric_column_count,
                "categorical_column_count": categorical_column_count,
                "measurement_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
            },
        )
        return CognitiveObservation(
            action_id=action.id,
            capability=definition.name,
            capability_version=definition.version,
            status=ObservationStatus.SUCCEEDED,
            summary=event.summary,
            payload=result.model_dump(mode="json"),
            evidence=[evidence],
            proposed_update=CognitiveStateUpdate(
                resolved_gap_targets=(
                    [action.target] if action.action_type is not CognitiveActionType.EXECUTE else []
                ),
                execution_outputs_to_add=(
                    [
                        ExecutionOutput(
                            task_id=action.target,
                            summary=event.summary,
                            output=result.model_dump(mode="json"),
                        )
                    ]
                    if action.action_type is CognitiveActionType.EXECUTE
                    else []
                ),
                trace_events_to_add=[event],
            ),
        )

    return FunctionCapability(definition, execute)
