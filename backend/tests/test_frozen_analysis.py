"""Real source contract, checked against an independent raw-JSON calculation."""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from math import sqrt
from pathlib import Path
from statistics import mean, quantiles

import pytest

from backend.app.domain.analysis import analyze_accuracy, analyze_decision
from backend.app.domain.sources import SourceIndex
from backend.app.ingestion.archive import read_archive
from backend.app.ingestion.normalize import normalize

SEED = Path("data/snapshots/january_2026.json.gz")


@pytest.fixture(scope="module")
def sources():
    batches = read_archive(SEED)
    normalized = {dataset: [] for dataset in ("WINDFOR", "FUELHH")}
    raw = {dataset: defaultdict(list) for dataset in normalized}
    for batch in batches:
        normalized[batch.request.dataset].extend(normalize(batch))
        for row in batch.rows():
            target = datetime.fromisoformat(row["startTime"])
            raw[batch.request.dataset][target].append(row)
    return (
        SourceIndex("WINDFOR", normalized["WINDFOR"]),
        SourceIndex("FUELHH", normalized["FUELHH"]),
        raw,
    )


@pytest.mark.parametrize("cutoff", [time(0), time(9), time(9, 45), time(23, 59)])
def test_full_month_matches_an_independent_raw_source_calculation(sources, cutoff):
    forecasts, actuals, raw = sources
    report = analyze_accuracy(forecasts, actuals, date(2026, 1, 1), date(2026, 1, 31), cutoff)
    expected_errors = []
    for day_number in range(1, 32):
        day = datetime(2026, 1, day_number, tzinfo=UTC)
        cutoff_utc = day.replace(hour=cutoff.hour, minute=cutoff.minute)
        for hour in range(24):
            target = day + timedelta(days=1, hours=hour)
            candidates = [
                row
                for row in raw["WINDFOR"][target]
                if datetime.fromisoformat(row["publishTime"]) <= cutoff_utc
            ]
            observations = raw["FUELHH"][target]
            if candidates and observations:
                forecast = max(candidates, key=lambda row: row["publishTime"])
                actual = max(observations, key=lambda row: row["publishTime"])
                expected_errors.append(forecast["generation"] - actual["generation"])
    errors = [
        point.error_mw for day in report.days for point in day.points if point.state == "paired"
    ]
    assert errors == expected_errors
    assert report.coverage.expected == 744
    assert report.coverage.paired == len(expected_errors)
    assert report.actual_source_coverage.expected == report.actual_source_coverage.valid == 1488
    assert report.metrics.mae_mw == pytest.approx(mean(abs(value) for value in expected_errors))
    assert report.metrics.rmse_mw == pytest.approx(
        sqrt(mean(value**2 for value in expected_errors))
    )
    assert report.metrics.bias_mw == pytest.approx(mean(expected_errors))
    assert report.metrics.p90_absolute_error_mw == pytest.approx(
        quantiles([abs(value) for value in expected_errors], n=10, method="inclusive")[8]
    )
    assert report.days[-1].window.delivery_date == date(2026, 2, 1)
    assert sum(
        point.used_in_metrics for day in report.days for point in day.actual_half_hours
    ) == len(errors)


def test_documented_january_example_is_reproduced_without_interpolating_half_hours(sources):
    forecasts, actuals, _ = sources
    report = analyze_accuracy(forecasts, actuals, date(2026, 1, 1), date(2026, 1, 1), time(9))
    midnight = report.days[0].points[0]
    assert midnight.target_start_utc == datetime(2026, 1, 2, tzinfo=UTC)
    assert midnight.forecast.generation_mw == 18781
    assert midnight.actual.generation_mw == 15228
    assert midnight.error_mw == 3553
    assert report.coverage.paired == 24
    assert len(report.days[0].actual_half_hours) == 48
    assert report.days[0].actual_half_hours[1].used_in_metrics is False
    decision = analyze_decision(forecasts, date(2026, 1, 1), time(9))
    assert all(
        point.forecast.publication_utc <= decision.window.cutoff_utc
        for point in decision.points
        if point.forecast.publication_utc is not None
    )
