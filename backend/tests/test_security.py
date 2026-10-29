"""Public request backstops, cache safety, and source-file containment."""

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
        assert "cdn.jsdelivr.net" in client.get("/api/docs").headers["content-security-policy"]


def test_hsts_is_limited_to_production_https(tmp_path):
    settings = Settings(
        _env_file=None,
        environment="production",
        frontend_dist=tmp_path,
        database_url=DEVELOPMENT_DATABASE_URL.replace("127.0.0.1", "localhost"),
    )
    with TestClient(create_app(settings), base_url="https://example.test") as client:
        assert client.get("/health/live").headers["strict-transport-security"] == "max-age=31536000"
    with TestClient(create_app(settings)) as client:
        assert "strict-transport-security" not in client.get("/health/live").headers
