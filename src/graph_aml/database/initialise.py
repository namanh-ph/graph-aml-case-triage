"""Database initialisation helpers for schema and table SQL artefacts."""

from sqlalchemy import Engine

from graph_aml.database.exceptions import DatabaseInitialisationError
from graph_aml.database.execution import execute_sql
from graph_aml.database.schemas import read_create_schemas_sql
from graph_aml.database.tables import read_create_tables_sql


def create_database_schemas(engine: Engine) -> int:
    """Execute idempotent schema creation SQL."""

    return execute_sql(engine, read_create_schemas_sql())


def create_core_tables(engine: Engine) -> int:
    """Execute idempotent core table creation SQL."""

    return execute_sql(engine, read_create_tables_sql())


def initialise_database(engine: Engine) -> dict[str, int]:
    """Initialise PostgreSQL schemas and core tables in dependency order."""

    try:
        schema_count = create_database_schemas(engine)
        table_count = create_core_tables(engine)
    except Exception as exc:
        raise DatabaseInitialisationError(f"Database initialisation failed: {exc}") from exc

    return {
        "schema_statements_executed": schema_count,
        "table_statements_executed": table_count,
    }
