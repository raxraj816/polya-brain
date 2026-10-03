"""Frozen PolyaBrain Reader evaluation: no language model, real Wikipedia and Wikidata.

PYTHONPATH=backend:. .venv/bin/python -m evals.reader.run --output runs/reader-eval/NEW

Sources are read through the polite fetcher (paced, Retry-After honoured, cached on
disk), so a rerun on the same cache is offline and deterministic. Set READER_CONTACT
to identify the client and read at Wikimedia's higher rate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.reader.reader import READER_VERSION, Reader, ReaderStatus, normalize
from app.reader.sources import PoliteFetcher, Wikidata, Wikipedia

ROOT = Path(__file__).parent
ANSWERED = {ReaderStatus.CORROBORATED.value, ReaderStatus.SINGLE_SOURCE.value}


def matches(expected: list[str], answer: str | None) -> bool:
    """Any expected variant equals the answer or one of its '; '-joined parts."""
    if not answer:
        return False
    parts = {normalize(part) for part in [answer, *answer.split(";")]}
    return any(normalize(variant) in parts for variant in expected)


def score(question: dict[str, Any], result: dict[str, Any]) -> str:
    """One outcome per question.

    correct / wrong: a trusted answer (corroborated or single source) that is right or not.
    flagged_correct / flagged_wrong: the Reader answered but marked the sources as conflicting.
    abstained: insufficient evidence on an answerable question.
    abstained_correctly / answered_unanswerable: for questions with no true answer.
    """
    status, answer = result["status"], result.get("answer")
    if question.get("unanswerable"):
        return "abstained_correctly" if answer is None else "answered_unanswerable"
    if answer is None:
        return "abstained"
    right = matches(question["answers"], answer)
    if status in ANSWERED:
        return "correct" if right else "wrong"
    return "flagged_correct" if right else "flagged_wrong"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=None)
    args = parser.parse_args()

    raw = (ROOT / "questions.json").read_bytes()
    freeze = json.loads((ROOT / "FREEZE.json").read_text())
    digest = hashlib.sha256(raw).hexdigest()
    if digest != freeze["questions_sha256"]:
        raise SystemExit(f"questions.json changed since it was frozen ({digest})")
    questions = json.loads(raw)

    settings = Settings()
    fetcher = PoliteFetcher(
        contact=settings.reader_contact,
        cache_dir=args.cache or Path(settings.reader_cache_dir),
    )
    reader = Reader(Wikipedia(fetcher), Wikidata(fetcher))
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for question in questions:
        answer = reader.answer(question["question"])
        result = answer.model_dump(mode="json")
        outcome = score(question, result)
        rows.append(
            {
                "id": question["id"],
                "question": question["question"],
                "expected": question["answers"],
                "answer": result.get("answer"),
                "status": result["status"],
                "outcome": outcome,
                "evidence": [
                    {"source": e["source"], "title": e["title"], "quote": e["quote"][:300]}
                    for e in result.get("evidence", [])[:3]
                ],
                "notes": result.get("notes", []),
                "model_calls": result.get("model_calls", 0),
            }
        )
        print(f"{outcome:22} {question['id']:26} -> {result.get('answer')!r} [{result['status']}]")
        (args.output / "results.json").write_text(json.dumps(rows, indent=2))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    answerable = sum(1 for q in questions if not q.get("unanswerable"))
    trusted = counts.get("correct", 0) + counts.get("wrong", 0)
    summary = {
        "reader_version": READER_VERSION,
        "questions_sha256": digest,
        "answerable": answerable,
        "unanswerable": len(questions) - answerable,
        "counts": counts,
        "trusted_answers": trusted,
        "trusted_precision": round(counts.get("correct", 0) / trusted, 3) if trusted else None,
        "answerable_correct_any_status": counts.get("correct", 0)
        + counts.get("flagged_correct", 0),
        "unanswerable_abstention": counts.get("abstained_correctly", 0),
        "model_calls": sum(row["model_calls"] for row in rows),
        "source_requests": fetcher.requests,
        "identified_client": fetcher.identified,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
