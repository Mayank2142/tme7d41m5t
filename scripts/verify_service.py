"""Read-only release gate against a running service; no live Elexon dependency."""

import argparse
import csv
import hashlib
import io
import json
import math
import re
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RELEASE = "f61cecb1c14d91cfc32f10c74a9945fd2cf7f1851abd8ca6b0eb3f3e8975b052"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def verify(base_url, timeout):
    base = base_url.rstrip("/")
    checks = []
    fingerprints = {}

    def get(path, expected=200, method="GET"):
        url = urllib.parse.urljoin(base + "/", path.lstrip("/"))
        assert urllib.parse.urlsplit(url).netloc == urllib.parse.urlsplit(base).netloc
        try:
            response = urllib.request.urlopen(
                urllib.request.Request(url, method=method), timeout=30
            )
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read()
            assert response.status == expected, (path, response.status, body[:150])
            headers = response.headers
            assert headers.get("X-Request-ID"), path
            assert headers.get("X-Content-Type-Options") == "nosniff"
            assert headers.get("X-Frame-Options") == "DENY"
            assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
            if path.startswith(("/api/", "/health/")):
                assert headers["Cache-Control"] == "no-store"
            return body, headers

    def read_json(path, expected=200):
        body, headers = get(path, expected)
        assert headers.get_content_type() == "application/json"
        result = json.loads(body)
        if expected != 200:
            assert result["request_id"] == headers["X-Request-ID"]
            assert set(result) == {"code", "message", "request_id", "errors"}
            assert not any(
                term in body.lower() for term in (b"traceback", b"password", b"sqlalchemy")
            )
        return result, headers

    deadline = time.monotonic() + timeout
    while True:
        try:
            read_json("/health/ready")
            break
        except (OSError, AssertionError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    read_json("/health/live")
    config, _ = read_json("/api/v1/config")
    assert config["dataset"]["release_id"] == RELEASE
    assert config["dataset"]["status"] == "available"
    checks.append("readiness, accepted seed and safe response headers")

    def analysis(path):
        result, headers = read_json(path + "&release_id=" + RELEASE)
        identity = digest(result["context"])
        assert identity == result["analysis_context_id"] == headers["X-Analysis-Context-ID"]
        assert result["context"]["release_id"] == headers["X-Dataset-Release"] == RELEASE
        assert result["context"]["build_sha"] == config["build_sha"]
        fingerprints[path] = digest(result)
        payload, csv_headers = get(result["export_url"])
        assert csv_headers.get_content_type() == "text/csv"
        assert csv_headers["X-Analysis-Context-ID"] == identity
        assert csv_headers["X-Dataset-Release"] == RELEASE
        rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
        assert {row["analysis_context_id"] for row in rows} == {identity}
        assert {row["release_id"] for row in rows} == {RELEASE}
        assert all("Elexon Limited" in row["attribution"] for row in rows)
        fingerprints[result["export_url"]] = hashlib.sha256(payload).hexdigest()
        return result, rows

    for date, cutoff, expected in (
        ("2026-01-01", "09:00", 18781),
        ("2026-01-31", "09:00", 10099),
        ("2026-01-31", "09:45", 10474),
    ):
        result, rows = analysis(f"/api/v1/decision-view?decision_date={date}&cutoff_local={cutoff}")
        points = result["analysis"]["points"]
        window = result["analysis"]["window"]
        assert len(points) == len(rows) == 24
        assert points[0]["forecast"]["generation_mw"] == expected
        assert window["delivery_date"] == ("2026-01-02" if date.endswith("01") else "2026-02-01")
        assert not any("actual" in key or "error" in key for key in rows[0])
        for point, row in zip(points, rows, strict=True):
            assert point["forecast"]["publication_utc"] <= window["cutoff_utc"]
            assert float(row["forecast_mw"]) == point["forecast"]["generation_mw"]
            assert (
                json.loads(row["forecast_source_version_ids"])
                == point["forecast"]["source_version_ids"]
            )
            assert row["target_start_utc"] == point["target_start_utc"]
    checks.append("January boundaries, cutoff publication eligibility and forecast-only CSV")

    for cutoff in ("09:00", "09:45"):
        result, rows = analysis(
            "/api/v1/accuracy?decision_from=2026-01-01&decision_to=2026-01-31&cutoff_local="
            + cutoff
        )
        assert len(rows) == 1488
        assert sum(row["row_type"] == "comparison_target" for row in rows) == 744
        points = {
            point["target_start_utc"]: point
            for day in result["analysis"]["days"]
            for point in day["points"]
        }
        errors = []
        for row in rows:
            if row["row_type"] == "actual_only":
                assert row["used_in_metrics"] == "false"
                assert row["forecast_mw"] == row["error_mw"] == ""
                continue
            assert row["used_in_metrics"] == "true"
            error = float(row["forecast_mw"]) - float(row["actual_mw"])
            assert error == float(row["error_mw"]) == points[row["target_start_utc"]]["error_mw"]
            assert json.loads(row["actual_source_version_ids"])
            errors.append(error)
        assert len(errors) == result["analysis"]["coverage"]["paired"] == 744
        independent = {
            "mae_mw": statistics.mean(map(abs, errors)),
            "rmse_mw": math.sqrt(statistics.mean(error * error for error in errors)),
            "bias_mw": statistics.mean(errors),
            "p90_absolute_error_mw": statistics.quantiles(
                list(map(abs, errors)), n=100, method="inclusive"
            )[89],
        }
        for key, value in independent.items():
            assert math.isclose(value, result["analysis"]["metrics"][key], rel_tol=1e-12)
    checks.append("1,488 CSV rows per cutoff and four independently recomputed metrics")

    quality, _ = read_json("/api/v1/data-quality?release_id=" + RELEASE)
    assert quality["release_id"] == RELEASE
    assert len(quality["raw_batches"]) == 10
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", batch["payload_sha256"]) for batch in quality["raw_batches"]
    )
    fingerprints["quality"] = digest(quality)
    checks.append("pinned raw-response provenance")
    for path, status in (
        ("/api/v1/decision-view?decision_date=2026-02-01", 422),
        ("/api/v1/decision-view?decision_date=2026-01-01&decision_date=2026-01-02", 422),
        ("/api/v1/accuracy?decision_from=2026-01-31&decision_to=2026-01-01", 422),
        ("/api/v1/data-quality?release_id=" + "0" * 64, 404),
        (result["export_url"].replace(result["analysis_context_id"], "0" * 64), 409),
        ("/api/v1/admin", 404),
    ):
        read_json(path, status)
    get("/api/v1/config", 405, method="POST")
    checks.append("safe validation, stale-download guard and read-only public routes")
    html, headers = get("/")
    assert headers["Cache-Control"] == "no-cache"
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html.decode())
    assert assets
    for asset in assets:
        _, headers = get(asset)
        assert "immutable" in headers["Cache-Control"]
    get("/assets/missing-phase6.js", 404)
    checks.append("real built assets, CSP and cache boundaries")
    return {
        "base_url": base,
        "release_id": RELEASE,
        "build_sha": config["build_sha"],
        "checks": checks,
        "stable_fingerprint": digest(fingerprints),
        "fingerprints": fingerprints,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("output/service-verification.json"))
    parser.add_argument("--readiness-timeout", type=int, default=90)
    args = parser.parse_args()
    result = verify(args.base_url, args.readiness_timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps({key: value for key, value in result.items() if key != "fingerprints"}, indent=2)
    )


if __name__ == "__main__":
    main()
