"""Coverage evidence for candidate releases, with latest-key integrity checks."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from backend.app.domain.sources import select_latest
from backend.app.ingestion.archive import RawBatch, canonical, digest, iso, january_requests
from backend.app.ingestion.normalize import PARSER_VERSION, SourceVersion, normalize

VALIDATION_VERSION = "january_coverage_v1"
CUTOFFS = ("09:00", "09:45")


def latest_key(versions: list[SourceVersion], cutoff: datetime | None = None):
    """Compatibility adapter; release validation and analysis share the same selector."""
    selection = select_latest(versions, cutoff)
    if selection.state != "valid":
        return None, selection.reason
    return next(row for row in versions if row.id == selection.source_version_ids[0]), None


def inspect_batches(batches: list[RawBatch]) -> tuple[dict, dict[str, list[SourceVersion]]]:
    requests = {request.id for request in january_requests()}
    if len(batches) != len(requests) or {batch.request.id for batch in batches} != requests:
        raise ValueError("Candidate release must include every required source window exactly once")
    by_batch = {batch.id: normalize(batch) for batch in batches}
    forecast, actual, variants = {}, {}, defaultdict(set)
    received_rows = 0
    for records in by_batch.values():
        received_rows += len(records)
        for row in records:
            (forecast if row.dataset == "WINDFOR" else actual)[row.id] = row
            variants[(row.dataset, *row.key)].add(row.id)
    forecast_targets, actual_targets = defaultdict(list), defaultdict(list)
    for row in forecast.values():
        forecast_targets[row.target_start_utc].append(row)
    for row in actual.values():
        actual_targets[row.target_start_utc].append(row)
    days = []
    for offset in range(31):
        decision = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=offset)
        delivery = decision + timedelta(days=1)
        actual_issues, actual_present = [], 0
        for period in range(48):
            target = delivery + timedelta(minutes=30 * period)
            row, reason = latest_key(actual_targets[target])
            if row:
                actual_present += 1
            else:
                actual_issues.append({"target": iso(target), "reason": reason})
        cutoff_results = {}
        for cutoff in CUTOFFS:
            hour, minute = map(int, cutoff.split(":"))
            instant = decision.replace(hour=hour, minute=minute)
            count, issues = 0, []
            for period in range(24):
                target = delivery + timedelta(hours=period)
                row, reason = latest_key(forecast_targets[target], instant)
                if row:
                    count += 1
                else:
                    issues.append({"target": iso(target), "reason": reason})
            cutoff_results[cutoff] = {"expected": 24, "valid": count, "issues": issues}
        days.append(
            {
                "decision_date": decision.date().isoformat(),
                "delivery_date": delivery.date().isoformat(),
                "actual_expected": 48,
                "actual_valid": actual_present,
                "actual_issues": actual_issues,
                "forecast_cutoffs": cutoff_results,
            }
        )
    actual_valid = sum(day["actual_valid"] for day in days)
    forecast_valid = {
        cutoff: sum(day["forecast_cutoffs"][cutoff]["valid"] for day in days) for cutoff in CUTOFFS
    }
    report = {
        "normalized_versions_sha256": digest(canonical(sorted(forecast) + sorted(actual))),
        "acceptance_policy": "strict_v1",
        "validation_version": VALIDATION_VERSION,
        "parser_version": PARSER_VERSION,
        "status": "complete"
        if actual_valid == 1488 and all(n == 744 for n in forecast_valid.values())
        else "partial",
        "forecast_versions": len(forecast),
        "actual_versions": len(actual),
        "exact_duplicate_rows": received_rows - len(forecast) - len(actual),
        "conflicting_source_keys": sum(len(ids) > 1 for ids in variants.values()),
        "invalid_source_versions": sum(
            bool(row.quality_reason) for row in [*forecast.values(), *actual.values()]
        ),
        "expected_actual_half_hours": 1488,
        "valid_actual_half_hours": actual_valid,
        "expected_forecast_targets_per_cutoff": 744,
        "valid_forecast_targets_by_cutoff": forecast_valid,
        "decisions": days,
    }
    if report["conflicting_source_keys"] or report["invalid_source_versions"]:
        report["status"] = "partial"
    return report, by_batch


def release_identity(batches: list[RawBatch], report: dict) -> str:
    return digest(
        canonical(
            {
                "batches": sorted(batch.id for batch in batches),
                "parser": PARSER_VERSION,
                "validation": VALIDATION_VERSION,
                "quality": report,
            }
        )
    )
