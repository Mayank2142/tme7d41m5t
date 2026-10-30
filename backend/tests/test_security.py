"""Public request backstops, cache safety, and source-file containment."""

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dataset import get_dataset_state
from backend.app.config import DEVELOPMENT_DATABASE_URL, Settings
from backend.app.main import create_app
from backend.app.persistence.releases import DatasetState
from backend.app.security import RequestLimiter


def test_peer_quota_expires_and_client_memory_is_bounded():
    now = [0.0]
    limiter = RequestLimiter(2, clock=lambda: now[0], capacity=2)
    assert limiter.retry_after("a") is None
    assert limiter.retry_after("a") is None
    assert limiter.retry_after("a") == 60
    now[0] = 1.5
    assert limiter.retry_after("a") == 59
    assert limiter.retry_after("b") is None
    now[0] = 60
    assert limiter.retry_after("a") is None
    assert limiter.retry_after("c") == 60  # New identities cannot evict an active quota.
    now[0] = 62
    assert limiter.retry_after("c") is None
    assert len(limiter._clients) == 2


def test_rate_limit_is_safe_json_and_forwarded_headers_cannot_bypass_it(tmp_path):
    app = create_app(
        Settings(
            _env_file=None, environment="test", frontend_dist=tmp_path, api_rate_limit_per_minute=2
        )
    )
    app.dependency_overrides[get_dataset_state] = lambda: DatasetState(True, True)
    with TestClient(app) as client:
        assert client.get("/api/v1/config").status_code == 200
        assert client.get("/api/v1/config").status_code == 200
        limited = client.get("/api/v1/config", headers={"X-Forwarded-For": "198.51.100.1"})
        assert limited.status_code == 429
        assert limited.json()["code"] == "RATE_LIMITED"
        assert limited.json()["request_id"] == limited.headers["x-request-id"]
        assert 1 <= int(limited.headers["retry-after"]) <= 60
        assert limited.headers["cache-control"] == "no-store"
        assert limited.headers["x-frame-options"] == "DENY"
        assert client.get("/health/live").status_code == 200


def test_injection_payloads_and_cors_cannot_open_data_or_mutation_routes(tmp_path):
    app = create_app(Settings(_env_file=None, environment="test", frontend_dist=tmp_path))
    with TestClient(app) as client:
        for filters in (
            {"decision_date": "2026-01-01' OR 1=1 --"},
            {"decision_date": "<script>alert(1)</script>"},
            {"decision_date": "2026-01-01", "release_id": "0;DROP TABLE active_release"},
            {"decision_date": "2026-01-01", "cutoff_local": "09:00;cat /etc/passwd"},
        ):
            response = client.get("/api/v1/decision-view", params=filters)
            assert response.status_code == 422
            assert response.headers["content-type"].startswith("application/json")
            assert "<script>" not in response.text
        response = client.options(
            "/api/v1/config",
            headers={"Origin": "https://attacker.example", "Access-Control-Request-Method": "POST"},
        )
        assert response.status_code == 405
        assert "access-control-allow-origin" not in response.headers


def test_static_containment_csp_and_cache_headers(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>application</html>")
    (dist / "assets" / "index-hash.js").write_text("console.log('application')")
    (tmp_path / "private.txt").write_text("private-sentinel")
    app = create_app(Settings(_env_file=None, environment="test", frontend_dist=dist))
    with TestClient(app) as client:
        html = client.get("/")
        assert html.headers["cache-control"] == "no-cache"
        assert "script-src 'self';" in html.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in html.headers["content-security-policy"]
        assert "immutable" in client.get("/assets/index-hash.js").headers["cache-control"]
        assert client.get("/assets/missing.js").headers["cache-control"] == "no-store"
        escaped = client.get("/%2e%2e/private.txt")
        assert escaped.status_code == 404 and "private-sentinel" not in escaped.text
        assert client.get("/assets/app%00.js").status_code == 404
        assert client.get("/assets/%2e%2e/index.html").status_code == 404
        assert "cdn.jsdelivr.net" in client.get("/api/docs").headers["content-security-policy"]


def test_hsts_is_limited_to_production_https(tmp_path):
    settings = Settings(
        _env_file=None,
        environment="production",
        frontend_dist=tmp_path,
        database_url=DEVELOPMENT_DATABASE_URL.replace("winddesk_local", "test-password-example"),
        allowed_hosts=["example.test", "testserver"],
    )
    with TestClient(create_app(settings), base_url="https://example.test") as client:
        assert client.get("/health/live").headers["strict-transport-security"] == "max-age=31536000"
    with TestClient(create_app(settings)) as client:
        assert "strict-transport-security" not in client.get("/health/live").headers


def test_private_build_files_are_never_served(tmp_path):
    (tmp_path / "assets").mkdir()
    for name in (".env", "private.json", "assets/app.js.map", "assets/.secret.js"):
        (tmp_path / name).write_text("private-sentinel")
    with TestClient(create_app(Settings(_env_file=None, frontend_dist=tmp_path))) as client:
        for name in (".env", "private.json", "assets/app.js.map", "assets/.secret.js"):
            response = client.get("/" + name)
            assert response.status_code == 404
            assert "private-sentinel" not in response.text


def test_request_guards_run_before_any_database_access(tmp_path):
    app = create_app(Settings(_env_file=None, environment="test", frontend_dist=tmp_path))

    def forbidden():
        raise AssertionError("Rejected traffic must not access PostgreSQL")

    app.dependency_overrides[get_dataset_state] = forbidden
    with TestClient(app) as client:
        for headers, status, code in (
            ({"Host": "attacker.example"}, 400, "INVALID_HOST"),
            ({"Sec-Fetch-Site": "cross-site"}, 403, "CROSS_SITE_REQUEST"),
            ({"Content-Length": "3000000"}, 413, "REQUEST_BODY_NOT_ALLOWED"),
            ({"X-Large": "x" * 17000}, 431, "HEADERS_TOO_LARGE"),
        ):
            response = client.get("/api/v1/config", headers=headers)
            assert response.status_code == status, response.text
            assert response.json()["code"] == code
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-content-type-options"] == "nosniff"
        assert client.get("/api/v1/config?x=" + "a" * 4100).status_code == 414
        assert client.post("/api/v1/config", json={"sql": "DROP TABLE"}).status_code == 405
        assert client.get("/health/live").status_code == 200


def test_production_docs_are_closed_and_configuration_fails_safe(tmp_path):
    import pytest
    from pydantic import ValidationError

    valid = dict(
        _env_file=None,
        environment="production",
        frontend_dist=tmp_path,
        database_url=DEVELOPMENT_DATABASE_URL.replace("winddesk_local", "test-example-password"),
        allowed_hosts=["testserver"],
    )
    with TestClient(create_app(Settings(**valid))) as client:
        assert client.get("/api/docs").status_code == 404
        assert client.get("/api/openapi.json").status_code == 404
    for override in (
        {"allowed_hosts": ["*"]},
        {"allowed_hosts": []},
        {"database_url": DEVELOPMENT_DATABASE_URL},
        {"api_rate_limit_enabled": False},
        {"trusted_proxy_ips": ["*"]},
        {"trusted_proxy_ips": ["0.0.0.0/0"]},
        {"database_url": "postgresql+psycopg://reader:test-example-password@db.example/winddesk"},
    ):
        with pytest.raises(ValidationError):
            Settings(**(valid | override))
    missing_hosts = valid.copy()
    missing_hosts.pop("allowed_hosts")
    with pytest.raises(ValidationError):
        Settings(**missing_hosts)


def test_vercel_preview_hostnames_are_exact_and_forwarded_hosts_are_not_trusted(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_URL", "preview-0123.example.vercel.app")
    monkeypatch.setenv("VERCEL_BRANCH_URL", "branch-example.vercel.app")
    monkeypatch.setenv("VERCEL_PROJECT_PRODUCTION_URL", "project-example.vercel.app")
    settings = Settings(
        _env_file=None,
        environment="production",
        frontend_dist=tmp_path,
        database_url=DEVELOPMENT_DATABASE_URL.replace("winddesk_local", "test-example-password"),
        allowed_hosts=["project-example.vercel.app"],
    )
    assert settings.allowed_hosts == [
        "project-example.vercel.app",
        "preview-0123.example.vercel.app",
        "branch-example.vercel.app",
    ]
    with TestClient(
        create_app(settings), base_url="https://preview-0123.example.vercel.app"
    ) as client:
        assert client.get("/health/live").status_code == 200
        rejected = client.get(
            "/health/live",
            headers={"Host": "attacker.invalid", "X-Forwarded-Host": "project-example.vercel.app"},
        )
        assert rejected.status_code == 400 and rejected.json()["code"] == "INVALID_HOST"
    monkeypatch.setenv("VERCEL", "0")
    local = Settings(_env_file=None)
    assert "preview-0123.example.vercel.app" not in local.allowed_hosts


def test_vercel_environment_cannot_enable_wildcard_hosts(monkeypatch):
    from pydantic import ValidationError

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("VERCEL_URL", "*.vercel.app")
    with pytest.raises(ValidationError, match="Allowed hosts"):
        Settings(
            _env_file=None,
            environment="production",
            database_url=DEVELOPMENT_DATABASE_URL.replace(
                "winddesk_local", "test-example-password"
            ),
            allowed_hosts=["project-example.vercel.app"],
        )


@pytest.mark.parametrize("first_path", ["/api/v1/config", "/health/ready"])
def test_overload_rejects_work_and_releases_capacity(tmp_path, first_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release = Event(), Event()
    app = create_app(Settings(_env_file=None, frontend_dist=tmp_path, api_max_inflight=1))

    def blocked():
        entered.set()
        assert release.wait(5)
        return DatasetState(True, True)

    app.dependency_overrides[get_dataset_state] = blocked
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(client.get, first_path)
        try:
            assert entered.wait(5)
            response = client.get("/api/v1/config")
            assert response.status_code == 503 and response.json()["code"] == "SERVER_BUSY"
            assert response.headers["retry-after"] == "1"
            assert client.get("/health/live").status_code == 200
        finally:
            release.set()
        completed = first.result(timeout=5)
        assert completed.status_code == (503 if first_path == "/health/ready" else 200)
        if first_path == "/health/ready":
            assert completed.json()["code"] == "NO_ACCEPTED_DATASET"
        assert client.get("/api/v1/config").status_code == 200
