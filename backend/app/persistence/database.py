"""A bounded, lazy PostgreSQL connection pool."""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.config import Settings


def create_database_engine(settings: Settings, *, read_only: bool = False) -> Engine:
    options = "-c timezone=UTC"
    if read_only:
        options += (
            " -c default_transaction_read_only=on -c statement_timeout=5000"
            " -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000"
        )
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=5,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3, "options": options},
        hide_parameters=True,
    )


def database_available(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
