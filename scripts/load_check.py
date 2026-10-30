"""Bounded loopback-only load check; reports measured capacity, not a traffic guarantee."""

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

PATH = "/api/v1/accuracy?decision_from=2026-01-01&decision_to=2026-01-31&cutoff_local=09%3A00"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--output", type=Path, default=Path("output/load-check.json"))
    args = parser.parse_args()
    target = urlsplit(args.base_url)
    if target.hostname not in {"127.0.0.1", "localhost"} or target.scheme != "http":
        parser.error("This tool is restricted to an explicitly local HTTP service")
    if not 1 <= args.users <= 100 or not args.users <= args.requests <= 2000:
        parser.error("Use 1..100 users and users..2000 requests")
    base = args.base_url.rstrip("/")
    with urlopen(base + "/api/v1/config", timeout=30) as response:
        config = json.load(response)
    path = PATH + "&release_id=" + config["dataset"]["release_id"]

    def fetch(_):
        started = perf_counter()
        try:
            with urlopen(
                Request(base + path, headers={"Accept-Encoding": "gzip"}), timeout=30
            ) as r:
                data = r.read(8 * 1024**2 + 1)
                if len(data) > 8 * 1024**2:
                    return "oversized", perf_counter() - started, None
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return str(r.status), perf_counter() - started, hashlib.sha256(data).hexdigest()
        except HTTPError as exc:
            exc.close()
            return str(exc.code), perf_counter() - started, None
        except (URLError, TimeoutError, OSError):
            return "connection_error", perf_counter() - started, None

    warm = fetch(0)
    if warm[0] != "200":
        raise SystemExit("Warm-up failed; ensure the service is ready and the quota has reset")
    started = perf_counter()
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        results = list(pool.map(fetch, range(args.requests)))
    elapsed = perf_counter() - started
    statuses = Counter(result[0] for result in results)
    durations = sorted(result[1] * 1000 for result in results)
    identical = all(digest == warm[2] for status, _, digest in results if status == "200")
    report = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "build_sha": config["build_sha"],
        "base_url": base,
        "release_id": config["dataset"]["release_id"],
        "users": args.users,
        "requests": args.requests,
        "statuses": dict(statuses),
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(args.requests / elapsed, 2),
        "latency_ms": {
            f"p{percent}": round(durations[math.ceil(len(durations) * percent / 100) - 1], 2)
            for percent in (50, 95, 99)
        },
        "all_successful_payloads_identical": identical,
        "note": "Warm immutable monthly accuracy, loopback, HTTP connections per request; "
        "excludes internet latency, CDN/WAF, cold starts and multi-instance quotas.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not identical or any(status != "200" for status in statuses):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
