"""TLS trust portability and credential-free connection diagnostics."""

from pathlib import Path

import certifi
import pytest
from sqlalchemy.exc import OperationalError

from backend.app.config import Settings
from backend.app.persistence.database import create_database_engine, report_database_failure


@pytest.mark.parametrize("root", ["system", "/operator-provided-ca.pem"])
def test_verified_database_tls_preserves_verification_and_explicit_roots(root):
    engine = create_database_engine(
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://reader:test-example-password@db.example/db"
            f"?sslmode=verify-full&sslrootcert={root}",
        ),
        read_only=True,
    )
    try:
        assert engine.url.query["sslmode"] == "verify-full"
        assert engine.url.query["sslrootcert"] == (certifi.where() if root == "system" else root)
        assert Path(certifi.where()).is_file()
    finally:
        engine.dispose()


def test_database_diagnostic_does_not_log_exception_sql_or_credentials(caplog):
    error = OperationalError(
        "private SQL", {}, Exception("certificate verify failed private-password")
    )
    report_database_failure(error)
    assert "TLS_TRUST" in caplog.text
    assert "private SQL" not in caplog.text and "private-password" not in caplog.text
