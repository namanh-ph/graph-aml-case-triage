"""Database health check helpers."""

from sqlalchemy import Engine, text

from graph_aml.database.exceptions import DatabaseConnectionError


def check_database_connection(engine: Engine) -> bool:
    """Return True when the database responds to SELECT 1."""

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return bool(result.scalar_one() == 1)
    except Exception as exc:
        raise DatabaseConnectionError(f"Database connection check failed: {exc}") from exc


def get_database_server_version(engine: Engine) -> str:
    """Return PostgreSQL server version text."""

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            return str(result.scalar_one())
    except Exception as exc:
        raise DatabaseConnectionError(f"Could not read database server version: {exc}") from exc


def get_existing_schemas(engine: Engine) -> tuple[str, ...]:
    """Return existing database schemas sorted by name."""

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT schema_name FROM information_schema.schemata"))
            return tuple(sorted(str(row[0]) for row in result))
    except Exception as exc:
        raise DatabaseConnectionError(f"Could not list database schemas: {exc}") from exc


def get_existing_tables(engine: Engine, schema_name: str) -> tuple[str, ...]:
    """Return existing base tables in one schema sorted by name."""

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = :schema_name
                      AND table_type = 'BASE TABLE'
                    """
                ),
                {"schema_name": schema_name},
            )
            return tuple(sorted(str(row[0]) for row in result))
    except Exception as exc:
        raise DatabaseConnectionError(
            f"Could not list database tables for schema {schema_name}: {exc}"
        ) from exc
