"""Explicit destructive database reset helpers."""

from sqlalchemy import Engine

from graph_aml.database.exceptions import DatabaseResetRefusedError
from graph_aml.database.execution import execute_sql
from graph_aml.database.schemas import read_create_schemas_sql, read_drop_schemas_sql
from graph_aml.database.tables import read_create_tables_sql, read_drop_tables_sql


def _require_confirmation(confirm: bool) -> None:
    if not confirm:
        raise DatabaseResetRefusedError(
            "Database reset refused. Pass confirm=True for destructive operations."
        )


def drop_core_tables(engine: Engine, confirm: bool = False) -> int:
    """Drop all core project tables using the explicit drop-table SQL artefact."""

    _require_confirmation(confirm)
    return execute_sql(engine, read_drop_tables_sql())


def drop_database_schemas(engine: Engine, confirm: bool = False) -> int:
    """Drop all project schemas using the explicit drop-schema SQL artefact."""

    _require_confirmation(confirm)
    return execute_sql(engine, read_drop_schemas_sql())


def reset_database(engine: Engine, confirm: bool = False) -> dict[str, int]:
    """Drop and recreate project schemas and core tables in dependency-safe order."""

    _require_confirmation(confirm)
    drop_table_count = drop_core_tables(engine, confirm=True)
    drop_schema_count = drop_database_schemas(engine, confirm=True)
    create_schema_count = execute_sql(engine, read_create_schemas_sql())
    create_table_count = execute_sql(engine, read_create_tables_sql())

    return {
        "drop_table_statements_executed": drop_table_count,
        "drop_schema_statements_executed": drop_schema_count,
        "create_schema_statements_executed": create_schema_count,
        "create_table_statements_executed": create_table_count,
    }
