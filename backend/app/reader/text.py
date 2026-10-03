"""Deterministic text tools: tokens, sentences, BM25 ranking and question analysis."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum

STOPWORDS = frozenset(
    [
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "whose",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
    ]
)
WH_WORDS = frozenset({"what", "when", "where", "which", "who", "whom", "whose", "why", "how"})


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+(?:['\-][a-z0-9]+)*", text.lower())]


def content_tokens(text: str) -> list[str]:
    return [t for t in tokens(text) if t not in STOPWORDS and t not in WH_WORDS and len(t) > 1]


def stem(token: str) -> str:
    """A light suffix stripper so 'founded'/'founder' and 'released'/'release' meet."""
    for suffix in ("ations", "ation", "ings", "ing", "ers", "er", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    # 'invention'/'inventor' meet 'invented'; short words like 'region' stay whole.
    for suffix in ("ion", "or"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


_ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "Mr.", "Mrs.", "Dr.", "St.", "vs.", "c.", "ca.", "No.")


def sentences(text: str) -> list[str]:
    """Split plain text into sentences without breaking common abbreviations or decimals."""
    protected = text
    for abbreviation in _ABBREVIATIONS:
        protected = protected.replace(abbreviation, abbreviation.replace(".", "\x00"))
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])|\n{2,}|\n(?=[A-Z])", protected)
    out = []
    for part in parts:
        cleaned = " ".join(part.replace("\x00", ".").split())
        if 20 <= len(cleaned) <= 1200:
            out.append(cleaned)
    return out


class BM25:
    """Okapi BM25 over a small in-memory collection of passages."""

    def __init__(self, documents: list[list[str]], k1: float = 1.4, b: float = 0.75) -> None:
        self.documents = [[stem(t) for t in doc] for doc in documents]
        self.k1, self.b = k1, b
        self.lengths = [len(doc) for doc in self.documents]
        self.average = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        self.frequencies = [Counter(doc) for doc in self.documents]
        df: Counter[str] = Counter()
        for doc in self.documents:
            df.update(set(doc))
        n = len(self.documents)
        self.idf = {
            term: math.log(1 + (n - count + 0.5) / (count + 0.5)) for term, count in df.items()
        }

    def score(self, query: list[str], index: int) -> float:
        terms = [stem(t) for t in query]
        freq, length = self.frequencies[index], self.lengths[index]
        total = 0.0
        for term in terms:
            tf = freq.get(term, 0)
            if not tf:
                continue
            norm = 1 - self.b + self.b * (length / self.average if self.average else 1.0)
            total += self.idf.get(term, 0.0) * tf * (self.k1 + 1) / (tf + self.k1 * norm)
        return total


class AnswerType(StrEnum):
    YEAR = "year"
    DATE = "date"
    NUMBER = "number"
    QUANTITY = "quantity"
    PERSON = "person"
    PLACE = "place"
    TERM = "term"


_TYPE_RULES: tuple[tuple[str, AnswerType], ...] = (
    (r"\b(what|which|in what|in which) year\b|\bwhat date\b", AnswerType.YEAR),
    (r"^\s*when\b", AnswerType.YEAR),
    (
        r"\bhow (tall|high|long|far|heavy|deep|wide|fast)\b|\bspeed of\b|\bboiling point\b|\bmelting point\b",
        AnswerType.QUANTITY,
    ),
    (r"\bhow (many|much)\b|\bnumber of\b|\bpopulation\b|\batomic number\b", AnswerType.NUMBER),
    (
        r"^\s*(who|whom)\b|\bwho (wrote|created|founded|invented|painted|developed|discovered|designed)\b",
        AnswerType.PERSON,
    ),
    (
        r"^\s*where\b|\bin (which|what) (country|city|state|continent|region)\b|\bcapital of\b",
        AnswerType.PLACE,
    ),
)


@dataclass(frozen=True)
class QuestionAnalysis:
    question: str
    answer_type: AnswerType
    key_terms: list[str]
    entity_phrases: list[str]
    property_terms: list[str]
    unit_hint: str | None = None
    query: str = ""
    notes: list[str] = field(default_factory=list)


def _entities(question: str) -> list[str]:
    """Capitalised phrases and quoted titles, excluding a sentence-initial wh-word."""
    found = re.findall(r"[\"“]([^\"”]{2,80})[\"”]", question)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-']*|[^\sA-Za-z0-9]", question)
    phrase: list[str] = []
    connectors = {"of", "and", "the", "de", "da", "von", "van"}
    for index, word in enumerate(words):
        capital = word[:1].isupper() or (word[:1].isdigit() and phrase)
        if (
            capital
            and not (index == 0 and word.lower() in WH_WORDS | {"in", "the", "what", "how"})
            or phrase
            and word.lower() in connectors
            and index + 1 < len(words)
            and words[index + 1][:1].isupper()
        ):
            phrase.append(word)
        else:
            if phrase:
                found.append(" ".join(phrase))
            phrase = []
    if phrase:
        found.append(" ".join(phrase))
    cleaned = []
    for item in found:
        item = re.sub(r"^(The|A|An|In|What|Which|Who|When|Where|How)\s+", "", item).strip(" ?.,")
        if item and item.lower() not in STOPWORDS:
            cleaned.append(item)
    return list(dict.fromkeys(cleaned))


def analyse_question(question: str) -> QuestionAnalysis:
    lowered = question.lower()
    answer_type = AnswerType.TERM
    for pattern, kind in _TYPE_RULES:
        if re.search(pattern, lowered):
            answer_type = kind
            break
    entities = _entities(question)
    entity_tokens = {t for phrase in entities for t in tokens(phrase)}
    key_terms = content_tokens(question)
    property_terms = [t for t in key_terms if t not in entity_tokens]
    unit = None
    unit_match = re.search(
        r"\bin (degrees celsius|celsius|fahrenheit|metres per second|meters per second|metres|meters|kilometres|kilometers|kilograms|years|feet|miles)\b",
        lowered,
    )
    if unit_match:
        unit = unit_match.group(1)
    query = " ".join(dict.fromkeys(key_terms))
    return QuestionAnalysis(
        question=question.strip(),
        answer_type=answer_type,
        key_terms=key_terms,
        entity_phrases=entities,
        property_terms=property_terms,
        unit_hint=unit,
        query=query or question.strip(),
    )
