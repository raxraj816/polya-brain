"""Deterministically build the frozen verified-claims task set (data, questions, truth).

PYTHONPATH=backend:. .venv/bin/python -m evals.verified_claims.build_tasks
Agent-authored tasks with known answers; not an independent benchmark.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def write_csv(name: str, header: list[str], rows: list[list[object]]) -> str:
    path = DATA / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)
    return str(path.relative_to(ROOT))


def build() -> list[dict[str, object]]:
    DATA.mkdir(exist_ok=True)
    tasks: list[dict[str, object]] = []

    # T1 net paid revenue in March excluding test accounts.
    rng = random.Random(101)
    rows, truth = [], 0
    for i in range(1, 401):
        day = date(2026, 2, 1) + timedelta(days=rng.randrange(0, 59))
        email = rng.choice(
            ["ann@shop.io", "bo@corp.com", "qa@example.com", "dev@EXAMPLE.com", "cy@mail.net"]
        )
        status = rng.choice(["paid"] * 6 + ["refunded", "pending"])
        cents = rng.randrange(500, 50000)
        rows.append([i, day.isoformat(), email, f"{cents / 100:.2f}", status])
        if day.month == 3 and status == "paid" and not email.lower().endswith("@example.com"):
            truth += cents
    tasks.append(
        {
            "id": "march_net_revenue",
            "tables": [
                write_csv(
                    "orders_march", ["order_id", "order_date", "email", "amount", "status"], rows
                )
            ],
            "question": "What was the total paid revenue in March 2026, excluding test accounts (emails ending in @example.com, case-insensitive)? Give the amount in dollars to 2 decimals.",
            "truth": {"total": round(truth / 100, 2)},
            "trap": "month filter, status filter, case-insensitive test-account exclusion",
        }
    )

    # T2 median latency excluding failures and NA.
    rng = random.Random(202)
    rows, kept = [], []
    for i in range(1, 301):
        endpoint = rng.choice(["/api/search", "/api/search", "/api/cart"])
        status = rng.choice([200] * 8 + [500, 503, 404])
        latency = rng.choice(["NA", ""] + [str(rng.randrange(20, 900))] * 10)
        rows.append([i, endpoint, status, latency])
        if endpoint == "/api/search" and status < 500 and latency not in {"NA", ""}:
            kept.append(int(latency))
    tasks.append(
        {
            "id": "search_median_latency",
            "tables": [
                write_csv("requests", ["request_id", "endpoint", "status", "latency_ms"], rows)
            ],
            "question": "What is the median latency in milliseconds for /api/search requests, ignoring server errors (status 500 or above) and rows without a latency value?",
            "truth": {"median": float(statistics.median(kept)), "count_used": len(kept)},
            "truth_required": ["median"],
            "trap": "NA/blank latencies, 5xx exclusion, even-count median",
        }
    )

    # T3 distinct users with at least two purchases, normalized ids.
    rng = random.Random(303)
    names = ["alice", "bob", "carol", "dave", "erin", "frank", "gina", "hal", "ivy", "jon"]
    rows, purchases = [], Counter()
    for i in range(1, 121):
        base = rng.choice(names)
        shown = rng.choice([base, base.upper(), " " + base, base.capitalize() + " "])
        kind = rng.choice(["purchase", "view", "view", "purchase", "refund"])
        rows.append([i, shown, kind])
        if kind == "purchase":
            purchases[base] += 1
    tasks.append(
        {
            "id": "repeat_buyers",
            "tables": [write_csv("events", ["event_id", "user_id", "event_type"], rows)],
            "question": "User ids are case-insensitive and surrounding spaces are not significant. How many distinct users made at least 4 purchases?",
            "truth": {"users": sum(1 for v in purchases.values() if v >= 4)},
            "trap": "id normalization (case and whitespace)",
        }
    )

    # T4 quantity-weighted average unit price.
    rng = random.Random(404)
    rows, qty_total, value_total = [], 0, 0
    for i in range(1, 201):
        qty = rng.choice([1, 1, 2, 3, 10, 50])
        price = rng.randrange(199, 4999)
        rows.append([i, rng.choice(["widget", "gadget"]), qty, f"{price / 100:.2f}"])
        qty_total += qty
        value_total += qty * price
    tasks.append(
        {
            "id": "weighted_unit_price",
            "tables": [
                write_csv("sales_lines", ["line_id", "product", "quantity", "unit_price"], rows)
            ],
            "question": "What was the average price paid per unit sold across all lines (i.e. total revenue divided by total units)? Round to 2 decimals.",
            "truth": {"average": round(value_total / qty_total / 100, 2)},
            "trap": "quantity-weighted vs naive mean",
        }
    )

    # T5 month-over-month percentage change of paid revenue.
    rng = random.Random(505)
    rows, months = [], defaultdict(int)
    for i in range(1, 301):
        day = date(2026, 1, 1) + timedelta(days=rng.randrange(0, 90))
        status = rng.choice(["paid"] * 5 + ["failed"])
        cents = rng.randrange(1000, 20000)
        rows.append([i, day.isoformat(), f"{cents / 100:.2f}", status])
        if status == "paid":
            months[day.month] += cents
    change = (months[3] - months[2]) / months[2] * 100
    tasks.append(
        {
            "id": "mom_change",
            "tables": [write_csv("payments", ["payment_id", "paid_on", "amount", "status"], rows)],
            "question": "By what percentage did paid revenue change from February 2026 to March 2026? Use February as the base, give a signed percentage rounded to 1 decimal.",
            "truth": {"change_pct": round(change, 1)},
            "trap": "base month, sign, status filter",
        }
    )

    # T6 top-3 customers by spend, ties alphabetical.
    rng = random.Random(606)
    customers = ["Zeta", "Alpha", "Mango", "Kite", "Birch", "Orca", "Delta"]
    rows, spend = [], Counter()
    for i in range(1, 61):
        customer = rng.choice(customers)
        amount = rng.choice([10, 20, 30, 40])
        rows.append([i, customer, amount])
        spend[customer] += amount
    ranked = sorted(spend, key=lambda c: (-spend[c], c))[:3]
    tasks.append(
        {
            "id": "top_customers",
            "tables": [write_csv("purchases", ["purchase_id", "customer", "amount"], rows)],
            "question": "Which 3 customers have the highest total spend? Break ties alphabetically by name and list them in rank order.",
            "truth": {"top3": ranked},
            "trap": "ties broken alphabetically, ordering",
        }
    )

    # T7 join with latest customer record.
    rng = random.Random(707)
    cust_rows, latest = [], {}
    for cid in range(1, 41):
        country = rng.choice(["Germany", "France", "Spain"])
        cust_rows.append([cid, country, "2025-01-01"])
        latest[cid] = country
        if rng.random() < 0.3:
            moved = rng.choice(["Germany", "France", "Spain"])
            cust_rows.append([cid, moved, "2026-01-15"])
            latest[cid] = moved
    rng.shuffle(cust_rows)
    order_rows, truth = [], 0
    for oid in range(1, 251):
        cid = rng.randrange(1, 41)
        cents = rng.randrange(1000, 30000)
        status = rng.choice(["paid"] * 4 + ["cancelled"])
        order_rows.append([oid, cid, f"{cents / 100:.2f}", status])
        if status == "paid" and latest[cid] == "Germany":
            truth += cents
    tasks.append(
        {
            "id": "germany_revenue",
            "tables": [
                write_csv("customers", ["customer_id", "country", "updated_at"], cust_rows),
                write_csv("orders_eu", ["order_id", "customer_id", "amount", "status"], order_rows),
            ],
            "question": "What is the total paid order revenue from customers whose CURRENT country is Germany? A customer's current country is the one on their most recent record (latest updated_at). Give dollars to 2 decimals.",
            "truth": {"total": round(truth / 100, 2)},
            "trap": "duplicate customer records, latest wins, join, status filter",
        }
    )

    # T8 deduplicate retried transactions.
    rng = random.Random(808)
    rows, truth = [], 0
    for i in range(1, 181):
        cents = rng.randrange(100, 9000)
        tid = f"tx-{i:04d}"
        rows.append([tid, f"{cents / 100:.2f}", "2026-03-01T10:00:00"])
        truth += cents
        if rng.random() < 0.25:
            rows.append([tid, f"{cents / 100:.2f}", "2026-03-01T10:00:05"])
    rng.shuffle(rows)
    tasks.append(
        {
            "id": "dedup_transactions",
            "tables": [write_csv("transactions", ["transaction_id", "amount", "logged_at"], rows)],
            "question": "Some transactions were logged more than once because of retries (same transaction_id). What is the total amount counting each transaction_id once? Give dollars to 2 decimals.",
            "truth": {"total": round(truth / 100, 2)},
            "trap": "retry duplicates",
        }
    )
    return tasks


def main() -> None:
    tasks = build()
    for task in tasks:
        task.setdefault("truth_required", list(task["truth"]))
    (ROOT / "tasks.json").write_text(json.dumps(tasks, indent=2) + "\n")
    freeze = {
        "statement": "Built and hashed before any solver or verifier run on these tasks. Agent-authored synthetic data with deterministic ground truth; not independently sourced.",
        "tasks_sha256": hashlib.sha256((ROOT / "tasks.json").read_bytes()).hexdigest(),
        "data_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(DATA.glob("*.csv"))
        },
    }
    (ROOT / "FREEZE.json").write_text(json.dumps(freeze, indent=2) + "\n")
    for task in tasks:
        print(task["id"], task["truth"])


if __name__ == "__main__":
    main()
