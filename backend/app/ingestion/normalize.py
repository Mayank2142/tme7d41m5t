"""Preserve invalid numeric values and source-key variants for explicit validation."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from backend.app.domain.sources import SourceVersion
from backend.app.ingestion.archive import RawBatch, canonical, digest, instant, iso

PARSER_VERSION = "elexon_streams_v2"


def normalize(batch: RawBatch) -> list[SourceVersion]:
    records = []
    for index, row in enumerate(batch.rows()):
        try:
            if row["dataset"] != batch.request.dataset:
                raise ValueError("Unexpected source dataset")
            target, publication = instant(row["startTime"]), instant(row["publishTime"])
            generation = row["generation"]
            if generation is not None and (
                isinstance(generation, bool) or not isinstance(generation, int)
            ):
                raise ValueError("Generation must be an integer or null")
            if generation is not None and not -(2**63) <= generation < 2**63:
                raise ValueError("Generation exceeds the source int64 range")
            reason = "NULL_GENERATION" if generation is None else None
            if generation is not None and generation < 0:
                reason = "NEGATIVE_WIND_GENERATION"
            expected_minutes = {0} if batch.request.dataset == "WINDFOR" else {0, 30}
            if target.minute not in expected_minutes or target.second or target.microsecond:
                reason = "UNEXPECTED_TARGET_RESOLUTION"
            settlement_date, settlement_period = None, None
            if batch.request.dataset == "FUELHH":
                if row["fuelType"] != "WIND":
                    raise ValueError("Actual response contained a non-WIND record")
                settlement_date = date.fromisoformat(row["settlementDate"])
                settlement_period = row["settlementPeriod"]
                if isinstance(settlement_period, bool) or not isinstance(settlement_period, int):
                    raise ValueError("Settlement period must be an integer")
                local = target.astimezone(ZoneInfo("Europe/London"))
                midnight = datetime.combine(
                    local.date(), datetime.min.time(), ZoneInfo("Europe/London")
                )
                expected_period = (
                    int((target - midnight.astimezone(UTC)).total_seconds() / 1800) + 1
                )
                if local.date() != settlement_date or settlement_period != expected_period:
                    reason = "SETTLEMENT_METADATA_MISMATCH"
            fingerprint = [
                PARSER_VERSION,
                batch.request.dataset,
                iso(target),
                iso(publication),
                generation,
                settlement_date.isoformat() if settlement_date else None,
                settlement_period,
                reason,
            ]
            records.append(
                SourceVersion(
                    digest(canonical(fingerprint)),
                    batch.request.dataset,
                    target,
                    publication,
                    generation,
                    settlement_date,
                    settlement_period,
                    reason,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"{batch.request.dataset} row {index}: invalid required source fields"
            ) from exc
    return records
