"""Offline source failure, integrity, normalization, and coverage checks."""

import base64
import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx2 as httpx
import pytest

from backend.app.ingestion.archive import (
    RawBatch,
    canonical,
    january_requests,
    read_archive,
    write_archive,
)
from backend.app.ingestion.client import ElexonClient, SourceError, download_january
from backend.app.ingestion.normalize import normalize
from backend.app.ingestion.validation import inspect_batches, latest_key

SEED = Path("data/snapshots/january_2026.json.gz")


def batch(rows, dataset="WINDFOR"):
    request = next(item for item in january_requests() if item.dataset == dataset)
    return RawBatch(request, datetime.now(UTC), canonical(rows))


def forecast(value, publication="2026-01-01T07:30:00Z"):
    return {
        "dataset": "WINDFOR",
        "startTime": "2026-01-02T00:00:00Z",
        "publishTime": publication,
        "generation": value,
    }


def test_real_seed_covers_every_january_decision_and_february_boundary():
    report, _ = inspect_batches(read_archive(SEED))
    assert report["status"] == "complete"
    assert report["valid_actual_half_hours"] == 1488
    assert report["valid_forecast_targets_by_cutoff"] == {"09:00": 744, "09:45": 744}
    assert report["decisions"][-1]["delivery_date"] == "2026-02-01"


def test_newest_invalid_or_conflicting_key_cannot_hide_behind_an_older_value():
    records = normalize(batch([forecast(100), forecast(None, "2026-01-01T08:30:00Z")]))
    cutoff = datetime(2026, 1, 1, 9, tzinfo=UTC)
    assert latest_key(records, cutoff) == (None, "NULL_GENERATION")
    variants = normalize(batch([forecast(100), forecast(101)]))
    assert latest_key(variants, cutoff) == (None, "CONFLICTING_SOURCE_KEY")


def test_post_cutoff_source_is_excluded_and_equal_cutoff_included():
    records = normalize(batch([forecast(100), forecast(200, "2026-01-01T09:00:00Z")]))
    assert latest_key(records, datetime(2026, 1, 1, 8, tzinfo=UTC))[0].generation_mw == 100
    assert latest_key(records, datetime(2026, 1, 1, 9, tzinfo=UTC))[0].generation_mw == 200


@pytest.mark.parametrize(
    "change",
    [
        {"generation": True},
        {"generation": 10.5},
        {"publishTime": "2026-01-01T07:30:00"},
        {"dataset": "OTHER"},
        {"startTime": 123},
    ],
)
def test_malformed_required_source_fields_are_rejected(change):
    with pytest.raises(ValueError, match="invalid required source fields"):
        normalize(batch([forecast(10) | change]))


def test_actual_metadata_and_long_dst_day_are_checked():
    row = {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "generation": 10,
        "startTime": "2026-10-25T01:00:00Z",
        "publishTime": "2026-10-25T01:30:00Z",
        "settlementDate": "2026-10-25",
        "settlementPeriod": 5,
    }
    assert normalize(batch([row], "FUELHH"))[0].quality_reason is None
    assert (
        normalize(batch([row | {"settlementPeriod": 3}], "FUELHH"))[0].quality_reason
        == "SETTLEMENT_METADATA_MISMATCH"
    )
    with pytest.raises(ValueError):
        normalize(batch([row | {"fuelType": "CCGT"}], "FUELHH"))


def test_payload_tampering_and_incomplete_archives_fail_integrity_checks(tmp_path):
    target = tmp_path / "archive.gz"
    write_archive(target, read_archive(SEED), complete=True)
    doc = json.loads(gzip.decompress(target.read_bytes()))
    doc["batches"][0]["payload_base64"] = base64.b64encode(b"[]").decode()
    target.write_bytes(gzip.compress(canonical(doc)))
    with pytest.raises(ValueError, match="integrity"):
        read_archive(target)
    write_archive(target, [], complete=False)
    with pytest.raises(ValueError, match="partial"):
        read_archive(target)


def test_retry_after_and_permanent_http_error_have_bounded_behavior():
    calls, sleeps = [], []

    def transport(request):
        calls.append(request)
        return (
            httpx.Response(429, headers={"Retry-After": "0"})
            if len(calls) == 1
            else httpx.Response(200, json=[])
        )

    with httpx.Client(transport=httpx.MockTransport(transport)) as http:
        result = ElexonClient(http, sleep=sleeps.append).fetch(january_requests()[0])
    assert len(calls) == 2 and result.attempts == 2 and len(sleeps) == 1
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(400))) as http:
        with pytest.raises(SourceError, match="400"):
            ElexonClient(
                http, sleep=lambda _: pytest.fail("Permanent errors must not retry")
            ).fetch(january_requests()[0])


def test_failed_download_resumes_from_the_saved_request_windows(tmp_path):
    requests, calls = january_requests(), []

    class Source:
        def fetch(self, request):
            calls.append(request.id)
            if len(calls) == 3:
                raise SourceError("temporary test failure")
            return RawBatch(request, datetime.now(UTC), b"[]")

    target = tmp_path / "archive.gz"
    with pytest.raises(SourceError):
        download_january(target, client=Source(), progress=lambda _: None)
    assert not target.exists()
    assert len(read_archive(target.with_suffix(".gz.partial"), allow_partial=True)) == 2
    download_january(target, client=Source(), progress=lambda _: None)
    assert len(read_archive(target)) == len(requests)
    assert calls.count(requests[0].id) == 1
