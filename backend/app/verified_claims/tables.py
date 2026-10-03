"""Read-only, bounded loading and description of user-supplied tables."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.execution.sandbox import MAX_DATA_BYTES

MAX_TABLES = 8
SAMPLE_ROWS = 5


class TableError(ValueError):
    """A table cannot be used; the message is user-facing."""


@dataclass(frozen=True)
class Table:
    name: str
    path: Path
    kind: str  # csv | json
    data: bytes
    columns: list[str]
    row_count: int
    sample: list[dict[str, object]] = field(default_factory=list)

    def describe(self) -> str:
        sample = json.dumps(self.sample, default=str)[:2_000]
        return (
            f"table {self.name!r} ({self.kind}, {self.row_count} rows) "
            f"columns: {', '.join(self.columns)}\n  first rows: {sample}"
        )


def _name(path: Path, taken: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9_]", "_", path.stem).strip("_") or "table"
    if base[0].isdigit():
        base = "t_" + base
    base = base[:48]
    name, index = base, 2
    while name in taken:
        name, index = f"{base}_{index}", index + 1
    return name


def load_tables(paths: list[Path]) -> list[Table]:
    if not paths or len(paths) > MAX_TABLES:
        raise TableError(f"Provide between 1 and {MAX_TABLES} tables.")
    tables: list[Table] = []
    taken: set[str] = set()
    total = 0
    for raw in paths:
        path = raw.expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in {".csv", ".json"}:
            raise TableError(f"{raw} must be an existing .csv or .json file.")
        data = path.read_bytes()
        total += len(data)
        if total > MAX_DATA_BYTES:
            raise TableError(f"Tables must total at most {MAX_DATA_BYTES:,} bytes for now.")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise TableError(f"{raw} is not UTF-8 text.") from exc
        name = _name(path, taken)
        taken.add(name)
        if path.suffix.lower() == ".csv":
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
            columns = list(reader.fieldnames or [])
            kind = "csv"
        else:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise TableError(f"{raw} is not valid JSON.") from exc
            if not isinstance(parsed, list) or not all(isinstance(r, dict) for r in parsed):
                raise TableError(f"{raw} must be a JSON list of objects.")
            rows = parsed
            columns = list(dict.fromkeys(key for row in rows for key in row))
            kind = "json"
        if not columns:
            raise TableError(f"{raw} has no columns.")
        tables.append(
            Table(name, path, kind, data, columns, len(rows), [dict(r) for r in rows[:SAMPLE_ROWS]])
        )
    return tables


def schema_text(tables: list[Table]) -> str:
    return "\n".join(table.describe() for table in tables)
