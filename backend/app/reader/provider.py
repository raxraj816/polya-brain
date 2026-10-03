"""PolyaBrain-owned search for the runtime's research capability (SEARCH_PROVIDER=polya)."""

from __future__ import annotations

from app.acquisition.contracts import SearchRequest, SearchResponse, SearchResultCandidate
from app.acquisition.providers import SearchProviderError
from app.reader.sources import SourceError, Wikipedia
from app.reader.text import BM25, sentences, tokens

PROVIDER_VERSION = "polya_reader_search@0.1.0"


class ReaderSearchProvider:
    """Search Wikipedia directly and return the best verbatim passages per page.

    No language model and no search vendor: titles come from the MediaWiki search
    API, passages are ranked by PolyaBrain's own BM25 over the page text, and every
    excerpt is copied verbatim from the page so downstream evidence checks can quote it.
    """

    name = "polya_reader"
    capability_version = PROVIDER_VERSION

    def __init__(self, wikipedia: Wikipedia) -> None:
        self.wikipedia = wikipedia

    def search(self, request: SearchRequest) -> SearchResponse:
        try:
            titles = self.wikipedia.search(request.query, limit=min(request.max_results, 5))
        except SourceError as exc:
            raise SearchProviderError(str(exc), kind="unavailable", retryable=True) from exc
        query = tokens(request.query)
        candidates: list[SearchResultCandidate] = []
        for rank, title in enumerate(titles, start=1):
            try:
                page = self.wikipedia.page(title, rank)
            except SourceError:
                continue
            if page is None:
                continue
            passages = sentences(page.text)[:1_500]
            if not passages:
                continue
            index = BM25([tokens(p) for p in passages])
            scored = sorted(
                ((index.score(query, i), p) for i, p in enumerate(passages)),
                key=lambda item: item[0],
                reverse=True,
            )
            best = [p for score, p in scored[:4] if score > 0] or passages[:1]
            top_score = scored[0][0] if scored else 0.0
            candidates.append(
                SearchResultCandidate(
                    id=f"polya-reader-{rank}",
                    title=page.title,
                    url=page.url,  # type: ignore[arg-type]
                    excerpt=best[0][:1_000],
                    extra_snippets=[p[:1_000] for p in best[1:]],
                    provider_rank=rank,
                    provider_score=min(1.0, top_score / 20.0) if top_score else None,
                )
            )
        return SearchResponse(
            provider=self.name,
            query=request.query,
            candidates=candidates,
            metadata={"version": PROVIDER_VERSION, "model_calls": 0, "pages_read": len(candidates)},
        )
