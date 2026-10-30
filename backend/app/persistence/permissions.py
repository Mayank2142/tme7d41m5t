"""Operator-only provisioning of a separate, narrowly privileged web login."""

import re

from psycopg import sql
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url

READ_TABLES = (
    "dataset_release",
    "active_release",
    "forecast_version",
    "actual_version",
    "release_forecast_member",
    "release_actual_member",
    "release_batch_member",
)


def configure_reader(engine: Engine, reader_url: str) -> None:
    target = make_url(reader_url)
    operator = engine.url
    name = target.username or ""
    if (
        target.drivername != "postgresql+psycopg"
        or (target.host, target.port, target.database)
        != (operator.host, operator.port, operator.database)
        or name == operator.username
        or not re.fullmatch(r"[a-z][a-z0-9_]{2,62}", name)
        or not target.password
    ):
        raise ValueError("Reader URL must use a separate login in the same PostgreSQL database")
    role = sql.Identifier(name)
    with engine.begin() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
        existing = connection.execute(
            text(
                "SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls "
                "OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member = pg_roles.oid) "
                "OR EXISTS (SELECT 1 FROM pg_class WHERE relowner = pg_roles.oid) "
                "OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspowner = pg_roles.oid) "
                "FROM pg_roles WHERE rolname = :name"
            ),
            {"name": name},
        ).scalar()
        if existing:
            raise ValueError("Refusing to reuse a privileged or object-owning reader role")
        cursor = connection.connection.driver_connection.cursor()
        try:
            # psycopg quotes identifiers/passwords; no credential is logged or printed.
            action = "ALTER" if existing is not None else "CREATE"
            cursor.execute(
                sql.SQL(
                    action + " ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT "
                    "NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 20 PASSWORD {}"
                ).format(role, sql.Literal(target.password))
            )
            cursor.execute(
                sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM {}").format(
                    sql.Identifier(schema), role
                )
            )
            cursor.execute(
                sql.SQL("REVOKE ALL ON SCHEMA {} FROM {}").format(sql.Identifier(schema), role)
            )
            cursor.execute(
                sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(schema), role)
            )
            for table in READ_TABLES:
                cursor.execute(
                    sql.SQL("GRANT SELECT ON {}.{} TO {}").format(
                        sql.Identifier(schema), sql.Identifier(table), role
                    )
                )
            cursor.execute(
                sql.SQL(
                    "GRANT SELECT (id, dataset, source_url, payload_sha256, received_at) "
                    "ON {}.raw_batch TO {}"
                ).format(sql.Identifier(schema), role)
            )
            cursor.execute(
                sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(role)
            )
            cursor.execute(sql.SQL("ALTER ROLE {} SET statement_timeout = '5s'").format(role))
            cursor.execute(sql.SQL("ALTER ROLE {} SET lock_timeout = '1s'").format(role))
        finally:
            cursor.close()
        if connection.scalar(
            text("SELECT has_schema_privilege(:role, :schema, 'CREATE')"),
            {"role": name, "schema": schema},
        ):
            raise ValueError(
                "Reader inherits schema CREATE permission; remove that public grant first"
            )
