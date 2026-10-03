# Chapter 176 — PolyaBrain Reader: owned retrieval and reading

Status: implemented, unit-tested offline, and evaluated once on a frozen question set
against live Wikipedia and Wikidata (trusted precision 0.75). Parked as an optional
capability by founder direction: rent tools, own the brain. Binding decision: master plan, "Chapter 176".

## Why

Answering a factual question should not require a rented model or a paid search API.
PolyaBrain now decides what to search, reads the sources itself, extracts the answer
deterministically, and shows the verbatim sentence or the structured claim it relied
on. It does **not** try to be a web search engine: crawling, freshness and ranking at
web scale are out of scope. It owns the *reading* of sources it chooses: Wikipedia,
Wikidata and a local corpus the user supplies. A general search engine can later be
one optional, pluggable source; it is never required.

## What runs

```bash
./polyabrain lookup "What is the capital of Australia?"
./polyabrain lookup --corpus ./runbooks --no-web "When was the payments service migrated?"
```

The pipeline lives in `backend/app/reader`. No language model is involved anywhere:
every answer reports `model_calls: 0`.

1. **Question analysis** (`text.py`): the answer type (year, date, number, quantity,
   person, place or term), entity phrases, relation terms, unit hints, and a search
   query, all derived deterministically.
2. **Structured facts** (`reader.py`, `sources.py`): when the question names exactly
   one subject and its relation maps to a Wikidata property (`lexicon.py`), the
   Reader reads typed claims (times, quantities, items, strings, with "as of"
   qualifiers). Namesakes are handled: the first same-named entity that actually
   carries the property is used, and the note says so. The lookup is skipped when
   the question asks about something no single property covers (for example "walk
   on the capital of Australia"), so a false premise cannot borrow a real fact.
3. **Reading text**: Wikipedia pages from several search queries are interleaved.
   When the question has no named entity, a second query drops constraint words so
   that "first person in space" does not find first-person shooters. Pages are
   split into sentences and ranked with BM25, with the relation's synonyms added to
   the query. The opening sentences of the subject's own page are always read.
4. **Support** (`_supported`): a sentence counts only when its main clause names the
   question's entities and states the asked relation. Parenthetical asides are
   ignored. Numbers in the question and constraint words (first, largest, only, ...)
   are mandatory. A namesake page such as "Hamlet (1996 film)" counts as the
   subject's page only when the question states its qualifier.
5. **Extraction and weighting**: typed spans (years, quantities, numbers, names).
   Each candidate is weighted by:
   - proximity to the relation words;
   - whether it appears on the subject's own page;
   - whether it appears in the page's lead sentences;
   - verbatim repetition of a three-word run of the question;
   - a penalty for hedged or contested statements ("would", "whether", "controversy");
   - a penalty for narrower records. "The first person born in Africa to fly in
     space" does not answer "the first person in space".

   Organisation names are not people. A lone surname ("Bell") credits the single
   full name it belongs to, or is dropped.
6. **Status**: each source counts once, by its strongest sentence. Structured and
   text agreement, or two pages agreeing, gives **corroborated**. One source gives
   **single source**. A rival from other sources scoring at least 80% of the top
   answer gives **conflicting**, and both are shown. Below the support floor the
   answer is **insufficient evidence** rather than a guess. Exit codes: 0 answered,
   3 conflicting, 4 insufficient.

Outputs: `answer.json` and `report.md` under `runs/reader/<run-id>/`. Every piece of
evidence is either a verbatim quote with its page URL or a Wikidata claim with its
entity and property URL.

`SEARCH_PROVIDER=polya` makes the runtime's research capability use
`ReaderSearchProvider`. It searches Wikipedia directly, ranks passages with BM25, and
returns verbatim excerpts with no vendor and no model.

## Source etiquette

All network access goes through `PoliteFetcher`, which handles the following:

- **Pacing.** Wikimedia allows clients without contact details about 10 requests a
  minute, and identified clients about 200. The fetcher paces to 6.5 s per request
  by default, or 0.35 s when `READER_CONTACT` names a contact URL or email for the
  User-Agent. PolyaBrain never invents a contact.
- **Rate limits.** It retries once after 429 or 503, honouring `Retry-After`. It
  stops with a clear message instead of hanging when asked to wait over 60 s.
- **Bounds.** Responses are bounded at 4 MB.
- **Caching.** Responses are cached in memory and on disk (`READER_CACHE_DIR`,
  default `runs/reader-cache`), so repeated questions and evaluations are offline
  and deterministic.

## Development discipline

The frozen set (`evals/reader/questions.json`, sha256 in `FREEZE.json`) was written
before any Reader code. The reading rules were developed on a separate set of 12
development questions, which were never frozen and are listed in the result
section. The rules are general (proximity, subject pages, hedges, narrowed records,
asides, namesakes, surname credit), but the synonym and property lexicon was written
by the same agent who wrote the frozen questions, so overlap is possible. Treat the
frozen result as an honest first measurement, not a benchmark.

## Result

Development set (12 questions, used to shape the rules): 10 of 11 answerable correct
and the false-premise question abstained. "Who invented the telephone?" ends as
**conflicting** (Elisha Gray vs Alexander Graham Bell): a contested question,
flagged rather than answered confidently.

Frozen set, run once (`runs/reader-eval/frozen-1`, anonymous pacing, 248 source
requests, 0 model calls):

| Outcome | Count |
| --- | --- |
| Correct, trusted (corroborated or single source) | 18 / 27 |
| **Wrong, trusted** | **6 / 27** |
| Answered but flagged conflicting (wrong) | 1 / 27 |
| Abstained on an answerable question | 2 / 27 |
| Abstained on an unanswerable question | 6 / 7 |
| **Answered an unanswerable question** | **1 / 7** |

Trusted precision is **0.75**: one trusted answer in four is wrong. That is not good
enough for answers a user would rely on. The misses are typical of deterministic
extraction:

- **Nearby wrong values.** Apollo 11 → 1959, Berlin Wall → 1990 (flagged), and the
  unobtainium boiling point → 100.
- **Wrong entity type.** Mount Everest → "Asia", Eiffel Tower → "France".
- **Wrong person.** Microsoft founder → Melinda French Gates.
- **Possessive left on a name.** "Neil Armstrong's".
- **Raw Wikidata ids.** Rust → "Q9661; …", ids whose items have no English label.
  This was fixed after the run: unlabeled items are dropped. That is a correctness
  fix, not a rescore.

## Decision after the result (founder direction, 2026-10-02)

PolyaBrain rents trusted tools (models, web search, sandboxes) and owns the brain:
choosing what to learn and which tools to use, experimenting, verifying and remembering. Building
its own infrastructure waits until there are resources. The Reader therefore stays
as an **optional, opt-in** capability: `lookup`, `SEARCH_PROVIDER=polya`, and a free
fallback when no search provider is configured. It is not a direction for further
investment and it is never the default. What carries forward is its discipline, to
apply over results from any rented search provider:

- verbatim evidence;
- corroboration across independent sources;
- conflicts flagged;
- abstention instead of guessing.
