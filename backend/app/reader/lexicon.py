"""Explicit, inspectable relation knowledge used by the Reader (no learned model).

Two small tables: which Wikidata property labels a question word usually asks
about, and which words in a sentence state the same relation. They describe
general relations (authorship, founding, location, quantities), never answers.
"""

from __future__ import annotations

from app.reader.text import stem

# Question word -> Wikidata property labels to try, most specific first.
PROPERTY_LABELS: dict[str, tuple[str, ...]] = {
    "wrote": ("author",),
    "written": ("author",),
    "author": ("author",),
    "created": ("creator", "developer", "designed by", "founded by"),
    "creator": ("creator", "developer"),
    "founded": ("founded by",),
    "founder": ("founded by",),
    "invented": ("discoverer or inventor", "inventor"),
    "inventor": ("discoverer or inventor",),
    "painted": ("creator",),
    "developed": ("developer", "creator", "discoverer or inventor"),
    "designed": ("designed by", "architect"),
    "discovered": ("discoverer or inventor",),
    "capital": ("capital",),
    "language": ("official language",),
    "currency": ("currency",),
    "population": ("population",),
    "symbol": ("element symbol",),
    "atomic": ("atomic number",),
    "located": ("country", "located in the administrative territorial entity"),
    "released": ("publication date", "inception"),
    "boiling": ("boiling point",),
    "melting": ("melting point",),
    "tall": ("height", "elevation above sea level"),
    "height": ("height", "elevation above sea level"),
    "elevation": ("elevation above sea level",),
    "born": ("date of birth",),
    "died": ("date of death",),
}

# A relation word -> words that state the same relation in prose.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "wrote": ("wrote", "written", "author", "writer", "novel", "by"),
    "written": ("written", "wrote", "author", "by"),
    "created": (
        "created",
        "creator",
        "designed",
        "developed",
        "initiated",
        "started",
        "began",
        "conceived",
    ),
    "founded": ("founded", "founder", "cofounded", "co-founded", "established"),
    "invented": ("invented", "inventor", "credited", "created", "proposed"),
    "painted": ("painted", "painter", "painting", "by"),
    "developed": ("developed", "developer", "published", "formulated", "proposed", "created"),
    "designed": ("designed", "designer", "architect", "engineered"),
    "discovered": ("discovered", "discoverer", "discovery"),
    "released": (
        "released",
        "release",
        "launched",
        "published",
        "introduced",
        "unveiled",
        "appeared",
    ),
    "launched": ("launched", "released", "launch"),
    "land": ("landed", "landing", "land"),
    "walk": ("walk", "walked", "step", "stepped", "walking"),
    "located": ("located", "situated", "lies", "in"),
    "fall": ("fall", "fell", "opened", "breach", "collapse"),
    "end": ("ended", "end", "surrender", "concluded", "ending"),
    "largest": ("largest", "biggest", "most massive"),
    "tallest": ("tallest", "highest"),
    "tall": ("tall", "height", "high", "tallest"),
    "high": ("high", "height", "tall", "elevation"),
    "won": ("won", "winner", "champion", "champions", "victory"),
    "visit": ("visited", "visit", "travelled", "traveled"),
}

# Words that describe the expected answer rather than the relation; a supporting
# sentence need not contain them.
ANSWER_DESCRIPTORS = frozenset(
    {
        "year",
        "date",
        "country",
        "city",
        "person",
        "place",
        "number",
        "name",
        "many",
        "much",
        "people",
        "total",
        "value",
        "located",
        "novel",
        "programming",
    }
)


# Ordinals and superlatives change which entity is meant; a supporting sentence
# must contain them (with their synonyms).
CONSTRAINT_WORDS = frozenset(
    {
        "first",
        "last",
        "largest",
        "biggest",
        "smallest",
        "tallest",
        "highest",
        "longest",
        "oldest",
        "youngest",
        "earliest",
        "latest",
        "only",
        "second",
        "third",
    }
)

# Unit words describe the answer's scale, not a relation.
UNIT_WORDS = frozenset(
    {
        "metres",
        "meters",
        "metre",
        "meter",
        "kilometres",
        "kilometers",
        "celsius",
        "fahrenheit",
        "degrees",
        "seconds",
        "kilograms",
        "feet",
        "miles",
        "years",
    }
)

# Hedged or counterfactual statements are weak evidence for what is the case.
HEDGES = frozenset(
    {
        "would",
        "could",
        "might",
        "if",
        "proposed",
        "planned",
        "hypothetical",
        # Contested statements: report the dispute, do not answer from it.
        "whether",
        "controversy",
        "disputed",
        "allegedly",
        "reportedly",
    }
)

# Modifiers that narrow a relation without naming one.
MODIFIERS = frozenset({"chemical", "official", "main", "primary", "national", "adult", "human"})

# Words that narrow "the first person in space" to a different record
# ("the first woman in space", "the first person born in Africa to fly in space").
RESTRICTIVE = frozenset(
    {"woman", "women", "female", "male", "born", "civilian", "private", "paying", "tourist"}
)

# Capitalised phrases that name institutions, events or works, never a person.
ORGANISATION_WORDS = frozenset(
    {
        "force",
        "army",
        "navy",
        "company",
        "corporation",
        "university",
        "institute",
        "agency",
        "union",
        "party",
        "republic",
        "kingdom",
        "ministry",
        "committee",
        "council",
        "society",
        "association",
        "museum",
        "school",
        "college",
        "bank",
        "inc",
        "ltd",
        "group",
        "department",
        "office",
        "administration",
        "program",
        "programme",
        "mission",
        "award",
        "prize",
        "war",
        "act",
        "treaty",
        "church",
        "states",
        "nations",
    }
)


def relation_stems(term: str) -> set[str]:
    words = SYNONYMS.get(term, ()) + (term,)
    return {stem(part) for word in words for part in word.split()}
