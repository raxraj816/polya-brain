"""Controlled knowledge-acquisition boundaries for PolyaBrain."""

from app.acquisition.artifacts import LocalArtifactInspector, local_artifact_capability
from app.acquisition.capabilities import evidence_evaluator_capability, web_search_capability
from app.acquisition.contracts import (
    DataSourceDefinition,
    DataSourceKind,
    EvidenceCandidate,
    ResearchBudget,
    SearchRequest,
    SearchResponse,
    SearchResultCandidate,
)
from app.acquisition.providers import BraveSearchProvider, SearchProvider, SearchProviderError
from app.acquisition.sources import AvailableDataSourceRegistry

__all__ = [
    "AvailableDataSourceRegistry",
    "BraveSearchProvider",
    "DataSourceDefinition",
    "DataSourceKind",
    "EvidenceCandidate",
    "LocalArtifactInspector",
    "ResearchBudget",
    "SearchProvider",
    "SearchProviderError",
    "SearchRequest",
    "SearchResponse",
    "SearchResultCandidate",
    "evidence_evaluator_capability",
    "local_artifact_capability",
    "web_search_capability",
]
