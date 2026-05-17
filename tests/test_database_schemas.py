"""Tests for PostgreSQL schema constants and SQL helpers."""

from pathlib import Path
from types import ModuleType

import yaml

from graph_aml.database import schemas
from graph_aml.database.schemas import (
    POSTGRES_SCHEMAS,
    get_postgres_schemas,
    get_schema_descriptions,
    get_schema_sql_dir,
    read_create_schemas_sql,
    read_drop_schemas_sql,
    validate_schema_name,
)

ROOT = Path(__file__).resolve().parents[1]


def test_postgres_schemas_are_canonical_tuple() -> None:
    assert POSTGRES_SCHEMAS == ("raw", "staging", "mart", "aml", "governance")


def test_get_postgres_schemas_returns_canonical_tuple() -> None:
    assert get_postgres_schemas() == POSTGRES_SCHEMAS


def test_get_schema_descriptions_contains_all_schema_names() -> None:
    descriptions = get_schema_descriptions()

    assert set(POSTGRES_SCHEMAS) <= set(descriptions)
    assert descriptions is not schemas.SCHEMA_DESCRIPTIONS


def test_validate_schema_name_accepts_canonical_schemas() -> None:
    for schema_name in POSTGRES_SCHEMAS:
        assert validate_schema_name(schema_name)


def test_validate_schema_name_rejects_invalid_names() -> None:
    assert not validate_schema_name("public")
    assert not validate_schema_name("raw_data")
    assert not validate_schema_name("")


def test_get_schema_sql_dir_points_to_existing_directory() -> None:
    assert get_schema_sql_dir().is_dir()


def test_read_create_schemas_sql_contains_all_schema_creates() -> None:
    sql = read_create_schemas_sql()

    for schema_name in POSTGRES_SCHEMAS:
        assert f"CREATE SCHEMA IF NOT EXISTS {schema_name};" in sql


def test_read_drop_schemas_sql_contains_all_schema_drops() -> None:
    sql = read_drop_schemas_sql()

    for schema_name in POSTGRES_SCHEMAS:
        assert f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;" in sql


def test_create_sql_contains_schema_comments() -> None:
    sql = read_create_schemas_sql()

    for schema_name in POSTGRES_SCHEMAS:
        assert f"COMMENT ON SCHEMA {schema_name}" in sql


def test_drop_sql_contains_cascade_and_destructive_warning() -> None:
    sql = read_drop_schemas_sql()

    assert "CASCADE" in sql
    assert "DESTRUCTIVE RESET SCRIPT" in sql
    assert "deletes all objects" in sql


def test_database_yaml_schema_names_match_constants() -> None:
    database_config = yaml.safe_load((ROOT / "config" / "database.yaml").read_text())
    configured_schemas = tuple(database_config["schemas"].values())

    assert configured_schemas == POSTGRES_SCHEMAS


def test_create_sql_does_not_create_tables() -> None:
    sql = read_create_schemas_sql().upper()

    assert "CREATE TABLE" not in sql


def test_schema_module_does_not_import_database_connection_libraries() -> None:
    assert isinstance(schemas, ModuleType)
    assert "sqlalchemy" not in schemas.__dict__
    assert "psycopg2" not in schemas.__dict__
