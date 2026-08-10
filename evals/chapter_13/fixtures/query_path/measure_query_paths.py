"""Generate real query-count and timing measurements for two SQLite query paths."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from statistics import median
from time import perf_counter_ns


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * fraction), len(ordered) - 1)
    return ordered[index]


def prepare_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE account_details (
            account_id INTEGER PRIMARY KEY,
            balance_cents INTEGER NOT NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        );
        """
    )
    connection.executemany(
        "INSERT INTO accounts(id, name) VALUES (?, ?)",
        [(index, f"account-{index}") for index in range(1, 51)],
    )
    connection.executemany(
        "INSERT INTO account_details(account_id, balance_cents) VALUES (?, ?)",
        [(index, index * 125) for index in range(1, 51)],
    )
    return connection


def measure_n_plus_one(connection: sqlite3.Connection) -> tuple[int, int, float]:
    query_count = 0

    def count_query(statement: str) -> None:
        nonlocal query_count
        if statement.lstrip().upper().startswith("SELECT"):
            query_count += 1

    connection.set_trace_callback(count_query)
    started = perf_counter_ns()
    account_ids = [row[0] for row in connection.execute("SELECT id FROM accounts")]
    rows = [
        connection.execute(
            "SELECT balance_cents FROM account_details WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        for account_id in account_ids
    ]
    duration_us = (perf_counter_ns() - started) / 1000
    connection.set_trace_callback(None)
    return query_count, len(rows), duration_us


def measure_join(connection: sqlite3.Connection) -> tuple[int, int, float]:
    query_count = 0

    def count_query(statement: str) -> None:
        nonlocal query_count
        if statement.lstrip().upper().startswith("SELECT"):
            query_count += 1

    connection.set_trace_callback(count_query)
    started = perf_counter_ns()
    rows = list(
        connection.execute(
            """
            SELECT accounts.id, account_details.balance_cents
            FROM accounts
            JOIN account_details ON account_details.account_id = accounts.id
            ORDER BY accounts.id
            """
        )
    )
    duration_us = (perf_counter_ns() - started) / 1000
    connection.set_trace_callback(None)
    return query_count, len(rows), duration_us


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=200)
    args = parser.parse_args()
    connection = prepare_database()
    measurements: list[dict[str, int | float | str]] = []
    for run_index in range(args.runs):
        for strategy, measure in [("n_plus_one", measure_n_plus_one), ("join", measure_join)]:
            query_count, row_count, duration_us = measure(connection)
            measurements.append(
                {
                    "strategy": strategy,
                    "run": run_index,
                    "query_count": query_count,
                    "row_count": row_count,
                    "duration_us": round(duration_us, 3),
                }
            )
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(measurements[0]))
        writer.writeheader()
        writer.writerows(measurements)

    summary: dict[str, object] = {"runs_per_strategy": args.runs, "strategies": {}}
    for strategy in ["n_plus_one", "join"]:
        rows = [item for item in measurements if item["strategy"] == strategy]
        durations = [float(item["duration_us"]) for item in rows]
        summary["strategies"][strategy] = {  # type: ignore[index]
            "query_count": rows[0]["query_count"],
            "row_count": rows[0]["row_count"],
            "median_duration_us": round(median(durations), 3),
            "p95_duration_us": round(percentile(durations, 0.95), 3),
        }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
