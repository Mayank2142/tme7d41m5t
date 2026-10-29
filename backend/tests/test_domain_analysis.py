"""Independent arithmetic, temporal integrity, and explicit coverage examples."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta
from math import sqrt
from random import Random

import pytest

from backend.app.domain.analysis import analyze_accuracy, analyze_decision
from backend.app.domain.calendar import (
    decision_dates,
    decision_window,
    parse_cutoff,
    target_grid,
    uk_day_bounds,
)
from backend.app.domain.metrics import error_metrics
from backend.app.domain.sources import SourceIndex, SourceVersion, select_latest

DAY = date(2026, 1, 1)
TARGET = datetime(2026, 1, 2, tzinfo=UTC)
ISSUE = datetime(2026, 1, 1, 8, tzinfo=UTC)
CUTOFF = datetime(2026, 1, 1, 9, tzinfo=UTC)


def version(value, *, target=TARGET, publication=ISSUE, dataset="WINDFOR", reason=None):
    return SourceVersion(
        id=f"{dataset}|{target.isoformat()}|{publication.isoformat()}|{value}|{reason}",
        dataset=dataset,
        target_start_utc=target,
        source_published_at=publication,
        generation_mw=value,
        settlement_date=target.date() if dataset == "FUELHH" else None,
        settlement_period=1 if dataset == "FUELHH" else None,
        quality_reason=reason,
    )


def accuracy(forecasts=(), actuals=(), start=DAY, end=DAY, cutoff=time(9)):
    return analyze_accuracy(
        SourceIndex("WINDFOR", forecasts), SourceIndex("FUELHH", actuals), start, end, cutoff
    )


def assert_reconciles(ledger):
    assert ledger.expected == (
        ledger.forecast_missing
        + ledger.forecast_invalid
        + ledger.actual_missing
        + ledger.actual_invalid
        + ledger.paired
    )


def test_january_calendar_includes_all_of_february_first_and_uses_exclusive_end():
    days = decision_dates(DAY, date(2026, 1, 31))
    assert len(days) == 31
    first, last = decision_window(days[0], time(9)), decision_window(days[-1], time(23, 59))
    assert first.delivery_start_utc == TARGET
    assert first.cutoff_utc == CUTOFF
    assert last.delivery_start_utc == datetime(2026, 2, 1, tzinfo=UTC)
    assert last.delivery_end_utc == datetime(2026, 2, 2, tzinfo=UTC)
    assert last.cutoff_utc == datetime(2026, 1, 31, 23, 59, tzinfo=UTC)
    points = target_grid(last.delivery_start_utc, last.delivery_end_utc, 60)
    assert len(points) == 24 and points[-1] == datetime(2026, 2, 1, 23, tzinfo=UTC)
    assert last.delivery_end_utc not in points


@pytest.mark.parametrize(
    ("day", "hours", "utc_start"),
    [
        (date(2026, 3, 29), 23, datetime(2026, 3, 29, tzinfo=UTC)),
        (date(2026, 10, 25), 25, datetime(2026, 10, 24, 23, tzinfo=UTC)),
    ],
)
def test_uk_civil_days_handle_both_clock_changes(day, hours, utc_start):
    start, end = uk_day_bounds(day)
    assert start == utc_start and end - start == timedelta(hours=hours)
    assert len(target_grid(start, end, 60)) == hours
    assert len(set(target_grid(start, end, 30))) == hours * 2


@pytest.mark.parametrize(
    ("start", "end"),
    [(date(2025, 12, 31), DAY), (DAY, date(2026, 2, 1)), (date(2026, 1, 2), DAY)],
)
def test_decision_scope_and_reversed_ranges_are_rejected(start, end):
    with pytest.raises(ValueError, match="January 2026"):
        decision_dates(start, end)


@pytest.mark.parametrize("value", ["9:00", "09:00:00", "09:00Z", "24:00", "09:60"])
def test_cutoff_requires_a_real_local_minute(value):
    with pytest.raises(ValueError):
        parse_cutoff(value)


def test_cutoff_midnight_is_allowed_and_offset_or_naive_datetimes_are_rejected():
    assert decision_window(DAY, parse_cutoff("00:00")).cutoff_utc == ISSUE.replace(hour=0)
    with pytest.raises(ValueError):
        decision_window(DAY, time(9, tzinfo=UTC))
    with pytest.raises(ValueError):
        select_latest([version(10)], CUTOFF.replace(tzinfo=None))
    with pytest.raises(ValueError):
        replace(version(10), target_start_utc=TARGET.replace(tzinfo=None))


def test_selection_is_inclusive_and_independent_per_target_with_mixed_issue_times():
    rows = [
        version(5),
        version(10, publication=CUTOFF),
        version(999, publication=CUTOFF + timedelta(microseconds=1)),
        version(20, target=TARGET + timedelta(hours=1), publication=ISSUE - timedelta(minutes=30)),
        version(30, target=TARGET + timedelta(hours=2), publication=CUTOFF + timedelta(seconds=1)),
        # A target outside this delivery day cannot enlarge the expected grid.
        version(100, target=TARGET - timedelta(hours=1)),
    ]
    decision = analyze_decision(SourceIndex("WINDFOR", rows), DAY, time(9))
    assert decision.points[0].forecast.generation_mw == 10
    assert decision.points[0].age_at_cutoff_seconds == 0
    assert decision.points[1].forecast.generation_mw == 20
    assert decision.points[1].age_at_cutoff_seconds == 5400
    assert decision.points[2].forecast.reason == "NO_PRE_CUTOFF_PUBLICATION"
    assert decision.points[2].forecast.publication_utc is None
    assert decision.points[2].forecast.source_version_ids == ()
    assert decision.coverage.expected == 24 and decision.coverage.valid == 2
    assert decision.summary.mean_reported_mw == 15
    # Post-cutoff identities, values, and even their publication times are absent.
    serialized = str(asdict(decision))
    assert "999" not in serialized and "actual" not in serialized and "metrics" not in serialized
    assert version(999, publication=CUTOFF + timedelta(microseconds=1)).id not in serialized


@pytest.mark.parametrize(
    ("latest", "reason"),
    [
        (version(None, publication=CUTOFF), "NULL_GENERATION"),
        (version(-1, publication=CUTOFF), "NEGATIVE_WIND_GENERATION"),
        (
            version(10, publication=CUTOFF, reason="UNEXPECTED_TARGET_RESOLUTION"),
            "UNEXPECTED_TARGET_RESOLUTION",
        ),
    ],
)
def test_invalid_latest_forecast_never_falls_back_to_an_older_valid_row(latest, reason):
    decision = analyze_decision(SourceIndex("WINDFOR", [version(100), latest]), DAY, time(9))
    selected = decision.points[0].forecast
    assert selected.state == "invalid" and selected.reason == reason
    assert selected.publication_utc == CUTOFF and selected.generation_mw is None
    assert selected.source_version_ids == (latest.id,)


def test_conflicts_deduplicate_identical_ids_and_resolve_only_with_a_newer_key():
    old, a, b = version(5), version(10, publication=CUTOFF), version(11, publication=CUTOFF)
    conflict = select_latest([old, a, a, b], CUTOFF)
    assert conflict.reason == "CONFLICTING_SOURCE_KEY"
    assert conflict.source_version_ids == tuple(sorted([a.id, b.id]))
    assert select_latest([old, a, a], CUTOFF).generation_mw == 10
    newer = version(15, publication=CUTOFF + timedelta(minutes=1))
    assert select_latest([old, a, b, newer]).generation_mw == 15


def test_actual_vintage_uses_latest_release_publication_and_retains_invalid_latest():
    old = version(8, dataset="FUELHH", publication=TARGET + timedelta(minutes=30))
    revised = version(7, dataset="FUELHH", publication=TARGET + timedelta(days=2))
    report = accuracy([version(10)], [old, revised])
    point = report.days[0].points[0]
    assert point.error_mw == 3 and point.actual.publication_utc == revised.source_published_at
    invalid = replace(
        revised, id="invalid-revision", generation_mw=None, quality_reason="NULL_GENERATION"
    )
    report = accuracy([version(10)], [old, invalid])
    assert report.days[0].points[0].state == "actual_invalid"
    assert report.metrics.reason == "NO_VALID_PAIRS"
    conflicting = replace(revised, id="conflicting-revision", generation_mw=9)
    report = accuracy([version(10)], [old, revised, conflicting])
    assert report.days[0].points[0].actual.reason == "CONFLICTING_SOURCE_KEY"


def test_every_coverage_state_reconciles_with_forecast_precedence_and_no_zero_filling():
    forecasts = [
        version(None, target=TARGET + timedelta(hours=1)),
        version(10, target=TARGET + timedelta(hours=2)),
        version(10, target=TARGET + timedelta(hours=3)),
        version(10, target=TARGET + timedelta(hours=4)),
    ]
    actuals = [
        # Both sources invalid at h1: forecast_invalid wins the ledger precedence.
        version(None, dataset="FUELHH", target=TARGET + timedelta(hours=1)),
        version(None, dataset="FUELHH", target=TARGET + timedelta(hours=3)),
        version(0, dataset="FUELHH", target=TARGET + timedelta(hours=4)),
        version(9999, dataset="FUELHH", target=TARGET + timedelta(hours=4, minutes=30)),
    ]
    report = accuracy(forecasts, actuals)
    assert [point.state for point in report.days[0].points[:5]] == [
        "forecast_missing",
        "forecast_invalid",
        "actual_missing",
        "actual_invalid",
        "paired",
    ]
    assert_reconciles(report.coverage)
    assert report.coverage.forecast_missing == 20
    assert report.coverage.forecast_invalid == 1
    assert report.coverage.actual_missing == 1
    assert report.coverage.actual_invalid == 1
    assert report.coverage.paired == 1
    assert report.coverage.paired_percent == pytest.approx(100 / 24)
    assert report.actual_source_coverage.expected == 48
    assert report.actual_source_coverage.valid == 2
    assert report.actual_source_coverage.invalid == 2
    assert report.actual_source_coverage.missing == 44
    assert report.metrics.mae_mw == 10
    assert report.days[0].points[0].error_mw is None
    # Half-hour observations remain available but are not extra forecast pairs.
    half_hour = report.days[0].actual_half_hours[9]
    assert half_hour.actual.generation_mw == 9999 and not half_hour.used_in_metrics


@pytest.mark.parametrize(
    ("errors", "mae", "rmse", "bias", "p90"),
    [
        ([2, -2], 2, 2, 0, 2),
        ([0, -2, 4, -10], 4, sqrt(30), -2, 8.2),
        ([7], 7, 7, 7, 7),
        ([0, 0], 0, 0, 0, 0),
    ],
)
def test_metrics_match_independently_calculated_examples(errors, mae, rmse, bias, p90):
    metrics = error_metrics(errors)
    assert metrics.mae_mw == pytest.approx(mae)
    assert metrics.rmse_mw == pytest.approx(rmse)
    assert metrics.bias_mw == pytest.approx(bias)
    assert metrics.p90_absolute_error_mw == pytest.approx(p90)
    assert metrics.paired_targets == len(errors) and metrics.reason is None


def test_empty_selection_returns_null_metrics_and_explicit_missing_targets():
    report = accuracy()
    assert report.coverage.expected == 24 and report.coverage.forecast_missing == 24
    assert report.coverage.paired == 0
    assert report.actual_source_coverage.expected == report.actual_source_coverage.missing == 48
    assert report.metrics.reason == "NO_VALID_PAIRS"
    assert report.metrics.mae_mw is report.metrics.rmse_mw is report.metrics.bias_mw is None
    assert report.metrics.p90_absolute_error_mw is None
    decision = analyze_decision(SourceIndex("WINDFOR", []), DAY, time(9))
    assert decision.summary.mean_reported_mw is None


def test_range_metrics_pool_pairs_instead_of_equally_weighting_daily_metrics():
    next_day = TARGET + timedelta(days=1)
    forecasts = [
        version(0),
        version(10, target=next_day),
        version(10, target=next_day + timedelta(hours=1)),
    ]
    actuals = [version(0, dataset="FUELHH", target=row.target_start_utc) for row in forecasts]
    report = accuracy(forecasts, actuals, end=DAY + timedelta(days=1))
    assert report.days[0].metrics.mae_mw == 0 and report.days[1].metrics.mae_mw == 10
    assert report.metrics.mae_mw == pytest.approx(20 / 3)
    assert report.metrics.mae_mw != 5
    assert report.coverage.expected == 48 and report.coverage.paired == 3
    assert_reconciles(report.coverage)


def test_input_order_and_repeated_exact_rows_cannot_change_the_analysis():
    forecasts = [
        version(10),
        version(15, publication=CUTOFF),
        version(20, target=TARGET + timedelta(hours=1)),
    ]
    actuals = [
        version(5, dataset="FUELHH"),
        version(7, dataset="FUELHH", target=TARGET + timedelta(hours=1)),
    ]
    expected = accuracy(forecasts, actuals)
    forecasts += forecasts[:2]
    Random(7).shuffle(forecasts)
    actuals.reverse()
    assert accuracy(forecasts, actuals) == expected


def test_selection_rejects_mixed_targets_and_indexes_reject_wrong_sources():
    with pytest.raises(ValueError, match="single dataset and target"):
        select_latest([version(1), version(1, target=TARGET + timedelta(hours=1))])
    with pytest.raises(ValueError, match="wrong dataset"):
        SourceIndex("WINDFOR", [version(1, dataset="FUELHH")])
