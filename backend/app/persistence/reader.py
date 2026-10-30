"""Read-only adapter; callers resolve a release once and reuse that exact ID."""

from sqlalchemy import Engine

from backend.app.cache import BoundedCache
from backend.app.domain.sources import SourceIndex
from backend.app.persistence.analysis import resolve_release, source_index
from backend.app.persistence.releases import release_provenance


class DatasetReader:
    def __init__(self, engine: Engine, cache_mb: int = 32) -> None:
        self.engine = engine
        self._sources = BoundedCache[SourceIndex](max_entries=4, max_bytes=cache_mb * 1024**2)

    def release(self, release_id: str | None) -> dict:
        return resolve_release(self.engine, release_id)

    def forecasts(self, release_id: str) -> SourceIndex:
        return self._index(release_id, "WINDFOR")

    def actuals(self, release_id: str) -> SourceIndex:
        return self._index(release_id, "FUELHH")

    def _index(self, release_id, dataset):
        return self._sources.get(
            (release_id, dataset),
            lambda: source_index(self.engine, release_id, dataset),
            lambda index: index.cache_weight,
        )

    def provenance(self, release_id: str) -> list[dict]:
        return release_provenance(self.engine, release_id)
