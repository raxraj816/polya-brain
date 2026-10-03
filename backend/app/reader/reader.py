"""PolyaBrain Reader: answer factual questions from sources it reads itself.

Pipeline (no language model, no search vendor):
question analysis -> Wikidata typed claims -> Wikipedia search and pages ->
sentence ranking (BM25) -> typed span extraction -> verbatim evidence ->
cross-source agreement -> answer, conflict, or insufficient evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from time import perf_counter

from pydantic import Field

from app.models.contracts import ContractModel
from app.reader.lexicon import (
    ANSWER_DESCRIPTORS,
    CONSTRAINT_WORDS,
    HEDGES,
    MODIFIERS,
    ORGANISATION_WORDS,
    PROPERTY_LABELS,
    RESTRICTIVE,
    SYNONYMS,
    UNIT_WORDS,
    relation_stems,
)
from app.reader.sources import (
    Claim,
    Document,
    LocalCorpus,
    SourceError,
    Wikidata,
    Wikipedia,
    strip_parentheticals,
)
from app.reader.text import (
    BM25,
    STOPWORDS,
    AnswerType,
    QuestionAnalysis,
    analyse_question,
    content_tokens,
    sentences,
    stem,
    tokens,
)

READER_VERSION = "polya_reader@0.1.0"
# Candidates have already passed the subject-and-relation support check; this only
# drops values stated far from the relation in low-ranked sentences.
MIN_SUPPORT_SCORE = 0.2
MONTHS = {
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}
# Capitalised sentence openers that are never part of a name.
LEADING_WORDS = {
    "either",
    "neither",
    "however",
    "although",
    "though",
    "while",
    "both",
    "many",
    "some",
    "most",
    "several",
    "after",
    "before",
    "since",
    "during",
    "because",
    "also",
    "later",
    "earlier",
    "today",
    "according",
    "following",
    "unlike",
    "like",
    "despite",
    "meanwhile",
    "thus",
    "therefore",
    "instead",
    "eventually",
    "originally",
}
_NAME_CONNECTORS = {"da", "de", "di", "van", "von", "der", "del", "la", "le", "bin", "al"}
_UNIT_PATTERNS = {
    "degrees celsius": r"°\s?C|degrees? Celsius",
    "celsius": r"°\s?C|degrees? Celsius",
    "fahrenheit": r"°\s?F|degrees? Fahrenheit",
    "metres per second": r"m/s|metres per second|meters per second|m\s?s[−-]1",
    "meters per second": r"m/s|metres per second|meters per second",
    "metres": r"\bm\b|metres|meters",
    "meters": r"\bm\b|metres|meters",
}


class ReaderStatus(StrEnum):
    CORROBORATED = "corroborated"
    SINGLE_SOURCE = "single_source"
    CONFLICTING = "conflicting"
    INSUFFICIENT = "insufficient_evidence"


class Evidence(ContractModel):
    source: str
    title: str
    url: str
    quote: str = Field(max_length=1_500)
    kind: str  # sentence | structured


class Candidate(ContractModel):
    value: str
    score: float
    sources: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class ReaderAnswer(ContractModel):
    version: str = READER_VERSION
    question: str
    answer: str | None = None
    status: ReaderStatus = ReaderStatus.INSUFFICIENT
    answer_type: str
    evidence: list[Evidence] = Field(default_factory=list)
    alternatives: list[Candidate] = Field(default_factory=list)
    sources_read: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    model_calls: int = 0
    elapsed_ms: float = 0.0


def normalize(value: str) -> str:
    text = value.strip().strip(".,;:").casefold()
    text = re.sub(r"^(the|a|an)\s+", "", text)
    if re.fullmatch(r"[\d,.\s]+", text):
        text = text.replace(",", "").replace(" ", "")
        if text.endswith(".0"):
            text = text[:-2]
    return " ".join(text.split())


@dataclass
class _Passage:
    document: Document
    sentence: str
    score: float = 0.0
    stems: set[str] = field(default_factory=set)
    position: int = 0  # sentence index within its document; small means the lead


def _title_subject(title: str) -> str:
    """'Hamlet (1996 film)' -> 'hamlet': the page's subject without disambiguation."""
    return normalize(re.sub(r"\s*\([^)]*\)\s*$", "", title))


def _exact_subject_page(passage: _Passage, analysis: QuestionAnalysis) -> bool:
    """The page is about the asked entity itself, not a namesake.

    'Python (programming language)' is the subject page for a question about the
    Python programming language, but 'Hamlet (1996 film)' is not the subject page
    for 'Who wrote Hamlet?': a disambiguation qualifier only counts when the
    question itself states it.
    """
    title = passage.document.title
    subject = _title_subject(title)
    if not any(normalize(phrase) == subject for phrase in analysis.entity_phrases):
        return False
    qualifier = re.search(r"\(([^)]*)\)\s*$", title)
    if qualifier is None:
        return True
    question_stems = {stem(t) for t in tokens(analysis.question)}
    return {stem(t) for t in content_tokens(qualifier.group(1))} <= question_stems


class Reader:
    def __init__(
        self,
        wikipedia: Wikipedia | None = None,
        wikidata: Wikidata | None = None,
        corpus: LocalCorpus | None = None,
        *,
        pages: int = 3,
    ) -> None:
        self.wikipedia = wikipedia
        self.wikidata = wikidata
        self.corpus = corpus
        self.pages = pages
        self._property_cache: dict[str, tuple[str, str] | None] = {}

    # ----- structured facts ---------------------------------------------------
    def _property(self, label: str) -> tuple[str, str] | None:
        if label in self._property_cache:
            return self._property_cache[label]
        assert self.wikidata is not None
        found = None
        for item in self.wikidata.find(label, kind="property", limit=5):
            if str(item.get("label", "")).casefold() == label.casefold():
                found = (str(item["id"]), str(item.get("label")))
                break
        self._property_cache[label] = found
        return found

    def _structured(self, analysis: QuestionAnalysis, notes: list[str]) -> list[Claim]:
        if self.wikidata is None:
            return []
        subjects = analysis.entity_phrases or _fallback_subject(analysis.question)
        if len(subjects) != 1:
            if subjects:
                notes.append("Several entities in the question; structured lookup skipped.")
            return []
        labels: list[str] = []
        for term in analysis.property_terms + analysis.key_terms:
            labels.extend(PROPERTY_LABELS.get(term, ()))
        labels = list(dict.fromkeys(labels))
        if not labels:
            return []
        subject_stems = {stem(t) for t in tokens(subjects[0])}
        unaccounted = [
            term
            for term in analysis.property_terms
            if term not in PROPERTY_LABELS
            and term not in ANSWER_DESCRIPTORS
            and term not in MODIFIERS
            and term not in UNIT_WORDS
            and stem(term) not in subject_stems
        ]
        if unaccounted:
            notes.append(
                "Structured lookup skipped: the question also asks about "
                + ", ".join(unaccounted)
                + ", which no single property covers."
            )
            return []
        matches = self.wikidata.find(subjects[0], limit=3)
        named = [m for m in matches if _same_name(str(m.get("label", "")), subjects[0])]
        if not named:
            if matches:
                notes.append(
                    f"Wikidata's best match '{matches[0].get('label', '')}' does not name "
                    f"'{subjects[0]}'."
                )
            return []
        properties = [p for p in (self._property(label) for label in labels) if p is not None]
        # Namesakes share a label (Hamlet the play, a hamlet the settlement); the first
        # same-named entity that actually carries the asked property is the subject.
        for entity in named:
            for prop in properties:
                claims = self.wikidata.claims(str(entity["id"]), prop[0], prop[1])
                claims = [c for c in claims if _claim_fits(c, analysis)]
                if claims:
                    if entity is not named[0]:
                        notes.append(
                            f"Read '{entity.get('label')}' ({entity.get('description', '')}): "
                            "the first namesake has no such property."
                        )
                    return claims
        return []

    # ----- text --------------------------------------------------------------
    def _documents(self, analysis: QuestionAnalysis, notes: list[str]) -> list[Document]:
        documents: list[Document] = []
        if self.corpus is not None:
            documents.extend(self.corpus.documents())
        if self.wikipedia is not None:
            queries = [analysis.query]
            if analysis.entity_phrases:
                queries.append(" ".join(analysis.entity_phrases))
            else:
                # Constraint words keep answers honest but can derail title search
                # ("first person" -> first-person shooters); also search without them.
                plain = " ".join(t for t in analysis.key_terms if t not in CONSTRAINT_WORDS)
                if plain and plain != analysis.query:
                    queries.append(plain)
            results: list[list[str]] = []
            for query in queries:
                try:
                    results.append(self.wikipedia.search(query, limit=self.pages))
                except SourceError as exc:
                    notes.append(f"Wikipedia search unavailable: {exc}")
            # Interleave so every query's best pages are read, not just the first query's.
            titles = [r[i] for i in range(self.pages) for r in results if i < len(r)]
            for rank, title in enumerate(list(dict.fromkeys(titles))[: self.pages + 2], start=1):
                try:
                    page = self.wikipedia.page(title, rank)
                except SourceError as exc:
                    notes.append(f"Could not read '{title}': {exc}")
                    continue
                if page is not None:
                    documents.append(page)
        return documents

    def _supported(self, passage: _Passage, analysis: QuestionAnalysis) -> bool:
        """The sentence must name the question's entities and state its relation.

        Both are judged on the main clause: a parenthetical aside such as
        '(the inventor of the telephone exchange)' describes something else.
        """
        main = {stem(t) for t in tokens(strip_parentheticals(passage.sentence))}
        passage = _Passage(
            passage.document, passage.sentence, passage.score, main, passage.position
        )
        title_stems = {stem(t) for t in tokens(passage.document.title)}
        visible = passage.stems | title_stems
        for phrase in analysis.entity_phrases:
            phrase_stems = {stem(t) for t in content_tokens(phrase)} or {
                stem(t) for t in tokens(phrase)
            }
            if not phrase_stems <= visible:
                return False
        for number in re.findall(r"\b\d{3,4}\b", analysis.question):
            if number not in passage.sentence:
                return False
        for word in analysis.key_terms:
            if word in CONSTRAINT_WORDS and not (relation_stems(word) & passage.stems):
                return False
        for phrase in analysis.entity_phrases:
            phrase_stems = {stem(t) for t in content_tokens(phrase)} or {
                stem(t) for t in tokens(phrase)
            }
            if not phrase_stems <= passage.stems and not _exact_subject_page(passage, analysis):
                return False
        entity_stems = {stem(t) for phrase in analysis.entity_phrases for t in tokens(phrase)}
        relation = [
            t
            for t in analysis.property_terms
            if t not in ANSWER_DESCRIPTORS
            and t not in CONSTRAINT_WORDS
            and t not in UNIT_WORDS
            and stem(t) not in entity_stems
        ]
        if not relation:
            return True
        covered = sum(1 for term in relation if relation_stems(term) & passage.stems)
        return covered / len(relation) >= 0.6

    def _relation_positions(self, sentence: str, analysis: QuestionAnalysis) -> list[int]:
        entity_stems = {stem(t) for phrase in analysis.entity_phrases for t in tokens(phrase)}
        relation: set[str] = set()
        for term in analysis.property_terms:
            if term in ANSWER_DESCRIPTORS or stem(term) in entity_stems:
                continue
            relation |= relation_stems(term)
        words = [stem(w) for w in tokens(sentence)]
        return [i for i, w in enumerate(words) if w in relation]

    def _weight(self, passage: _Passage, analysis: QuestionAnalysis, value: str) -> float:
        """Prefer values stated next to the asked relation, on the subject's own page."""
        sentence = strip_parentheticals(passage.sentence)
        words = tokens(sentence)
        value_tokens = tokens(value)
        positions = [
            i
            for i in range(len(words))
            if value_tokens and words[i : i + len(value_tokens)] == value_tokens
        ]
        anchors = self._relation_positions(sentence, analysis)
        proximity = 1.0
        if positions and anchors:
            distance = min(abs(p - a) for p in positions for a in anchors)
            proximity = 1.0 / (1.0 + distance / 3.0)
        subject_page = 1.5 if _exact_subject_page(passage, analysis) else 1.0
        lead = 1.5 if passage.position < 5 else 1.0
        hedged = 0.3 if {w.lower() for w in words} & HEDGES else 1.0
        phrase = 1.5 if _states_question_phrase(words, analysis) else 1.0
        narrowed = 0.3 if _narrowed_record(sentence, analysis) else 1.0
        return proximity * subject_page * lead * hedged * phrase * narrowed

    def _extract(self, passage: _Passage, analysis: QuestionAnalysis) -> list[str]:
        sentence = strip_parentheticals(passage.sentence)
        question_numbers = set(re.findall(r"\d+", analysis.question))
        question_stems = {stem(t) for t in tokens(analysis.question)}
        kind = analysis.answer_type
        if kind in {AnswerType.YEAR, AnswerType.DATE}:
            return [
                y
                for y in re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", sentence)
                if y not in question_numbers
            ]
        if kind is AnswerType.QUANTITY:
            unit = _UNIT_PATTERNS.get(analysis.unit_hint or "")
            pattern = (
                r"(\d[\d,]*(?:\.\d+)?)\s*(?:" + unit + ")" if unit else r"(\d[\d,]*(?:\.\d+)?)"
            )
            return [m for m in re.findall(pattern, sentence) if m not in question_numbers]
        if kind is AnswerType.NUMBER:
            values = []
            words = sentence.split()
            anchors = [
                i
                for i, w in enumerate(words)
                if stem(w.strip(".,;:").lower()) in {stem(t) for t in analysis.property_terms}
            ]
            for index, word in enumerate(words):
                raw = word.strip(".,;:()")
                is_number = (
                    bool(re.fullmatch(r"\d[\d,]*(\.\d+)?", raw)) and raw not in question_numbers
                )
                is_year = bool(re.fullmatch(r"1[0-9]{3}|20[0-9]{2}", raw))
                near = not anchors or min(abs(index - a) for a in anchors) <= 6
                if is_number and near and (not is_year or "population" in analysis.property_terms):
                    values.append(raw)
            return values
        names = []
        for match in re.finditer(
            r"[A-Z][\w'’\-]*(?:\s+(?:(?:" + "|".join(_NAME_CONNECTORS) + r")\s+)?[A-Z][\w'’\-]*)*",
            sentence,
        ):
            name = match.group(0).strip()
            parts = name.split()
            while parts and (
                parts[0].lower() in MONTHS | LEADING_WORDS or parts[0].lower() in STOPWORDS
            ):
                parts = parts[1:]
            name = " ".join(parts)
            if not name:
                continue
            name_stems = {stem(t) for t in tokens(name)}
            if name_stems & question_stems:
                continue
            # A lone surname ('Bell') is kept only to credit a full name read elsewhere.
            if kind is AnswerType.PERSON and not 1 <= len(parts) <= 4:
                continue
            if kind is AnswerType.PERSON and {p.lower() for p in parts} & ORGANISATION_WORDS:
                continue
            if kind is not AnswerType.PERSON and len(parts) > 4:
                continue
            names.append(name)
        return names

    def answer(self, question: str) -> ReaderAnswer:
        started = perf_counter()
        analysis = analyse_question(question)
        notes: list[str] = []
        result = ReaderAnswer(question=analysis.question, answer_type=analysis.answer_type.value)
        candidates: dict[str, Candidate] = {}

        try:
            claims = self._structured(analysis, notes)
        except SourceError as exc:
            claims = []
            notes.append(f"Wikidata unavailable: {exc}")
        structured_values = []
        for claim in claims:
            value = claim.value
            key = normalize(value)
            evidence = Evidence(
                source="wikidata",
                title=f"{claim.entity_label} — {claim.property_label}",
                url=claim.url,
                quote=f"{claim.entity_label}: {claim.property_label} = {value}"
                + (f" ({claim.qualifier})" if claim.qualifier else ""),
                kind="structured",
            )
            candidate = candidates.setdefault(key, Candidate(value=value, score=0.0))
            candidate.score += 3.0
            candidate.sources.append("wikidata")
            candidate.evidence.append(evidence)
            structured_values.append(key)

        documents = self._documents(analysis, notes)
        result.sources_read = [f"{d.source}: {d.title}" for d in documents]
        passages = [
            _Passage(document=d, sentence=s, position=i)
            for d in documents
            for i, s in enumerate(sentences(d.text)[:1_500])
        ]
        if passages:
            index = BM25([tokens(p.sentence) for p in passages])
            # Rank with the relation's synonyms too, so "written by" can answer "who wrote".
            query = list(analysis.key_terms)
            for term in analysis.property_terms:
                query.extend(w for phrase in SYNONYMS.get(term, ()) for w in phrase.split())
            for position, passage in enumerate(passages):
                passage.score = index.score(query, position)
                passage.stems = {stem(t) for t in tokens(passage.sentence)}
            ranked = sorted(passages, key=lambda p: p.score, reverse=True)[:60]
            # A subject page's opening sentences define the subject; always read them.
            ranked += [
                p
                for p in passages
                if p.position < 5 and p not in ranked and _exact_subject_page(p, analysis)
            ]
            best = ranked[0].score or 1.0
            # Each source counts once, by its strongest supporting sentence.
            strongest: dict[tuple[str, str], float] = {}
            for passage in ranked:
                if passage.score <= 0 or not self._supported(passage, analysis):
                    continue
                for value in self._extract(passage, analysis):
                    key = normalize(value)
                    if not key:
                        continue
                    candidate = candidates.setdefault(key, Candidate(value=value, score=0.0))
                    source_id = f"{passage.document.source}:{passage.document.title}"
                    weight = (passage.score / best) * self._weight(passage, analysis, value)
                    evidence = Evidence(
                        source=passage.document.source,
                        title=passage.document.title,
                        url=passage.document.url,
                        quote=passage.sentence[:1_500],
                        kind="sentence",
                    )
                    previous = strongest.get((key, source_id))
                    if previous is None:
                        candidate.sources.append(source_id)
                        candidate.score += weight
                        candidate.evidence.append(evidence)
                        strongest[(key, source_id)] = weight
                    elif weight > previous:
                        candidate.score += weight - previous
                        strongest[(key, source_id)] = weight
                        slot = next(
                            i
                            for i, item in enumerate(candidate.evidence)
                            if item.kind == "sentence"
                            and f"{item.source}:{item.title}" == source_id
                        )
                        candidate.evidence[slot] = evidence

            if analysis.answer_type is AnswerType.PERSON:
                _merge_surnames(candidates, strongest)

        ordered = sorted(candidates.values(), key=lambda c: c.score, reverse=True)
        result.elapsed_ms = (perf_counter() - started) * 1000
        result.notes = notes
        if not ordered or ordered[0].score < MIN_SUPPORT_SCORE:
            result.notes.append(
                "No source sentence both names the question's subject and states the asked relation."
            )
            return result
        top = ordered[0]
        if (
            structured_values
            and len(structured_values) > 1
            and normalize(top.value) in structured_values
        ):
            # Several structured values (e.g. co-founders) are all part of the answer.
            joined = [candidates[key] for key in dict.fromkeys(structured_values)]
            result.answer = "; ".join(c.value for c in joined)
            result.evidence = [e for c in joined for e in c.evidence][:8]
            independent = {s.split(":", 1)[0] for c in joined for s in c.sources}
            result.status = (
                ReaderStatus.CORROBORATED
                if len(independent) > 1 or any(len(c.sources) > 1 for c in joined)
                else ReaderStatus.SINGLE_SOURCE
            )
            result.alternatives = [
                c for c in ordered if normalize(c.value) not in structured_values
            ][:3]
            return result
        result.answer = top.value
        result.evidence = top.evidence[:6]
        result.alternatives = ordered[1:4]
        rival = ordered[1] if len(ordered) > 1 else None
        if (
            rival is not None
            and rival.score >= 0.8 * top.score
            and not set(rival.sources) <= set(top.sources)
        ):
            result.status = ReaderStatus.CONFLICTING
            result.notes.append(
                f"Sources also support '{rival.value}' almost as strongly; check before relying on either."
            )
        elif len(top.sources) >= 2:
            result.status = ReaderStatus.CORROBORATED
        else:
            result.status = ReaderStatus.SINGLE_SOURCE
        return result


def _merge_surnames(
    candidates: dict[str, Candidate], strongest: dict[tuple[str, str], float]
) -> None:
    """Credit 'Bell' to 'Alexander Graham Bell' when exactly one full name ends with it.

    Each source still counts once, by its strongest sentence for either form. A lone
    surname that matches no full name, or several, is dropped rather than guessed.
    """
    full = {k: c for k, c in candidates.items() if len(c.value.split()) >= 2}
    for key, alias in list(candidates.items()):
        if key in full or "wikidata" in alias.sources:
            continue
        del candidates[key]
        owners = [k for k, c in full.items() if c.value.split()[-1].casefold() == key]
        if len(owners) != 1:
            continue
        owner = candidates[owners[0]]
        for source in alias.sources:
            gained = strongest.get((key, source), 0.0)
            held = strongest.get((owners[0], source))
            if held is None:
                owner.sources.append(source)
                owner.score += gained
                owner.evidence.extend(
                    e for e in alias.evidence if f"{e.source}:{e.title}" == source
                )
                strongest[(owners[0], source)] = gained
            elif gained > held:
                owner.score += gained - held
                strongest[(owners[0], source)] = gained


def _states_question_phrase(words: list[str], analysis: QuestionAnalysis) -> bool:
    """The sentence repeats a 3+ word run of the question, e.g. 'first person in space'."""
    asked = tokens(analysis.question)
    content = set(analysis.key_terms)
    runs = {
        tuple(asked[i : i + 3])
        for i in range(len(asked) - 2)
        if content & set(asked[i : i + 3]) and asked[i] not in STOPWORDS
    }
    return any(tuple(words[i : i + 3]) in runs for i in range(len(words) - 2))


_CLAUSE_END = frozenset({"was", "is", "were", "are", "became", "becomes", "has", "had"})


def _narrowed_record(sentence: str, analysis: QuestionAnalysis) -> bool:
    """'The first person born in Africa to fly in space' answers a narrower question.

    In the phrase a constraint word (first, largest, ...) opens, up to the asked
    relation or the end of the clause, a proper noun or restrictive word the question
    never mentioned changes which record is meant.
    """
    asked = set(tokens(analysis.question))
    relation = {
        stem(t)
        for t in analysis.property_terms
        if t not in CONSTRAINT_WORDS and t not in ANSWER_DESCRIPTORS
    }
    pieces = re.findall(r"[A-Za-z0-9]+(?:['\-][A-Za-z0-9]+)*|[,;:()]", sentence)
    for i, piece in enumerate(pieces):
        if piece.lower() not in CONSTRAINT_WORDS or piece.lower() not in asked:
            continue
        for word in pieces[i + 1 : i + 9]:
            low = word.lower()
            if not word[:1].isalnum() or low in _CLAUSE_END or stem(low) in relation:
                break
            if low in asked:
                continue
            if low in RESTRICTIVE or word[:1].isupper():
                return True
    return False


def _fallback_subject(question: str) -> list[str]:
    match = re.search(
        r"\b(?:of|for)\s+(?:the\s+)?([a-z][a-z ]{2,40}?)(?:\s+(?:in|at|on)\b|\?|$)",
        question.lower(),
    )
    return [match.group(1).strip()] if match else []


def _same_name(label: str, phrase: str) -> bool:
    a, b = {stem(t) for t in tokens(label)}, {stem(t) for t in tokens(phrase)}
    return bool(a) and (a <= b or b <= a)


def _claim_fits(claim: Claim, analysis: QuestionAnalysis) -> bool:
    kind = analysis.answer_type
    if kind in {AnswerType.YEAR, AnswerType.DATE}:
        return claim.kind == "time"
    if kind in {AnswerType.NUMBER, AnswerType.QUANTITY}:
        return claim.kind == "quantity"
    return claim.kind in {"item", "string"}


def render(answer: ReaderAnswer) -> str:
    status = {
        ReaderStatus.CORROBORATED: "Corroborated by independent sources",
        ReaderStatus.SINGLE_SOURCE: "Supported by one source",
        ReaderStatus.CONFLICTING: "Sources conflict",
        ReaderStatus.INSUFFICIENT: "Insufficient evidence",
    }[answer.status]
    lines = [
        f"# {answer.answer or 'No answer found'}",
        "",
        f"**Question:** {answer.question}",
        "",
        f"**Status:** {status}",
        "",
    ]
    if answer.evidence:
        lines += ["## Evidence (verbatim)", ""]
        for item in answer.evidence:
            lines += [f"> {item.quote}", f"> — [{item.title}]({item.url})", ""]
    if answer.alternatives:
        lines += ["## Other candidates", ""]
        lines += [
            f"- {c.value} (score {c.score:.2f}, {len(c.sources)} source(s))"
            for c in answer.alternatives
        ]
        lines.append("")
    if answer.notes:
        lines += ["## Notes", "", *[f"- {note}" for note in answer.notes], ""]
    lines += [
        "## How this was found",
        "",
        f"PolyaBrain Reader ({answer.version}) read these sources itself, with no language model and no "
        f"search vendor: {', '.join(answer.sources_read) or 'none'}. Every answer above is a verbatim "
        f"sentence or a structured Wikidata claim. Answer type: {answer.answer_type}. "
        f"{answer.elapsed_ms / 1000:.1f}s.",
        "",
    ]
    return "\n".join(lines)
