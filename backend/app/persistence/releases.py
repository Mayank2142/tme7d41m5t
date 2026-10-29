"""Transactional, append-only dataset publication and release-scoped reads."""

import gzip
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from backend.app.ingestion.archive import RawBatch, digest, read_archive
from backend.app.ingestion.normalize import PARSER_VERSION
from backend.app.ingestion.validation import inspect_batches, release_identity
from backend.app.persistence.models import (
    ActiveRelease,
    ActualBatchMember,
    ActualVersion,
    DatasetRelease,
    ForecastBatchMember,
    ForecastVersion,
    IngestionRun,
    RawBatchRecord,
    ReleaseActualMember,
    ReleaseBatchMember,
    ReleaseForecastMember,
)


def _insert_missing(connection, model, rows: list[dict]) -> None:
    for offset in range(0, len(rows), 500):
        connection.execute(
            pg_insert(model).values(rows[offset : offset + 500]).on_conflict_do_nothing()
        )


def import_archive(engine: Engine, path: Path, *, allow_partial: bool = False) -> dict:
    run_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            insert(IngestionRun).values(
                id=run_id,
                started_at=datetime.now(UTC),
                status="running",
                archive_sha256=digest(path.read_bytes()),
            )
        )
    try:
        batches = read_archive(path)
        report, normalized = inspect_batches(batches)
        report["acceptance_policy"] = "allow_partial_v1" if allow_partial else "strict_v1"
        release_id = release_identity(batches, report)
        accepted = report["status"] == "complete" or allow_partial
        with engine.begin() as connection:
            connection.execute(text("SELECT pg_advisory_xact_lock(20260102)"))
            _insert_missing(
                connection,
                RawBatchRecord,
                [
                    {
                        "id": batch.id,
                        "dataset": batch.request.dataset,
                        "source_url": batch.request.url,
                        "parameters": batch.request.parameters,
                        "received_at": batch.received_at,
                        "payload_sha256": batch.payload_sha256,
                        "payload_gzip": gzip.compress(batch.payload, mtime=0),
                        "payload_bytes": len(batch.payload),
                    }
                    for batch in batches
                ],
            )
            forecast, actual, forecast_members, actual_members = {}, {}, set(), set()
            for batch in batches:
                for row in normalized[batch.id]:
                    values = row.values()
                    if row.dataset == "WINDFOR":
                        forecast[row.id] = values
                        forecast_members.add((batch.id, row.id))
                    else:
                        actual[row.id] = values | {
                            "settlement_date": row.settlement_date,
                            "settlement_period": row.settlement_period,
                        }
                        actual_members.add((batch.id, row.id))
            _insert_missing(connection, ForecastVersion, list(forecast.values()))
            _insert_missing(connection, ActualVersion, list(actual.values()))
            _insert_missing(
                connection,
                ForecastBatchMember,
                [{"batch_id": batch, "version_id": version} for batch, version in forecast_members],
            )
            _insert_missing(
                connection,
                ActualBatchMember,
                [{"batch_id": batch, "version_id": version} for batch, version in actual_members],
            )
            _insert_missing(
                connection,
                DatasetRelease,
                [
                    {
                        "id": release_id,
                        "created_at": datetime.now(UTC),
                        "status": "accepted" if accepted else "rejected",
                        "quality": report,
                        "parser_version": PARSER_VERSION,
                    }
                ],
            )
            _insert_missing(
                connection,
                ReleaseBatchMember,
                [{"release_id": release_id, "batch_id": batch.id} for batch in batches],
            )
            _insert_missing(
                connection,
                ReleaseForecastMember,
                [{"release_id": release_id, "version_id": version_id} for version_id in forecast],
            )
            _insert_missing(
                connection,
                ReleaseActualMember,
                [{"release_id": release_id, "version_id": version_id} for version_id in actual],
            )
            if accepted:
                pointer = pg_insert(ActiveRelease).values(
                    name="january_2026", release_id=release_id, activated_at=datetime.now(UTC)
                )
                connection.execute(
                    pointer.on_conflict_do_update(
                        index_elements=[ActiveRelease.name],
                        set_={
                            "release_id": release_id,
                            "activated_at": pointer.excluded.activated_at,
                        },
                    )
                )
            connection.execute(
                update(IngestionRun)
                .where(IngestionRun.id == run_id)
                .values(
                    status="succeeded" if accepted else "rejected",
                    finished_at=datetime.now(UTC),
                    release_id=release_id,
                )
            )
        return {"run_id": run_id, "release_id": release_id, "accepted": accepted, "quality": report}
    except Exception as exc:
        with engine.begin() as connection:
            connection.execute(
                update(IngestionRun)
                .where(IngestionRun.id == run_id)
                .values(
                    status="failed",
                    finished_at=datetime.now(UTC),
                    error_code=type(exc).__name__,
                )
            )
        raise


@dataclass(frozen=True)
class DatasetState:
    database: bool
    schema: bool
    release: dict | None = None
    error: str | None = None

    @property
    def code(self) -> str:
        if self.error:
            return self.error
        if not self.database:
            return "DATABASE_UNAVAILABLE"
        if not self.schema:
            return "SCHEMA_NOT_INITIALIZED"
        return "OK" if self.release else "NO_ACCEPTED_DATASET"


def dataset_state(engine: Engine) -> DatasetState:
    try:
        with engine.connect() as connection:
            row = (
                connection.execute(
                    select(DatasetRelease.id, DatasetRelease.quality, DatasetRelease.created_at)
                    .join(ActiveRelease, ActiveRelease.release_id == DatasetRelease.id)
                    .where(
                        ActiveRelease.name == "january_2026", DatasetRelease.status == "accepted"
                    )
                )
                .mappings()
                .first()
            )
            return DatasetState(True, True, dict(row) if row else None)
    except ProgrammingError as exc:
        if getattr(exc.orig, "sqlstate", None) == "42P01":
            return DatasetState(True, False)
        return DatasetState(True, False, error="DATASET_QUERY_FAILED")
    except SQLAlchemyError:
        return DatasetState(False, False)


def release_versions(engine: Engine, release_id: str, dataset: str) -> list[dict]:
    if dataset not in {"WINDFOR", "FUELHH"}:
        raise ValueError("Unknown source dataset")
    model, membership = (
        (ForecastVersion, ReleaseForecastMember)
        if dataset == "WINDFOR"
        else (ActualVersion, ReleaseActualMember)
    )
    with engine.connect() as connection:
        query = (
            select(model)
            .join(membership, membership.version_id == model.id)
            .where(membership.release_id == release_id)
            .distinct()
        )
        return [dict(row) for row in connection.execute(query).mappings()]


def export_archive(engine: Engine, release_id: str, path: Path) -> None:
    from backend.app.ingestion.archive import SourceRequest, write_archive

    with engine.connect() as connection:
        records = (
            connection.execute(
                select(RawBatchRecord)
                .join(ReleaseBatchMember)
                .where(ReleaseBatchMember.release_id == release_id)
            )
            .mappings()
            .all()
        )
    if not records:
        raise ValueError("Unknown release or release without raw batches")
    batches = [
        RawBatch(
            SourceRequest(row["dataset"], row["parameters"]),
            row["received_at"],
            gzip.decompress(row["payload_gzip"]),
        )
        for row in records
    ]
    if any(
        batch.payload_sha256 != row["payload_sha256"]
        for batch, row in zip(batches, records, strict=True)
    ):
        raise ValueError("Stored raw-response checksum mismatch")
    write_archive(path, batches, complete=True)


def release_provenance(engine: Engine, release_id: str) -> list[dict]:
    from backend.app.ingestion.archive import iso

    with engine.connect() as connection:
        records = (
            connection.execute(
                select(
                    RawBatchRecord.id,
                    RawBatchRecord.dataset,
                    RawBatchRecord.source_url,
                    RawBatchRecord.payload_sha256,
                    RawBatchRecord.received_at,
                )
                .join(ReleaseBatchMember)
                .where(ReleaseBatchMember.release_id == release_id)
                .order_by(RawBatchRecord.id)
            )
            .mappings()
            .all()
        )
    return [dict(row) | {"received_at": iso(row["received_at"])} for row in records]
