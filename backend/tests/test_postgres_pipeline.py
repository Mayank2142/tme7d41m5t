"""Real PostgreSQL integration in isolated schemas, never a SQLite substitute."""

import csv
import gzip
import io
import json
import os
import shutil
import sys
from datetime import UTC, date, datetime, time
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.exc import DBAPIError

from backend.app.config import Settings
from backend.app.domain.analysis import analyze_accuracy, analyze_decision
from backend.app.ingestion.archive import RawBatch, canonical, read_archive, write_archive
from backend.app.main import create_app
from backend.app.persistence.analysis import load_analysis_sources, resolve_release
from backend.app.persistence.migrate import migrate
from backend.app.persistence.models import Base, ForecastVersion, IngestionRun
from backend.app.persistence.releases import (
    dataset_state,
    export_archive,
    import_archive,
    release_versions,
)

SEED = Path("data/snapshots/january_2026.json.gz")


@pytest.fixture(scope="module")
def database():
    url = os.getenv("GRID_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set GRID_TEST_DATABASE_URL to run real PostgreSQL integration tests")
    admin = create_engine(url, connect_args={"connect_timeout": 3})
    schema = "winddesk_test_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url,
        connect_args={"connect_timeout": 3, "options": f"-c search_path={schema} -c timezone=UTC"},
    )
    try:
        migrate(engine)
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        import_archive(engine, SEED)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_seed_retry_immutability_failed_candidate_and_replay(database, tmp_path, monkeypatch):
    original = import_archive(database, SEED)
    assert original["accepted"]
    assert dataset_state(database).release["id"] == original["release_id"]
    repeat = import_archive(database, SEED)
    assert repeat["release_id"] == original["release_id"]
    with database.connect() as connection:
        count = connection.scalar(select(func.count()).select_from(ForecastVersion))
    assert count == original["quality"]["forecast_versions"]
    rows = release_versions(database, original["release_id"], "WINDFOR")
    assert rows and rows[0]["target_start_utc"].utcoffset().total_seconds() == 0
    with pytest.raises(DBAPIError), database.begin() as connection:
        connection.execute(
            update(ForecastVersion)
            .where(ForecastVersion.id == rows[0]["id"])
            .values(generation_mw=0)
        )
    batches = read_archive(SEED)
    changed = []
    for source in batches:
        payload = source.payload
        if source.request.dataset == "FUELHH":
            records = [row for row in source.rows() if row["startTime"] != "2026-01-02T00:00:00Z"]
            payload = canonical(records)
        changed.append(RawBatch(source.request, datetime.now(UTC), payload))
    broken = tmp_path / "missing.gz"
    write_archive(broken, changed, complete=True)
    rejected = import_archive(database, broken)
    assert not rejected["accepted"] and rejected["quality"]["valid_actual_half_hours"] == 1487
    with pytest.raises(ValueError, match="accepted"):
        resolve_release(database, rejected["release_id"])
    assert dataset_state(database).release["id"] == original["release_id"]
    assert len(release_versions(database, original["release_id"], "FUELHH")) == 1488
    restored = tmp_path / "restored.gz"
    export_archive(database, original["release_id"], restored)
    restored_batches = read_archive(restored)
    assert {batch.payload_sha256 for batch in restored_batches} == {
        batch.payload_sha256 for batch in batches
    }
    assert import_archive(database, restored)["release_id"] == original["release_id"]
    # A new parser can add versions for the same raw bytes without changing old release membership.
    import backend.app.ingestion.normalize as parser

    with monkeypatch.context() as changed_parser:
        changed_parser.setattr(parser, "PARSER_VERSION", "test_reparse_version")
        reparsed = import_archive(database, SEED)
    assert reparsed["release_id"] != original["release_id"]
    # Even while another parser's release is active, the analysis adapter pins the
    # requested old members, including their original source-version identities.
    pinned = load_analysis_sources(database, original["release_id"])
    point = analyze_decision(pinned.forecasts, date(2026, 1, 1), time(9)).points[0]
    assert point.forecast.generation_mw == 18781
    assert point.forecast.source_version_ids[0] in {row["id"] for row in rows}
    assert {row["id"] for row in release_versions(database, original["release_id"], "WINDFOR")} == {
        row["id"] for row in rows
    }
    # Restore the original active release through the normal idempotent import path.
    assert import_archive(database, SEED)["release_id"] == original["release_id"]
    doc = json.loads(gzip.decompress(restored.read_bytes()))
    doc["batches"][0]["payload_sha256"] = "0" * 64
    restored.write_bytes(gzip.compress(canonical(doc)))
    with pytest.raises(ValueError, match="integrity"):
        import_archive(database, restored)
    assert dataset_state(database).release["id"] == original["release_id"]
    with database.connect() as connection:
        assert (
            connection.scalar(
                select(func.count())
                .select_from(IngestionRun)
                .where(IngestionRun.status == "failed")
            )
            == 1
        )


def test_readiness_and_metadata_follow_the_active_release(database, tmp_path):
    app = create_app(Settings(_env_file=None, environment="test", frontend_dist=tmp_path))
    unused = app.state.database
    with TestClient(app) as client:
        app.state.database = database
        try:
            ready = client.get("/health/ready")
            config = client.get("/api/v1/config")
            quality = client.get("/api/v1/data-quality")
        finally:
            app.state.database = unused
    assert ready.status_code == 200
    assert config.json()["stage"] == "data_ready"
    assert config.json()["dataset"]["forecast_versions"] == 19856
    assert quality.status_code == 200
    assert quality.json()["release_id"] == ready.json()["release_id"]
    assert "payload_gzip" not in quality.text and "database_url" not in config.text


def test_analysis_adapter_loads_only_accepted_release_members(database):
    sources = load_analysis_sources(database)
    assert sources.release_id == dataset_state(database).release["id"]
    report = analyze_accuracy(
        sources.forecasts, sources.actuals, date(2026, 1, 1), date(2026, 1, 31), time(9)
    )
    assert report.coverage.expected == report.coverage.paired == 744
    assert report.actual_source_coverage.valid == 1488
    assert report.days[0].points[0].error_mw == 3553
    with pytest.raises(ValueError, match="accepted"):
        resolve_release(database, "0" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        resolve_release(database, "abbreviated-id")


def test_public_analysis_json_csv_quality_and_read_only_behavior(database, tmp_path):
    app = create_app(Settings(_env_file=None, environment="test", frontend_dist=tmp_path))
    unused = app.state.database
    with database.connect() as connection:
        before = connection.scalar(select(func.count()).select_from(IngestionRun))
    with TestClient(app) as client:
        app.state.database = database
        try:
            decision = client.get("/api/v1/decision-view?decision_date=2026-01-31")
            assert decision.status_code == 200, decision.text
            assert "actual" not in decision.text
            assert decision.json()["analysis"]["window"]["delivery_date"] == "2026-02-01"
            accuracy = client.get(
                "/api/v1/accuracy?decision_from=2026-01-01&decision_to=2026-01-31"
            )
            assert accuracy.status_code == 200, accuracy.text
            body = accuracy.json()
            export = client.get(body["export_url"])
            assert export.status_code == 200
            rows = list(csv.DictReader(io.StringIO(export.text)))
            paired = [row for row in rows if row["used_in_metrics"] == "true"]
            assert len(rows) == 1488 and len(paired) == 744
            assert sum(abs(int(row["error_mw"])) for row in paired) / 744 == pytest.approx(
                body["analysis"]["metrics"]["mae_mw"]
            )
            assert export.headers["x-analysis-context-id"] == body["analysis_context_id"]
            quality = client.get(body["source"]["data_quality_url"])
            assert quality.status_code == 200
            assert quality.json()["release_id"] == body["context"]["release_id"]
            assert len(quality.json()["raw_batches"]) == 10
            with database.connect() as connection:
                rejected_id = connection.scalar(
                    text("SELECT id FROM dataset_release WHERE status='rejected' LIMIT 1")
                )
            if rejected_id is not None:
                rejected = client.get("/api/v1/data-quality?release_id=" + rejected_id)
                assert (
                    rejected.status_code == 404 and rejected.json()["code"] == "RELEASE_NOT_FOUND"
                )
        finally:
            app.state.database = unused
    with database.connect() as connection:
        after = connection.scalar(select(func.count()).select_from(IngestionRun))
    assert after == before


def test_seed_cli_reads_immutable_inputs_and_writes_only_an_explicit_report(
    database, tmp_path, monkeypatch
):
    from backend.app import cli

    archive = tmp_path / "bundled" / "january_2026.json.gz"
    archive.parent.mkdir()
    shutil.copyfile(SEED, archive)
    manifest = archive.with_name("manifest.json")
    manifest.write_text('{"input":"immutable"}\n')
    before = manifest.read_bytes()
    archive.chmod(0o444)
    manifest.chmod(0o444)
    monkeypatch.setattr(cli, "create_database_engine", lambda _: database)
    try:
        monkeypatch.setattr(sys, "argv", ["winddesk", "seed", "--archive", str(archive)])
        with pytest.raises(SystemExit) as result:
            cli.main()
        assert result.value.code == 0
        assert manifest.read_bytes() == before
        report = tmp_path / "operator-output" / "manifest.json"
        monkeypatch.setattr(
            sys, "argv", ["winddesk", "seed", "--archive", str(archive), "--report", str(report)]
        )
        with pytest.raises(SystemExit) as result:
            cli.main()
        assert result.value.code == 0
        assert json.loads(report.read_text())["release_id"] == dataset_state(database).release["id"]
        assert manifest.read_bytes() == before
    finally:
        archive.chmod(0o644)
        manifest.chmod(0o644)
