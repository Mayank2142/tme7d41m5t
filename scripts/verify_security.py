"""Small read-only HTTP security regression gate; does not constitute a penetration test."""

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("output/security-http.json"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if urlsplit(base).scheme not in {"http", "https"}:
        parser.error("Use an HTTP(S) service URL")
    cases = (
        ("untrusted host", "/api/v1/config", 400, {"Host": "attacker.invalid"}, None, "GET"),
        (
            "cross-site browser fetch",
            "/api/v1/config",
            403,
            {"Sec-Fetch-Site": "cross-site"},
            None,
            "GET",
        ),
        ("oversized URI", "/api/v1/config?x=" + "a" * 4100, 414, {}, None, "GET"),
        ("unwanted request body", "/api/v1/config", 413, {}, b"unwanted-body", "GET"),
        ("write method", "/api/v1/config", 405, {}, b"{}", "POST"),
        ("private environment file", "/.env", 404, {}, None, "GET"),
        ("source map", "/assets/index.js.map", 404, {}, None, "GET"),
        ("path traversal", "/assets/%2e%2e/%2e%2e/.env", 404, {}, None, "GET"),
        (
            "SQL injection",
            "/api/v1/decision-view?" + urlencode({"decision_date": "2026-01-01' OR 1=1 --"}),
            422,
            {},
            None,
            "GET",
        ),
        (
            "script injection",
            "/api/v1/decision-view?" + urlencode({"decision_date": "<script>alert(1)</script>"}),
            422,
            {},
            None,
            "GET",
        ),
    )
    checks = []
    for name, path, status, headers, body, method in cases:
        request = Request(base + path, headers=headers, data=body, method=method)
        try:
            response = urlopen(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            assert response.code == status, (name, response.code)
            assert response.headers["Cache-Control"] == "no-store", name
            assert response.headers["X-Content-Type-Options"] == "nosniff", name
            assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin", name
            data = json.load(response)
            assert data["request_id"] == response.headers["X-Request-ID"], name
            assert "<script>" not in json.dumps(data), name
        checks.append({"check": name, "status": status})
    report = {"base_url": base, "checks": checks, "passed": len(checks)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
