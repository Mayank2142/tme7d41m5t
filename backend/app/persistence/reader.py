"""Read-only adapter; callers resolve a release once and reuse that exact ID."""

from sqlalchemy import Engine

from backend.app.domain.sources import SourceIndex
from backend.app.persistence.analysis import resolve_release, source_index
from backend.app.persistence.releases import release_provenance


class DatasetReader:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def release(self, release_id: str | None) -> dict:
        return resolve_release(self.engine, release_id)

    def forecasts(self, release_id: str) -> SourceIndex:
        return source_index(self.engine, release_id, "WINDFOR")

    def actuals(self, release_id: str) -> SourceIndex:
        return source_index(self.engine, release_id, "FUELHH")

    def provenance(self, release_id: str) -> list[dict]:
        return release_provenance(self.engine, release_id)
