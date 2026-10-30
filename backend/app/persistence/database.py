"""A bounded, lazy PostgreSQL connection pool."""

import logging

import certifi
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from backend.app.config import Settings


def create_database_engine(settings: Settings, *, read_only: bool = False) -> Engine:
    database_url = make_url(settings.database_url.get_secret_value())
    if database_url.query.get("sslrootcert") == "system":
        # libpq wheels and serverless base images can disagree on the system
        # certificate location. Use the shipped Mozilla roots without weakening
        # sslmode or overriding an explicitly supplied private CA bundle.
        database_url = database_url.update_query_dict({"sslrootcert": certifi.where()})
    options = "-c timezone=UTC"
    if read_only:
        options += (
            " -c default_transaction_read_only=on -c statement_timeout=5000"
            " -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000"
        )
    return create_engine(
        database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=5,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3, "options": options},
        hide_parameters=True,
    )


def report_database_failure(exc: SQLAlchemyError) -> None:
    """Report a bounded category, never exception text, SQL, host or credentials."""
    underlying = getattr(exc, "orig", exc)
    message = str(underlying).lower()
    category = next(
        (
            category
            for tokens, category in (
                (("certificate", "sslrootcert"), "TLS_TRUST"),
                (("authentication failed",), "AUTHENTICATION"),
                (("unsupported startup parameter",), "STARTUP_PARAMETERS"),
                (("timeout", "timed out"), "TIMEOUT"),
                (("could not translate host", "name or service not known"), "DNS"),
            )
            if any(token in message for token in tokens)
        ),
        "DATABASE_CONNECTION",
    )
    logging.getLogger("winddesk.database").warning(
        "Stored dataset unavailable: category=%s", category
    )


def database_available(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
