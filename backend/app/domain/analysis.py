"""Forecast-only decisions and explicitly retrospective source-time accuracy."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time
from math import fsum
from typing import Literal

from backend.app.domain.calendar import DecisionWindow, decision_dates, decision_window, target_grid
from backend.app.domain.metrics import ErrorMetrics, error_metrics
from backend.app.domain.policy import PILOT_POLICY
from backend.app.domain.sources import (
    ACTUAL_VINTAGE_POLICY,
    SELECTION_POLICY,
    SourceIndex,
    SourceSelection,
)

EvaluationState = Literal[
    "forecast_missing", "forecast_invalid", "actual_missing", "actual_invalid", "paired"
]


@dataclass(frozen=True)
class SourceCoverage:
    expected: int
    valid: int
    missing: int
    invalid: int
    valid_percent: float | None


def source_coverage(selections: tuple[SourceSelection, ...]) -> SourceCoverage:
    counts = Counter(item.state for item in selections)
    expected = len(selections)
    return SourceCoverage(
        expected,
        counts["valid"],
        counts["missing"],
        counts["invalid"],
        100 * counts["valid"] / expected if expected else None,
    )


@dataclass(frozen=True)
class ForecastPoint:
    target_start_utc: datetime
    forecast: SourceSelection
    age_at_cutoff_seconds: int | None


@dataclass(frozen=True)
class ForecastSummary:
    mean_reported_mw: float | None
    minimum_reported_mw: int | None
    maximum_reported_mw: int | None
    earliest_publication_utc: datetime | None
    latest_publication_utc: datetime | None


@dataclass(frozen=True)
class DecisionAnalysis:
    """Accepts forecasts only and carries no actuals or retrospective metrics."""

    window: DecisionWindow
    points: tuple[ForecastPoint, ...]
    coverage: SourceCoverage
    summary: ForecastSummary
    selection_policy: str = SELECTION_POLICY
    availability_model: str = PILOT_POLICY.availability_model


def analyze_decision(forecasts: SourceIndex, day: date, cutoff: time) -> DecisionAnalysis:
    if forecasts.dataset != "WINDFOR":
        raise ValueError("Decision analysis requires forecast records")
    window = decision_window(day, cutoff)
    points = []
    for target in target_grid(window.delivery_start_utc, window.delivery_end_utc, 60):
        selection = forecasts.select(target, window.cutoff_utc)
        age = (
            int((window.cutoff_utc - selection.publication_utc).total_seconds())
            if selection.publication_utc is not None
            else None
        )
        points.append(ForecastPoint(target, selection, age))
    values = [item.forecast.generation_mw for item in points if item.forecast.state == "valid"]
    publications = [
        item.forecast.publication_utc
        for item in points
        if item.forecast.publication_utc is not None
    ]
    return DecisionAnalysis(
        window,
        tuple(points),
        source_coverage(tuple(item.forecast for item in points)),
        ForecastSummary(
            fsum(values) / len(values) if values else None,
            min(values) if values else None,
            max(values) if values else None,
            min(publications) if publications else None,
            max(publications) if publications else None,
        ),
    )


@dataclass(frozen=True)
class AccuracyPoint:
    target_start_utc: datetime
    forecast: SourceSelection
    actual: SourceSelection
    state: EvaluationState
    reason: str | None
    error_mw: int | None


@dataclass(frozen=True)
class CoverageLedger:
    expected: int
    forecast_missing: int
    forecast_invalid: int
    actual_missing: int
    actual_invalid: int
    paired: int
    paired_percent: float | None


def coverage_ledger(points: tuple[AccuracyPoint, ...]) -> CoverageLedger:
    counts = Counter(item.state for item in points)
    expected = len(points)
    return CoverageLedger(
        expected,
        counts["forecast_missing"],
        counts["forecast_invalid"],
        counts["actual_missing"],
        counts["actual_invalid"],
        counts["paired"],
        100 * counts["paired"] / expected if expected else None,
    )


@dataclass(frozen=True)
class ActualPoint:
    target_start_utc: datetime
    actual: SourceSelection
    used_in_metrics: bool


@dataclass(frozen=True)
class DailyAccuracy:
    window: DecisionWindow
    points: tuple[AccuracyPoint, ...]
    actual_half_hours: tuple[ActualPoint, ...]
    metrics: ErrorMetrics
    coverage: CoverageLedger
    actual_source_coverage: SourceCoverage


@dataclass(frozen=True)
class AccuracyAnalysis:
    decision_from: date
    decision_to: date
    cutoff_local: str
    days: tuple[DailyAccuracy, ...]
    metrics: ErrorMetrics
    coverage: CoverageLedger
    actual_source_coverage: SourceCoverage
    comparison_policy: str = PILOT_POLICY.comparison_policy
    selection_policy: str = SELECTION_POLICY
    actual_vintage_policy: str = ACTUAL_VINTAGE_POLICY
    availability_model: str = PILOT_POLICY.availability_model
    retrospective: bool = True


def _pair(point: ForecastPoint, actual: SourceSelection) -> AccuracyPoint:
    forecast = point.forecast
    if forecast.state != "valid":
        state, reason = f"forecast_{forecast.state}", forecast.reason
    elif actual.state != "valid":
        state, reason = f"actual_{actual.state}", actual.reason
    else:
        state, reason = "paired", None
    error = forecast.generation_mw - actual.generation_mw if state == "paired" else None
    return AccuracyPoint(point.target_start_utc, forecast, actual, state, reason, error)


def analyze_accuracy(
    forecasts: SourceIndex,
    actuals: SourceIndex,
    start: date,
    end: date,
    cutoff: time,
) -> AccuracyAnalysis:
    if actuals.dataset != "FUELHH":
        raise ValueError("Accuracy analysis requires WIND actual records")
    days = []
    for day in decision_dates(start, end):
        decision = analyze_decision(forecasts, day, cutoff)
        window = decision.window
        # Actuals intentionally use hindsight within this frozen release, not the
        # forecast cutoff. They never enter analyze_decision's inputs or output.
        observations = {
            target: actuals.select(target)
            for target in target_grid(window.delivery_start_utc, window.delivery_end_utc, 30)
        }
        points = tuple(
            _pair(point, observations[point.target_start_utc]) for point in decision.points
        )
        paired_targets = {point.target_start_utc for point in points if point.state == "paired"}
        actual_points = tuple(
            ActualPoint(target, selection, target in paired_targets)
            for target, selection in observations.items()
        )
        days.append(
            DailyAccuracy(
                window,
                points,
                actual_points,
                error_metrics(point.error_mw for point in points if point.error_mw is not None),
                coverage_ledger(points),
                source_coverage(tuple(observations.values())),
            )
        )
    all_points = tuple(point for day in days for point in day.points)
    return AccuracyAnalysis(
        start,
        end,
        days[0].window.cutoff_local,
        tuple(days),
        error_metrics(point.error_mw for point in all_points if point.error_mw is not None),
        coverage_ledger(all_points),
        source_coverage(tuple(point.actual for day in days for point in day.actual_half_hours)),
    )
