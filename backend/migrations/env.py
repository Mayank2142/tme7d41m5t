"""Alembic uses the operator-provided connection; no credential-bearing ini file."""

from alembic import context

from backend.app.persistence.models import Base

connection = context.config.attributes["connection"]
context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
with context.begin_transaction():
    context.run_migrations()
