"""Offline campaign inventory; never authorizes spending or contacts a provider."""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def money(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Missing or boolean amount")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Amount must be finite and nonnegative")
    return result


def audit_campaign(roots, traces=(), cap="5"):
    """Deduplicate paths and returned response IDs, retaining uncertain reservations.

    Explicit traces are only for calls outside SpendGuard, not copies of guarded
    calls. They lack response IDs and therefore cannot be globally deduplicated.
    """
    cap = money(cap)
    hashes, issues, records, duplicates, seen = {}, [], [], [], {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw, parse_float=Decimal)

    directories = set()
    for root in roots:
        root = Path(root).resolve()
        if not root.is_dir():
            issues.append(f"Missing inventory root: {root}")
        directories.update(p.resolve() for p in root.rglob("spend") if p.is_dir())
    for directory in sorted(directories):
        stems = sorted({p.name.split(".")[0] for p in directory.glob("*.json")})
        for stem in stems:
            files = {
                kind: directory / f"{stem}.{kind}.json"
                for kind in ("reserved", "reported", "response", "unknown")
            }
            record = dict(
                source=str(directory / stem),
                kind="guarded",
                reported_usd="0",
                unresolved_reservation_usd="0",
            )
            try:
                reserve = read(files["reserved"])
                amount = money(reserve["reserve_usd"])
                # Retain before parsing the response: malformed records cannot refund it.
                record["unresolved_reservation_usd"] = str(amount)
                if files["unknown"].exists():
                    read(files["unknown"])
                if files["reported"].exists() and files["response"].exists():
                    reported, response = read(files["reported"]), read(files["response"])
                    cost = money(reported["provider_reported_cost_usd"])
                    if (
                        cost != money(response["usage"]["estimated_cost_usd"])
                        or reported["model"] != response["model"]
                        or reported["response_id"] != response["response_id"]
                    ):
                        raise ValueError("Response and reported ledger disagree")
                    identity = reported["response_id"]
                    if not isinstance(identity, str) or not identity.strip():
                        raise ValueError("Missing response identity")
                    signature = hashes[str(files["response"])]
                    if identity in seen:
                        prior_source, prior_signature = seen[identity]
                        if signature != prior_signature:
                            raise ValueError("Conflicting records for the same response ID")
                        duplicates.append(dict(source=record["source"], duplicate_of=prior_source))
                        cost_to_count = Decimal(0)
                    else:
                        seen[identity] = (record["source"], signature)
                        cost_to_count = cost
                    record.update(
                        response_id=identity,
                        reported_usd=str(cost_to_count),
                        unresolved_reservation_usd="0",
                    )
                    if response["model"] != reserve["model"]:
                        issues.append(f"Route mismatch: {record['source']}")
                    if cost > amount:
                        issues.append(f"Reported cost exceeds reservation: {record['source']}")
                    if files["unknown"].exists():
                        issues.append(
                            f"Unknown marker alongside returned response: {record['source']}"
                        )
                else:
                    if files["reported"].exists() or files["response"].exists():
                        raise ValueError("Incomplete reported/response pair")
                    record["cost_unknown"] = True
            except (OSError, ValueError, KeyError, TypeError) as exc:
                issues.append(f"{record['source']}: {type(exc).__name__}: {exc}")
            records.append(record)

    for path in sorted({Path(p).resolve() for p in traces}):
        try:
            if any(directory.parent in path.parents for directory in directories):
                raise ValueError("Trace overlaps a guarded batch")
            events = read(path)
            calls = [
                call
                for event in events
                if isinstance(event.get("metadata", {}).get("model_calls"), list)
                for call in event["metadata"]["model_calls"]
            ]
            if not calls:
                raise ValueError("No itemized model calls; does not establish zero cost")
            for index, call in enumerate(calls):
                cost = money(call["cost_usd"])
                records.append(
                    dict(
                        source=f"{path}#call-{index}",
                        kind="trace_only",
                        reported_usd=str(cost),
                        unresolved_reservation_usd="0",
                    )
                )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(f"{path}: {type(exc).__name__}: {exc}")

    reported = sum((money(r["reported_usd"]) for r in records), Decimal(0))
    reserved = sum((money(r["unresolved_reservation_usd"]) for r in records), Decimal(0))
    return dict(
        version="offline_campaign_inventory@1",
        campaign_cap_usd=str(cap),
        provider_or_trace_reported_usd=str(reported),
        unresolved_local_reservations_usd=str(reserved),
        recorded_reported_plus_reserved_usd=str(reported + reserved),
        nominal_difference_from_cap_usd=str(cap - reported - reserved),
        unresolved_calls=sum(
            money(r["unresolved_reservation_usd"]) > 0 or r.get("cost_unknown", False)
            for r in records
        ),
        records=records,
        duplicate_responses=duplicates,
        artifact_issues=issues,
        source_sha256=hashes,
        invoice_verified=False,
        account_cap_verified=False,
        safe_to_resume_paid_calls=False,
        limitations=[
            "Inventory is limited to supplied roots and explicitly selected unguarded traces.",
            "Local reservations are estimates, not upper bounds on invoices.",
            "Trace-only calls lack response IDs; totals are not invoice reconciliation.",
            "Missing/malformed records make totals incomplete; never infer zero cost.",
            "No spending authorization or provider requests are performed by this audit.",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, required=True)
    parser.add_argument("--trace", action="append", type=Path, default=[])
    parser.add_argument("--cap", default="5")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_campaign(args.root, args.trace, args.cap)
    # Preserve historical audits; choose a new path for each snapshot.
    with args.output.open("x") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("records", "source_sha256", "limitations")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
