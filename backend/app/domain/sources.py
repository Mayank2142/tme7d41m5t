"""Source facts and publication-key selection, independent of storage and HTTP."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

Dataset = Literal["WINDFOR", "FUELHH"]
SelectionState = Literal["valid", "missing", "invalid"]
SELECTION_POLICY = "latest_source_key_v1"
ACTUAL_VINTAGE_POLICY = "latest_publication_in_release_v1"


@dataclass(frozen=True)
class SourceVersion:
    id: str
    dataset: Dataset
    target_start_utc: datetime
    source_published_at: datetime
    generation_mw: int | None
    settlement_date: date | None
    settlement_period: int | None
    quality_reason: str | None

    def __post_init__(self) -> None:
        if self.dataset not in {"WINDFOR", "FUELHH"}:
            raise ValueError("Unknown source dataset")
        if (
            self.target_start_utc.utcoffset() is None
            or self.source_published_at.utcoffset() is None
        ):
            raise ValueError("Source timestamps must be timezone-aware")
        object.__setattr__(self, "target_start_utc", self.target_start_utc.astimezone(UTC))
        object.__setattr__(self, "source_published_at", self.source_published_at.astimezone(UTC))
        value = self.generation_mw
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError("Source generation must be an integer or null")

    @property
    def key(self) -> tuple[datetime, datetime]:
        return self.target_start_utc, self.source_published_at

    def values(self) -> dict:
        return {
            "id": self.id,
            "target_start_utc": self.target_start_utc,
            "source_published_at": self.source_published_at,
            "generation_mw": self.generation_mw,
            "quality_reason": self.quality_reason,
        }


@dataclass(frozen=True)
class SourceSelection:
    state: SelectionState
    publication_utc: datetime | None
    generation_mw: int | None
    source_version_ids: tuple[str, ...]
    reason: str | None


def select_latest(
    versions: Iterable[SourceVersion],
    cutoff: datetime | None = None,
    *,
    missing_reason: str = "MISSING",
) -> SourceSelection:
    """Choose a single target's latest key before inspecting its quality.

    Returned evidence contains only eligible records. An invalid latest key never
    falls back to a previous valid publication. Identical version IDs deduplicate.
    """
    if cutoff is not None and cutoff.utcoffset() is None:
        raise ValueError("Publication cutoff must be timezone-aware")
    versions = tuple(versions)
    if len({(row.dataset, row.target_start_utc) for row in versions}) > 1:
        raise ValueError("Selection requires a single dataset and target")
    eligible = [row for row in versions if cutoff is None or row.source_published_at <= cutoff]
    if not eligible:
        return SourceSelection("missing", None, None, (), missing_reason)
    publication = max(row.source_published_at for row in eligible)
    variants = {}
    for row in eligible:
        if row.source_published_at == publication:
            if row.id in variants and variants[row.id] != row:
                raise ValueError("Inconsistent content for the same source version ID")
            variants[row.id] = row
    ids = tuple(sorted(variants))
    if len(ids) != 1:
        return SourceSelection("invalid", publication, None, ids, "CONFLICTING_SOURCE_KEY")
    row = variants[ids[0]]
    reason = row.quality_reason
    if row.generation_mw is None:
        reason = reason or "NULL_GENERATION"
    elif row.generation_mw < 0:
        reason = reason or "NEGATIVE_WIND_GENERATION"
    return SourceSelection(
        "invalid" if reason else "valid",
        publication,
        None if reason else row.generation_mw,
        ids,
        reason,
    )


class SourceIndex:
    """Index once per release, then select independently per expected target."""

    def __init__(self, dataset: Dataset, versions: Iterable[SourceVersion]) -> None:
        by_target = defaultdict(list)
        for row in versions:
            if row.dataset != dataset:
                raise ValueError("Source index received the wrong dataset")
            by_target[row.target_start_utc].append(row)
        self._by_target = {target: tuple(rows) for target, rows in by_target.items()}
        self.dataset = dataset

    def select(self, target: datetime, cutoff: datetime | None = None) -> SourceSelection:
        if target.utcoffset() is None:
            raise ValueError("Target must be timezone-aware")
        return select_latest(
            self._by_target.get(target, ()),
            cutoff,
            missing_reason="NO_PRE_CUTOFF_PUBLICATION"
            if self.dataset == "WINDFOR"
            else "NO_ACTUAL_PUBLICATION",
        )
