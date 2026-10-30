"""Public contracts and exports, including missing data and release changes."""

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from math import sqrt
from pathlib import Path
from statistics import mean, quantiles

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, ProgrammingError

from backend.app.api.dataset import get_dataset_reader
from backend.app.config import Settings
from backend.app.domain.sources import SourceIndex, SourceVersion
from backend.app.ingestion.archive import read_archive
from backend.app.ingestion.normalize import normalize
from backend.app.main import create_app
from backend.app.persistence.analysis import NoAcceptedRelease, ReleaseNotFound

SEED = Path("data/snapshots/january_2026.json.gz")
MANIFEST = json.loads(Path("data/snapshots/manifest.json").read_text())
RELEASE = MANIFEST["release_id"]
OTHER = "a" * 64
DAY = "2026-01-01"
ACCURACY = "/api/v1/accuracy?decision_from=2026-01-01&decision_to=2026-01-31"
DECISION = "/api/v1/decision-view?decision_date=2026-01-01"


@pytest.fixture(scope="module")
def source_indexes():
    records = {"WINDFOR": [], "FUELHH": []}
    for batch in read_archive(SEED):
        records[batch.request.dataset].extend(normalize(batch))
    return {dataset: SourceIndex(dataset, rows) for dataset, rows in records.items()}


class Reader:
    def __init__(self, indexes):
        self.indexes = indexes
        self.active = RELEASE
        self.release_calls = []
        self.source_calls = []
        self.flip_during_read = False
        self.failure = None

    def release(self, release_id):
        self.release_calls.append(release_id)
        if self.failure:
            raise self.failure
        if release_id is None and self.active is None:
            raise NoAcceptedRelease("No matching accepted dataset release")
        pinned = release_id or self.active
        if pinned not in {RELEASE, OTHER}:
            raise ReleaseNotFound("No matching accepted dataset release")
        return {
            "id": pinned,
            "parser_version": "elexon_streams_v2",
            "created_at": datetime(2026, 10, 29, tzinfo=UTC),
            "quality": MANIFEST["quality"],
        }

    def forecasts(self, release_id):
        self.source_calls.append(("WINDFOR", release_id))
        if self.flip_during_read:
            self.active = OTHER
        return self.indexes["WINDFOR"] if release_id == RELEASE else SourceIndex("WINDFOR", [])

    def actuals(self, release_id):
        self.source_calls.append(("FUELHH", release_id))
        return self.indexes["FUELHH"]

    def provenance(self, release_id):
        self.source_calls.append(("provenance", release_id))
        return [
            {key: batch[key] for key in ("id", "dataset", "source_url", "received_at")}
            | {"payload_sha256": batch["sha256"]}
            for batch in MANIFEST["raw_batches"]
        ]


@pytest.fixture
def api(source_indexes, tmp_path):
    app = create_app(
        Settings(_env_file=None, environment="test", frontend_dist=tmp_path, build_sha="test-build")
    )
    reader = Reader(source_indexes)
    app.dependency_overrides[get_dataset_reader] = lambda: reader
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, reader, app


def rows(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in response.headers["content-disposition"]
    return list(csv.DictReader(io.StringIO(response.text)))


def test_decision_contract_and_export_have_only_eligible_forecasts(api):
    client, reader, _ = api
    response = client.get(DECISION)
    assert response.status_code == 200, response.text
    body = response.json()
    assert reader.release_calls == [None]
    assert reader.source_calls == [("WINDFOR", RELEASE)]
    assert (
        "actual" not in response.text
        and "metrics" not in response.text
        and "error_mw" not in response.text
    )
    assert body["analysis"]["window"]["delivery_start_utc"] == "2026-01-02T00:00:00Z"
    assert body["analysis"]["points"][0]["forecast"]["generation_mw"] == 18781
    assert body["context"]["cutoff_local"] == "09:00"
    assert body["analysis"]["coverage"]["valid"] == 24
    exported = client.get(body["export_url"])
    records = rows(exported)
    assert len(records) == 24
    assert not any("actual" in key or "error" in key or "metrics" in key for key in records[0])
    for record, point in zip(records, body["analysis"]["points"], strict=True):
        assert record["target_start_utc"] == point["target_start_utc"]
        assert int(record["forecast_mw"]) == point["forecast"]["generation_mw"]
        assert record["forecast_published_at"] == point["forecast"]["publication_utc"]
        assert record["forecast_published_at"] <= record["cutoff_utc"]
        assert (
            json.loads(record["forecast_source_version_ids"])
            == point["forecast"]["source_version_ids"]
        )
        assert record["analysis_context_id"] == body["analysis_context_id"]
        assert record["target_start_local"].endswith("+00:00")
    assert exported.headers["x-analysis-context-id"] == response.headers["x-analysis-context-id"]


def test_accuracy_csv_recomputes_all_metrics_and_preserves_half_hours(api):
    client, reader, _ = api
    response = client.get(ACCURACY)
    assert response.status_code == 200, response.text
    body = response.json()
    assert reader.release_calls == [None]
    assert reader.source_calls == [("WINDFOR", RELEASE), ("FUELHH", RELEASE)]
    exported = client.get(body["export_url"])
    records = rows(exported)
    assert len(records) == 1488
    comparisons = [row for row in records if row["row_type"] == "comparison_target"]
    unscored = [row for row in records if row["row_type"] == "actual_only"]
    assert len(comparisons) == len(unscored) == 744
    assert all(row["comparison_expected"] == "true" for row in comparisons)
    assert all(
        row["used_in_metrics"] == "false" and row["error_mw"] == "" and row["forecast_mw"] == ""
        for row in unscored
    )
    assert records[-1]["target_start_utc"] == "2026-02-01T23:30:00Z"
    errors = [int(row["error_mw"]) for row in comparisons if row["used_in_metrics"] == "true"]
    metrics = body["analysis"]["metrics"]
    assert metrics["paired_targets"] == len(errors) == 744
    assert metrics["mae_mw"] == pytest.approx(mean(abs(error) for error in errors))
    assert metrics["rmse_mw"] == pytest.approx(sqrt(mean(error**2 for error in errors)))
    assert metrics["bias_mw"] == pytest.approx(mean(errors))
    assert metrics["p90_absolute_error_mw"] == pytest.approx(
        quantiles([abs(error) for error in errors], n=10, method="inclusive")[8]
    )
    points = [point for day in body["analysis"]["days"] for point in day["points"]]
    for record, point in zip(comparisons, points, strict=True):
        assert int(record["error_mw"]) == point["error_mw"]
        assert int(record["absolute_error_mw"]) == abs(point["error_mw"])
        assert (
            json.loads(record["actual_source_version_ids"]) == point["actual"]["source_version_ids"]
        )
        assert record["analysis_context_id"] == body["analysis_context_id"]
    assert exported.headers["x-dataset-release"] == RELEASE


def test_context_is_canonical_and_changes_with_filters_mode_and_build(api):
    client, _, app = api
    first = client.get(DECISION).json()
    explicit = client.get(DECISION + "&cutoff_local=09%3A00&release_id=" + RELEASE).json()
    assert first == explicit
    expected = hashlib.sha256(
        json.dumps(
            first["context"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    assert first["analysis_context_id"] == expected
    later = client.get(DECISION + "&cutoff_local=09:45").json()
    assert later["analysis_context_id"] != expected
    next_day = client.get(DECISION.replace(DAY, "2026-01-02")).json()
    assert next_day["analysis_context_id"] != expected
    accuracy = client.get(ACCURACY.replace("2026-01-31", DAY)).json()
    assert accuracy["analysis_context_id"] != expected
    app.state.settings = app.state.settings.model_copy(update={"build_sha": "next-build"})
    changed = client.get(first["export_url"])
    assert changed.status_code == 409 and changed.json()["code"] == "ANALYSIS_CONTEXT_MISMATCH"


def test_active_release_change_during_read_and_export_cannot_mix_members(api):
    client, reader, _ = api
    reader.flip_during_read = True
    body = client.get(ACCURACY).json()
    assert reader.active == OTHER
    assert reader.release_calls == [None]
    assert reader.source_calls == [("WINDFOR", RELEASE), ("FUELHH", RELEASE)]
    exported = client.get(body["export_url"])
    assert {row["release_id"] for row in rows(exported)} == {RELEASE}
    assert exported.headers["x-analysis-context-id"] == body["analysis_context_id"]
    current = client.get(ACCURACY).json()
    assert current["context"]["release_id"] == OTHER
    assert current["analysis"]["metrics"]["mae_mw"] is None
    assert current["analysis_context_id"] != body["analysis_context_id"]


def test_valid_missing_data_returns_200_nulls_and_reconciled_export(api):
    client, reader, _ = api
    reader.indexes = {"WINDFOR": SourceIndex("WINDFOR", []), "FUELHH": SourceIndex("FUELHH", [])}
    body = client.get(ACCURACY).json()
    assert body["analysis"]["metrics"]["reason"] == "NO_VALID_PAIRS"
    assert body["analysis"]["metrics"]["mae_mw"] is None
    assert body["analysis"]["coverage"]["forecast_missing"] == 744
    records = rows(client.get(body["export_url"]))
    assert len(records) == 1488
    comparisons = [row for row in records if row["comparison_expected"] == "true"]
    assert len(comparisons) == 744
    assert all(
        row["forecast_mw"] == row["actual_mw"] == row["error_mw"] == "" for row in comparisons
    )
    assert {row["reason"] for row in comparisons} == {"NO_PRE_CUTOFF_PUBLICATION"}


@pytest.mark.parametrize("include_invalid", [True, False])
def test_invalid_latest_key_and_negative_errors_survive_json_csv_round_trip(api, include_invalid):
    client, reader, _ = api
    target = datetime(2026, 1, 2, tzinfo=UTC)
    publication = datetime(2026, 1, 1, 8, tzinfo=UTC)

    def fact(dataset, value, issue, identity):
        return SourceVersion(
            hashlib.sha256(identity.encode()).hexdigest(),
            dataset,
            target,
            issue,
            value,
            None,
            None,
            None,
        )

    old = fact("WINDFOR", 2, publication, "old")
    invalid = fact("WINDFOR", None, publication.replace(minute=30), "invalid")
    actual = fact("FUELHH", 5, target.replace(minute=30), "actual")
    reader.indexes = {
        "WINDFOR": SourceIndex("WINDFOR", [old, invalid] if include_invalid else [old]),
        "FUELHH": SourceIndex("FUELHH", [actual]),
    }
    body = client.get(ACCURACY).json()
    record = rows(client.get(body["export_url"]))[0]
    if include_invalid:
        assert record["evaluation_state"] == "forecast_invalid"
        assert record["reason"] == "NULL_GENERATION"
        assert record["forecast_mw"] == record["error_mw"] == ""
        assert record["forecast_published_at"] == "2026-01-01T08:30:00Z"
    else:
        assert record["error_mw"] == "-3" and record["absolute_error_mw"] == "3"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/decision-view",
        DECISION + "&cutoff_local=9:00",
        DECISION + "&cutoff_local=09:00:00",
        DECISION + "&cutoff_local=09:00Z",
        DECISION + "&cutoff_local=24:00",
        DECISION.replace(DAY, "2026-02-01"),
        DECISION.replace(DAY, "1767225600"),
        DECISION.replace(DAY, "2026-01-01T00:00:00Z"),
        DECISION + "&release_id=short",
        DECISION + "&unknown=private-value",
        ACCURACY + "&comparison_policy=hourly_mean_v1",
        "/api/v1/accuracy?decision_from=2026-01-31&decision_to=2026-01-01",
        "/api/v1/export.csv?mode=decision",
        "/api/v1/export.csv?mode=accuracy&decision_from=2026-01-01",
        "/api/v1/export.csv?mode=decision&decision_date=2026-01-01&decision_to=2026-01-02",
        "/api/v1/export.csv?mode=accuracy&decision_from=2026-01-01&decision_to=2026-01-02&decision_date=2026-01-01",
        "/api/v1/data-quality?release_id=short",
    ],
)
def test_invalid_filters_are_422_before_any_source_reads(api, path):
    client, reader, _ = api
    response = client.get(path)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "INVALID_FILTERS"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "private-value" not in response.text
    assert reader.release_calls == reader.source_calls == []


def test_duplicate_filters_are_rejected_even_if_values_agree(api):
    client, reader, _ = api
    response = client.get(DECISION + "&decision_date=" + DAY)
    assert response.status_code == 422 and response.json()["code"] == "DUPLICATE_FILTER"
    assert reader.release_calls == []


def test_unknown_no_active_and_database_failures_have_safe_statuses(api):
    client, reader, _ = api
    unknown = client.get(DECISION + "&release_id=" + "0" * 64)
    assert unknown.status_code == 404 and unknown.json()["code"] == "RELEASE_NOT_FOUND"
    reader.active = None
    response = client.get(DECISION)
    assert response.status_code == 503 and response.json()["code"] == "NO_ACCEPTED_DATASET"
    reader.failure = OperationalError("sensitive SQL", {}, Exception("private-password"))
    response = client.get(DECISION)
    assert response.status_code == 503 and response.json()["code"] == "DATABASE_UNAVAILABLE"
    assert "sensitive" not in response.text and "private-password" not in response.text

    class MissingTable(Exception):
        sqlstate = "42P01"

    reader.failure = ProgrammingError("sensitive SQL", {}, MissingTable())
    response = client.get(DECISION)
    assert response.status_code == 503 and response.json()["code"] == "SCHEMA_NOT_INITIALIZED"
    reader.failure = RuntimeError("private-password")
    response = client.get(DECISION)
    assert response.status_code == 500 and response.json()["code"] == "INTERNAL_ERROR"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "private-password" not in response.text


def test_quality_is_typed_and_pinned_and_unsupported_methods_are_json(api):
    client, reader, _ = api
    response = client.get("/api/v1/data-quality?release_id=" + RELEASE)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["release_id"] == RELEASE and len(body["raw_batches"]) == 10
    assert len(body["raw_batches"][0]["payload_sha256"]) == 64
    assert body["created_at"].endswith("Z")
    assert body["quality"]["actual_versions"] == 1488
    assert reader.source_calls == [("provenance", RELEASE)]
    assert "payload_gzip" not in response.text and "payload_base64" not in response.text
    assert "password" not in response.text
    response = client.post(DECISION)
    assert response.status_code == 405 and response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_config_advertises_versions_without_breaking_its_existing_stage(api):
    client, _, _ = api
    # This call uses the existing readiness dependency; no test database is needed.
    from backend.app.api.dataset import get_dataset_state
    from backend.app.persistence.releases import DatasetState

    client.app.dependency_overrides[get_dataset_state] = lambda: DatasetState(True, True)
    body = client.get("/api/v1/config").json()
    assert body["stage"] == "foundation"
    assert body["supported_comparison_policies"] == ["source_timestamp_v1"]
    assert body["metrics_version"] == "metrics_v1"


def test_openapi_separates_decision_and_accuracy_and_declares_csv(api):
    client, _, _ = api
    schema = client.get("/api/openapi.json").json()
    decision = schema["paths"]["/api/v1/decision-view"]["get"]
    accuracy = schema["paths"]["/api/v1/accuracy"]["get"]
    assert decision["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DecisionResponse"
    )
    assert accuracy["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/AccuracyResponse"
    )
    assert "text/csv" in schema["paths"]["/api/v1/export.csv"]["get"]["responses"]["200"]["content"]


def test_cached_json_csv_preserve_context_and_observe_new_active_release(api):
    client, reader, _ = api
    first = client.get(DECISION)
    body = first.json()
    again = client.get(DECISION)
    export = client.get(body["export_url"])
    assert again.content == first.content and export.status_code == 200
    assert reader.source_calls == [("WINDFOR", RELEASE)]
    assert export.headers["x-analysis-context-id"] == body["analysis_context_id"]
    assert (
        client.get(body["export_url"].replace(body["analysis_context_id"], "0" * 64)).status_code
        == 409
    )
    assert (
        client.get(DECISION + "&cutoff_local=09:45").json()["analysis_context_id"]
        != body["analysis_context_id"]
    )
    reader.active = OTHER
    moved = client.get(DECISION).json()
    assert moved["context"]["release_id"] == OTHER
    assert moved["analysis_context_id"] != body["analysis_context_id"]
    # A warm result must never conceal an unavailable/revoked source release.
    reader.failure = ReleaseNotFound("revoked")
    assert client.get(DECISION).status_code == 404


def test_analysis_is_compressed_without_changing_its_payload(api):
    client, _, _ = api
    compressed = client.get(ACCURACY, headers={"Accept-Encoding": "gzip"})
    plain = client.get(ACCURACY, headers={"Accept-Encoding": "identity"})
    assert compressed.headers["content-encoding"] == "gzip"
    assert int(compressed.headers["content-length"]) < len(plain.content) / 2
    assert compressed.content == plain.content
    assert "Accept-Encoding" in compressed.headers["vary"]
