"""Pin one accepted release before adapting its immutable members to the domain."""

import re
from dataclasses import dataclass

from sqlalchemy import Engine, select

from backend.app.domain.sources import Dataset, SourceIndex, SourceVersion
from backend.app.persistence.models import ActiveRelease, DatasetRelease
from backend.app.persistence.releases import release_versions


@dataclass(frozen=True)
class AnalysisSources:
    release_id: str
    parser_version: str
    forecasts: SourceIndex
    actuals: SourceIndex


class ReleaseNotFound(ValueError):
    pass


class NoAcceptedRelease(ValueError):
    pass


def resolve_release(engine: Engine, release_id: str | None = None) -> dict:
    if release_id is not None and not re.fullmatch(r"[0-9a-f]{64}", release_id):
        raise ValueError("Release ID must be a full lowercase SHA-256 identifier")
    query = select(
        DatasetRelease.id,
        DatasetRelease.parser_version,
        DatasetRelease.created_at,
        DatasetRelease.quality,
    ).where(DatasetRelease.status == "accepted")
    if release_id is None:
        query = query.join(ActiveRelease, ActiveRelease.release_id == DatasetRelease.id).where(
            ActiveRelease.name == "january_2026"
        )
    else:
        query = query.where(DatasetRelease.id == release_id)
    with engine.connect() as connection:
        row = connection.execute(query).mappings().first()
    if row is None:
        error = NoAcceptedRelease if release_id is None else ReleaseNotFound
        raise error("No matching accepted dataset release")
    return dict(row)


def source_index(engine: Engine, release_id: str, dataset: Dataset) -> SourceIndex:
    rows = release_versions(engine, release_id, dataset)
    return SourceIndex(
        dataset,
        (
            SourceVersion(
                id=row["id"],
                dataset=dataset,
                target_start_utc=row["target_start_utc"],
                source_published_at=row["source_published_at"],
                generation_mw=row["generation_mw"],
                settlement_date=row.get("settlement_date"),
                settlement_period=row.get("settlement_period"),
                quality_reason=row["quality_reason"],
            )
            for row in rows
        ),
    )


def load_analysis_sources(engine: Engine, release_id: str | None = None) -> AnalysisSources:
    release = resolve_release(engine, release_id)
    # Membership is immutable: a concurrent active-pointer change cannot mix releases.
    pinned_id = release["id"]
    return AnalysisSources(
        pinned_id,
        release["parser_version"],
        source_index(engine, pinned_id, "WINDFOR"),
        source_index(engine, pinned_id, "FUELHH"),
    )
