"""Important foundation boundaries; no live external database is needed for these tests."""

from datetime import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.api.dataset import get_dataset_state
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.persistence.releases import DatasetState


@pytest.fixture
def app(tmp_path):
    application = create_app(
        Settings(_env_file=None, environment="test", frontend_dist=tmp_path / "dist")
    )
    application.dependency_overrides[get_dataset_state] = lambda: DatasetState(True, True)
    return application


def test_public_config_exposes_policy_but_no_credentials(app):
    with TestClient(app) as client:
        response = client.get("/api/v1/config")
    assert response.status_code == 200
    result = response.json()
    assert result["policy"]["decision_from"] == "2026-01-01"
    assert result["policy"]["delivery_to"] == "2026-02-01"
    assert result["policy"]["comparison_policy"] == "source_timestamp_v1"
    assert result["dataset"]["status"] == "not_initialized"
    assert result["dataset"]["release_id"] is None
    assert "database_url" not in result
    assert "winddesk_local" not in response.text
    assert response.headers["x-request-id"]


def test_liveness_does_not_require_database_or_dataset(app):
    def forbidden_probe():
        raise AssertionError("Liveness must not query PostgreSQL")

    app.dependency_overrides[get_dataset_state] = forbidden_probe
    with TestClient(app) as client:
        assert client.get("/health/live").json()["status"] == "ok"


@pytest.mark.parametrize(
    ("available", "code"), [(False, "DATABASE_UNAVAILABLE"), (True, "NO_ACCEPTED_DATASET")]
)
def test_readiness_does_not_claim_data_is_ready(app, available, code):
    app.dependency_overrides[get_dataset_state] = lambda: DatasetState(available, True)
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["code"] == code


def test_unknown_api_route_is_json_even_when_frontend_is_built(app, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>frontend</html>", encoding="utf-8")
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        missing = client.get("/api/v1/unknown")
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("cutoff", [time(9, 0, 1), "09:00+01:00"])
def test_invalid_cutoff_is_rejected(cutoff):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, default_cutoff_local=cutoff)


def test_non_postgres_database_and_production_default_are_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite:///local.db")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")
