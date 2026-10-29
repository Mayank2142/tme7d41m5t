"""Bounded UTF-8 CSV from the same typed objects returned by the JSON routes."""

import csv
import io
import json
from datetime import datetime

from backend.app.contracts import AccuracyResponse, DecisionResponse
from backend.app.domain.calendar import LONDON, DecisionWindow
from backend.app.domain.sources import SourceSelection
from backend.app.ingestion.archive import iso

COMMON_COLUMNS = (
    "mode",
    "analysis_context_id",
    "release_id",
    "source_parser",
    "application_version",
    "build_sha",
    "calendar_policy",
    "selection_policy",
    "availability_model",
    "timezone",
    "decision_date",
    "cutoff_local",
    "cutoff_utc",
    "delivery_start_utc",
    "delivery_end_utc",
    "row_type",
    "target_start_utc",
    "target_start_local",
    "forecast_cadence_minutes",
    "forecast_state",
    "forecast_mw",
    "forecast_published_at",
    "forecast_source_version_ids",
    "forecast_reason",
    "forecast_age_at_cutoff_seconds",
    "attribution",
    "licence_url",
)
ACCURACY_COLUMNS = (
    "comparison_policy",
    "actual_vintage_policy",
    "metrics_version",
    "actual_interval_minutes",
    "comparison_expected",
    "actual_state",
    "actual_mw",
    "actual_published_at",
    "actual_source_version_ids",
    "actual_reason",
    "used_in_metrics",
    "evaluation_state",
    "reason",
    "error_mw",
    "absolute_error_mw",
)


def safe_cell(value):
    """Protect textual cells without altering legitimate negative numeric errors."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n"))
        or value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@"))
    ):
        return "'" + value
    return value


def _source(selection: SourceSelection, prefix: str) -> dict:
    return {
        f"{prefix}_state": selection.state,
        f"{prefix}_mw": selection.generation_mw,
        f"{prefix}_published_at": iso(selection.publication_utc)
        if selection.publication_utc
        else None,
        f"{prefix}_source_version_ids": json.dumps(
            selection.source_version_ids, separators=(",", ":")
        ),
        f"{prefix}_reason": selection.reason,
    }


def _common(response, window: DecisionWindow, target: datetime) -> dict:
    context = response.context
    return {
        "mode": context.mode,
        "analysis_context_id": response.analysis_context_id,
        "release_id": context.release_id,
        "source_parser": context.source_parser,
        "application_version": context.application_version,
        "build_sha": context.build_sha,
        "calendar_policy": context.calendar_policy,
        "selection_policy": context.selection_policy,
        "availability_model": context.availability_model,
        "timezone": context.timezone,
        "decision_date": window.decision_date.isoformat(),
        "cutoff_local": context.cutoff_local,
        "cutoff_utc": iso(window.cutoff_utc),
        "delivery_start_utc": iso(window.delivery_start_utc),
        "delivery_end_utc": iso(window.delivery_end_utc),
        "target_start_utc": iso(target),
        "target_start_local": target.astimezone(LONDON).isoformat(),
        "forecast_cadence_minutes": context.forecast_cadence_minutes,
        "attribution": response.source.attribution,
        "licence_url": response.source.licence_url,
    }


def render_csv(response: DecisionResponse | AccuracyResponse) -> str:
    output = io.StringIO(newline="")
    columns = COMMON_COLUMNS + (ACCURACY_COLUMNS if isinstance(response, AccuracyResponse) else ())
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\r\n")
    writer.writeheader()

    def write(row):
        writer.writerow({key: safe_cell(value) for key, value in row.items()})

    if isinstance(response, DecisionResponse):
        analysis = response.analysis
        for point in analysis.points:
            write(
                _common(response, analysis.window, point.target_start_utc)
                | {
                    "row_type": "forecast_target",
                    "forecast_age_at_cutoff_seconds": point.age_at_cutoff_seconds,
                }
                | _source(point.forecast, "forecast")
            )
    else:
        context = response.context
        for day in response.analysis.days:
            comparisons = {point.target_start_utc: point for point in day.points}
            for observation in day.actual_half_hours:
                target = observation.target_start_utc
                point = comparisons.get(target)
                row = (
                    _common(response, day.window, target)
                    | {
                        "row_type": "comparison_target" if point else "actual_only",
                        "comparison_policy": context.comparison_policy,
                        "actual_vintage_policy": context.actual_vintage_policy,
                        "metrics_version": context.metrics_version,
                        "actual_interval_minutes": context.actual_interval_minutes,
                        "comparison_expected": point is not None,
                        "used_in_metrics": observation.used_in_metrics,
                    }
                    | _source(observation.actual, "actual")
                )
                if point:
                    publication = point.forecast.publication_utc
                    row |= _source(point.forecast, "forecast") | {
                        "forecast_age_at_cutoff_seconds": int(
                            (day.window.cutoff_utc - publication).total_seconds()
                        )
                        if publication is not None
                        else None,
                        "evaluation_state": point.state,
                        "reason": point.reason,
                        "error_mw": point.error_mw,
                        "absolute_error_mw": abs(point.error_mw)
                        if point.error_mw is not None
                        else None,
                    }
                write(row)
    return output.getvalue()
