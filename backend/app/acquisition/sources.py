"""Registry of observable sources available to one PolyaBrain composition."""

from __future__ import annotations

from app.acquisition.contracts import DataSourceDefinition


class AvailableDataSourceRegistry:
    """Prevent the gap detector from inventing unavailable data sources."""

    def __init__(self) -> None:
        self._sources: dict[str, DataSourceDefinition] = {}

    def register(self, source: DataSourceDefinition) -> None:
        """Register one stable source definition."""
        if source.name in self._sources:
            raise ValueError(f"data source already registered: {source.name}")
        self._sources[source.name] = source

    def available(self) -> tuple[DataSourceDefinition, ...]:
        """Return only usable sources in deterministic order."""
        return tuple(
            self._sources[name] for name in sorted(self._sources) if self._sources[name].available
        )

    def prompt_description(self) -> str:
        """Expose a compact source inventory to bounded gap detection."""
        return "; ".join(
            f"{source.name} ({source.kind.value}): {source.description}"
            for source in self.available()
        )
