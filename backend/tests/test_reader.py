"""PolyaBrain Reader: owned retrieval and reading, tested offline on fixed source responses."""

from __future__ import annotations

import io
import json
import urllib.error
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from app.reader.reader import Reader, ReaderStatus, normalize, render
from app.reader.sources import (
    ANONYMOUS_INTERVAL_SECONDS,
    IDENTIFIED_INTERVAL_SECONDS,
    LocalCorpus,
    PoliteFetcher,
    SourceError,
    Wikidata,
    Wikipedia,
)
from app.reader.text import AnswerType, analyse_question

PAGES = {
    "Canberra": (
        "Canberra is the capital city of Australia. Founded following the federation of the "
        "colonies of Australia as the seat of government for the new nation, it is the largest "
        "inland city in Australia."
    ),
    "Australia": (
        "Australia is a country comprising the mainland of the Australian continent. The "
        "capital of Australia is Canberra, while its largest city is Sydney."
    ),
    "Golden Gate Bridge": (
        "The Golden Gate Bridge is a suspension bridge spanning the Golden Gate strait. "
        "The bridge opened in 1937 after four years of construction. In 2011 a new visitor "
        "plaza near the south tower of the bridge opened to the public."
    ),
}
SEARCH = {
    "capital australia": ["Canberra", "Australia"],
    "Australia": ["Australia"],
    "golden gate bridge opened": ["Golden Gate Bridge"],
    "Golden Gate Bridge": ["Golden Gate Bridge"],
}
ENTITIES = {"Australia": {"id": "Q408", "label": "Australia"}}
PROPERTIES = {"capital": {"id": "P36", "label": "capital"}}
CLAIMS = {
    "Q408": {
        "labels": {"en": {"value": "Australia"}},
        "claims": {
            "P36": [
                {
                    "rank": "normal",
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"type": "wikibase-entityid", "value": {"id": "Q3114"}},
                    },
                }
            ]
        },
    },
    "Q3114": {"id": "Q3114", "labels": {"en": {"value": "Canberra"}}},
}


def fake_fetch(url: str, params: Mapping[str, str]) -> Any:
    if "wikipedia" in url and params.get("list") == "search":
        titles = SEARCH.get(params["srsearch"], [])
        return {"query": {"search": [{"title": t} for t in titles]}}
    if "wikipedia" in url and params.get("prop") == "extracts":
        title = params["titles"]
        if title not in PAGES:
            return {"query": {"pages": [{"title": title, "missing": True}]}}
        return {"query": {"pages": [{"title": title, "extract": PAGES[title]}]}}
    if params.get("action") == "wbsearchentities":
        table = PROPERTIES if params.get("type") == "property" else ENTITIES
        hit = table.get(params["search"])
        return {"search": [hit] if hit else []}
    if params.get("action") == "wbgetentities":
        return {"entities": {i: CLAIMS[i] for i in params["ids"].split("|") if i in CLAIMS}}
    raise AssertionError(f"unexpected request {url} {dict(params)}")


def reader() -> Reader:
    return Reader(Wikipedia(fake_fetch), Wikidata(fake_fetch))


@pytest.mark.parametrize(
    ("question", "kind", "entities"),
    [
        ("What is the capital of Australia?", AnswerType.PLACE, ["Australia"]),
        ("In what year did the Berlin Wall fall?", AnswerType.YEAR, ["Berlin Wall"]),
        ("Who painted the Mona Lisa?", AnswerType.PERSON, ["Mona Lisa"]),
        ("How many bones are in the adult human body?", AnswerType.NUMBER, []),
        ("How tall is the Burj Khalifa in metres?", AnswerType.QUANTITY, ["Burj Khalifa"]),
    ],
)
def test_question_analysis(question: str, kind: AnswerType, entities: list[str]) -> None:
    analysis = analyse_question(question)
    assert analysis.answer_type is kind
    assert analysis.entity_phrases == entities


def test_structured_claim_and_text_corroborate_each_other() -> None:
    answer = reader().answer("What is the capital of Australia?")
    assert answer.answer == "Canberra"
    assert answer.status is ReaderStatus.CORROBORATED
    kinds = {item.kind for item in answer.evidence}
    assert kinds == {"structured", "sentence"}
    sentence = next(item for item in answer.evidence if item.kind == "sentence")
    assert sentence.quote in PAGES[sentence.title]  # verbatim, never paraphrased
    assert answer.model_calls == 0
    assert "no language model" in render(answer)


def test_year_nearest_the_asked_relation_wins_over_other_years() -> None:
    answer = reader().answer("In what year was the Golden Gate Bridge opened?")
    assert answer.answer == "1937"
    assert "2011" in {c.value for c in answer.alternatives}


def test_false_premise_returns_insufficient_evidence() -> None:
    answer = reader().answer("Who was the first person to walk on the capital of Australia?")
    assert answer.answer is None and answer.status is ReaderStatus.INSUFFICIENT


def test_normalize() -> None:
    assert normalize("299,792,458") == "299792458"
    assert normalize("The Hague.") == "hague"


class _Response(io.BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_polite_fetcher_paces_honours_retry_after_and_caches(tmp_path: Path) -> None:
    now = [0.0]
    sleeps: list[float] = []
    calls: list[str] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    def opener(request: Any, timeout: float) -> _Response:
        calls.append(request.get_header("User-agent"))
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "busy", {"Retry-After": "3"}, None)  # type: ignore[arg-type]
        return _Response(json.dumps({"ok": len(calls)}).encode())

    fetcher = PoliteFetcher(cache_dir=tmp_path, sleep=sleep, clock=lambda: now[0], opener=opener)
    assert fetcher.min_interval == ANONYMOUS_INTERVAL_SECONDS
    assert fetcher("https://en.wikipedia.org/w/api.php", {"a": "1"}) == {"ok": 2}
    assert 3.0 in sleeps  # waited as asked by Retry-After
    assert "python-urllib" in calls[0] and "(" not in calls[0]
    assert fetcher("https://en.wikipedia.org/w/api.php", {"a": "1"}) == {"ok": 2}  # memory cache
    fresh = PoliteFetcher(cache_dir=tmp_path, opener=lambda *a, **k: pytest.fail("network"))
    assert fresh("https://en.wikipedia.org/w/api.php", {"a": "1"}) == {"ok": 2}  # disk cache
    identified = PoliteFetcher(contact="https://example.org/bot; ops@example.org")
    assert identified.min_interval == IDENTIFIED_INTERVAL_SECONDS
    assert identified.user_agent.startswith("PolyaBrain-Reader/0.1 (https://example.org/bot")


def test_long_retry_after_stops_instead_of_hanging() -> None:
    def opener(request: Any, timeout: float) -> _Response:
        raise urllib.error.HTTPError(request.full_url, 429, "busy", {"Retry-After": "3600"}, None)  # type: ignore[arg-type]

    fetcher = PoliteFetcher(min_interval=0.0, sleep=lambda s: None, opener=opener)
    with pytest.raises(SourceError, match="wait 3600s"):
        fetcher("https://en.wikipedia.org/w/api.php", {"b": "1"})


def test_search_provider_returns_verbatim_ranked_passages() -> None:
    from app.acquisition.contracts import SearchRequest
    from app.reader.provider import ReaderSearchProvider

    response = ReaderSearchProvider(Wikipedia(fake_fetch)).search(
        SearchRequest(query="capital australia", max_results=3)
    )
    assert response.provider == "polya_reader" and response.metadata["model_calls"] == 0
    first = response.candidates[0]
    assert first.title == "Canberra" and first.excerpt in PAGES["Canberra"]


def test_lookup_reads_a_local_corpus_without_the_web(tmp_path: Path) -> None:
    from app.investigator.cli import main

    corpus = tmp_path / "notes"
    corpus.mkdir()
    (corpus / "runbook.md").write_text(
        "The payments service was migrated to PostgreSQL in 2019. "
        "The ledger service retries each message at most five times."
    )
    (tmp_path / "irrelevant.bin").write_bytes(b"\x00\x01")
    code = main(
        [
            "lookup",
            "In what year was the payments service migrated to PostgreSQL?",
            "--corpus",
            str(corpus),
            "--no-web",
            "--output-root",
            str(tmp_path / "out"),
            "--run-id",
            "r1",
        ]
    )
    assert code == 0
    answer = json.loads((tmp_path / "out" / "r1" / "answer.json").read_text())
    assert answer["answer"] == "2019" and answer["evidence"][0]["source"] == "local"
    assert LocalCorpus(corpus).documents()[0].title == "runbook.md"


def test_sentence_openers_are_not_glued_onto_names() -> None:
    from app.reader.reader import _Passage
    from app.reader.sources import Document
    from app.reader.text import analyse_question

    analysis = analyse_question("Who wrote Hamlet?")
    passage = _Passage(
        Document("wikipedia", "Hamlet", "https://en.wikipedia.org/wiki/Hamlet", "", 1),
        "Either William Shakespeare or a contemporary reviser wrote the surviving text of Hamlet.",
    )
    assert reader()._extract(passage, analysis) == ["William Shakespeare"]


def _local_reader(tmp_path: Path, files: dict[str, str]) -> Reader:
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return Reader(None, None, LocalCorpus(tmp_path))


def test_hedged_counterfactual_sentences_lose_to_factual_ones(tmp_path: Path) -> None:
    reader_ = _local_reader(
        tmp_path,
        {
            "Burj Khalifa.md": (
                "Burj Khalifa is a skyscraper in Dubai. Without the spire, Burj Khalifa would be "
                "585 metres tall. Burj Khalifa has a total height of 828 metres including its spire."
            )
        },
    )
    assert reader_.answer("How tall is the Burj Khalifa in metres?").answer == "828"


def test_a_sentence_that_does_not_name_the_subject_only_counts_on_the_subject_page(
    tmp_path: Path,
) -> None:
    reader_ = _local_reader(
        tmp_path,
        {
            "Hamlet (1996 film).md": "Desson Thomson wrote of the performance that it was overlong.",
            "Hamlet.md": "Hamlet is a tragedy written by William Shakespeare around 1600.",
        },
    )
    answer = reader_.answer("Who wrote Hamlet?")
    assert answer.answer == "William Shakespeare"
    assert all(c.value != "Desson Thomson" for c in answer.alternatives)


def test_an_unasked_qualifier_marks_a_narrower_record(tmp_path: Path) -> None:
    reader_ = _local_reader(
        tmp_path,
        {
            "Astronaut.md": (
                "The first person born in Africa to fly in space was Patrick Baudry of France. "
                "The first cosmonaut was Soviet Air Force pilot Yuri Gagarin, the first person "
                "in space."
            )
        },
    )
    assert reader_.answer("Who was the first person in space?").answer == "Yuri Gagarin"


def test_a_lone_surname_credits_the_one_full_name_it_belongs_to(tmp_path: Path) -> None:
    reader_ = _local_reader(
        tmp_path,
        {
            "a.md": "The telephone was invented by Alexander Graham Bell in Boston.",
            "b.md": "Bell is credited as the inventor of the telephone.",
            "c.md": "Some say the telephone was invented by Elisha Gray first.",
        },
    )
    answer = reader_.answer("Who invented the telephone?")
    assert answer.answer == "Alexander Graham Bell"
    assert len(answer.alternatives) == 1 and answer.alternatives[0].value == "Elisha Gray"
    assert len({e.title for e in answer.evidence}) == 2


def test_namesake_pages_and_parenthetical_asides_do_not_answer() -> None:
    from app.reader.reader import _exact_subject_page, _Passage
    from app.reader.sources import Document

    def page(title: str) -> _Passage:
        return _Passage(Document("wikipedia", title, "u", "", 1), "x")

    hamlet = analyse_question("Who wrote Hamlet?")
    python = analyse_question("In what year was the Python programming language first released?")
    assert _exact_subject_page(page("Hamlet"), hamlet)
    assert not _exact_subject_page(page("Hamlet (1996 film)"), hamlet)
    assert _exact_subject_page(page("Python (programming language)"), python)

    reader_ = reader()
    aside = _Passage(
        Document("wikipedia", "History", "u", "", 1),
        "1875: Tivadar Puskás (the inventor of the telephone exchange) arrives in the USA.",
        1.0,
        {"1875", "tivadar", "pusk", "invent", "telephon", "exchange", "arriv", "usa"},
    )
    assert not reader_._supported(aside, analyse_question("Who invented the telephone?"))


def test_items_without_an_english_label_are_not_answers() -> None:
    def fetch(url: str, params: Mapping[str, str]) -> Any:
        if params["props"] == "labels":
            return {"entities": {"Q9661": {"id": "Q9661", "labels": {}}}}
        return {
            "entities": {
                "Q1": {
                    "labels": {"en": {"value": "Rust"}},
                    "claims": {
                        "P170": [
                            {
                                "rank": "normal",
                                "mainsnak": {
                                    "snaktype": "value",
                                    "datavalue": {
                                        "type": "wikibase-entityid",
                                        "value": {"id": "Q9661"},
                                    },
                                },
                            }
                        ]
                    },
                }
            }
        }

    assert Wikidata(fetch).claims("Q1", "P170", "creator") == []
