"""`polyabrain lookup`: answer a factual question from sources PolyaBrain reads itself."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.config import Settings
from app.investigator.artifacts import write_json
from app.reader.reader import Reader, ReaderStatus, render
from app.reader.sources import LocalCorpus, PoliteFetcher, SourceError, Wikidata, Wikipedia

EXIT_CODES = {
    ReaderStatus.CORROBORATED: 0,
    ReaderStatus.SINGLE_SOURCE: 0,
    ReaderStatus.CONFLICTING: 3,
    ReaderStatus.INSUFFICIENT: 4,
}


def add_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "lookup",
        help="Answer a factual question from Wikipedia, Wikidata or your own files, with verbatim evidence and no model.",
    )
    parser.add_argument("question", nargs="+")
    parser.add_argument(
        "--corpus", type=Path, help="A folder of .txt/.md/.rst files to read as well."
    )
    parser.add_argument(
        "--no-web", action="store_true", help="Read only --corpus; never contact the web."
    )
    parser.add_argument("--output-root", type=Path, default=Path("runs/reader"))
    parser.add_argument("--run-id")
    parser.add_argument("--json", action="store_true")


def build_reader(settings: Settings, *, corpus: Path | None, web: bool) -> Reader:
    fetcher = PoliteFetcher(
        contact=settings.reader_contact,
        cache_dir=Path(settings.reader_cache_dir).expanduser()
        if settings.reader_cache_dir.strip()
        else None,
    )
    return Reader(
        Wikipedia(fetcher) if web else None,
        Wikidata(fetcher) if web else None,
        LocalCorpus(corpus) if corpus is not None else None,
    )


def run(args: argparse.Namespace) -> int:
    """Exit 0 answered, 3 conflicting sources, 4 insufficient evidence, 1 setup error."""
    question = " ".join(args.question).strip()
    if not question or len(question) > 1_000:
        print("polyabrain: The question must contain 1–1000 characters.", file=sys.stderr)
        return 1
    if args.no_web and args.corpus is None:
        print("polyabrain: --no-web needs --corpus.", file=sys.stderr)
        return 1
    if args.run_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.run_id):
        print("polyabrain: --run-id must be a plain folder name.", file=sys.stderr)
        return 1
    try:
        settings = Settings()
        reader = build_reader(settings, corpus=args.corpus, web=not args.no_web)
    except (SourceError, ValidationError) as exc:
        print(f"polyabrain: {exc}", file=sys.stderr)
        return 1
    answer = reader.answer(question)
    if reader.wikipedia is not None and not settings.reader_contact.strip():
        answer.notes.append(
            "Reading Wikimedia anonymously (10 requests/minute). Set READER_CONTACT to a contact URL "
            "or email to identify PolyaBrain and read faster."
        )
    directory = args.output_root.resolve() / (args.run_id or str(uuid4()))
    try:
        directory.mkdir(parents=True, mode=0o700)
    except FileExistsError:
        print(
            "polyabrain: That run directory already exists. Choose a new --run-id.", file=sys.stderr
        )
        return 1
    write_json(directory / "answer.json", answer.model_dump(mode="json"))
    (directory / "report.md").write_text(render(answer), encoding="utf-8")
    if args.json:
        print(
            json.dumps({**answer.model_dump(mode="json"), "report": str(directory / "report.md")})
        )
    else:
        print(f"{answer.answer or 'No answer'} [{answer.status.value}]")
        for item in answer.evidence[:3]:
            print(f'  "{item.quote[:200]}" — {item.url}')
        print(f"Report: {directory / 'report.md'}")
    return EXIT_CODES[answer.status]
