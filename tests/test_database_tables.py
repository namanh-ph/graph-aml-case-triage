"""Tests for PostgreSQL table metadata and SQL helpers."""

from pathlib import Path
from types import ModuleType

import yaml

from graph_aml.database import tables
from graph_aml.database.schemas import POSTGRES_SCHEMAS
from graph_aml.database.tables import (
    AML_TABLES,
    GOVERNANCE_TABLES,
    MART_TABLES,
    POSTGRES_TABLES_BY_SCHEMA,
    RAW_TABLES,
    STAGING_TABLES,
    get_all_table_names,
    get_qualified_table_names,
    get_table_descriptions,
    get_table_sql_dir,
    get_tables_for_schema,
    read_create_tables_sql,
    read_drop_tables_sql,
    validate_table_name,
)

ROOT = Path(__file__).resolve().parents[1]


def test_table_groups_contain_expected_table_names() -> None:
    assert RAW_TABLES == (
        "customers_raw",
        "accounts_raw",
        "transactions_raw",
        "counterparties_raw",
        "countries_raw",
        "devices_raw",
    )
    assert STAGING_TABLES == (
        "countries",
        "customers",
        "accounts",
        "counterparties",
        "devices",
        "transactions",
    )
    assert MART_TABLES == (
        "features_account_daily",
        "graph_features",
        "account_anomaly_scores",
        "account_risk_scores",
    )
    assert AML_TABLES == (
        "alerts",
        "cases",
        "case_alerts",
        "case_entities",
        "case_risk_scores",
        "case_evidence_packs",
        "case_explanations",
        "case_lifecycle_events",
        "case_assignments",
    )
    assert GOVERNANCE_TABLES == ("audit_events", "model_runs", "validation_reports")


def test_postgres_tables_by_schema_contains_expected_schemas() -> None:
    assert tuple(POSTGRES_TABLES_BY_SCHEMA) == POSTGRES_SCHEMAS


def test_get_tables_for_schema_returns_expected_tables() -> None:
    for schema_name, table_names in POSTGRES_TABLES_BY_SCHEMA.items():
        assert get_tables_for_schema(schema_name) == table_names


def test_get_all_table_names_returns_all_unqualified_names() -> None:
    table_names = get_all_table_names()

    assert len(table_names) == 28
    assert "raw.transactions_raw" not in table_names
    assert set(table_names) == {
        table_name
        for table_group in POSTGRES_TABLES_BY_SCHEMA.values()
        for table_name in table_group
    }


def test_get_qualified_table_names_returns_schema_prefixed_names() -> None:
    qualified_names = get_qualified_table_names()

    assert len(qualified_names) == 28
    assert "raw.transactions_raw" in qualified_names
    assert "governance.validation_reports" in qualified_names


def test_get_table_descriptions_contains_all_qualified_names() -> None:
    descriptions = get_table_descriptions()

    assert set(get_qualified_table_names()) == set(descriptions)
    assert descriptions is not tables.TABLE_DESCRIPTIONS


def test_validate_table_name_accepts_canonical_tables() -> None:
    for schema_name, table_names in POSTGRES_TABLES_BY_SCHEMA.items():
        for table_name in table_names:
            assert validate_table_name(schema_name, table_name)


def test_validate_table_name_rejects_invalid_schema_or_table() -> None:
    assert not validate_table_name("public", "transactions")
    assert not validate_table_name("raw", "transactions")
    assert not validate_table_name("staging", "transactions_raw")


def test_get_table_sql_dir_points_to_existing_directory() -> None:
    assert get_table_sql_dir().is_dir()


def test_read_create_tables_sql_contains_create_table_statements() -> None:
    sql = read_create_tables_sql()

    assert "CREATE TABLE IF NOT EXISTS" in sql


def test_read_drop_tables_sql_contains_drop_table_statements() -> None:
    sql = read_drop_tables_sql()

    assert "DROP TABLE IF EXISTS" in sql


def test_database_yaml_table_names_match_constants() -> None:
    database_config = yaml.safe_load((ROOT / "config" / "database.yaml").read_text())

    for schema_name, expected_tables in POSTGRES_TABLES_BY_SCHEMA.items():
        configured_tables = set(database_config["tables"][schema_name].values())
        assert configured_tables == set(expected_tables)


def test_table_module_does_not_import_database_connection_libraries() -> None:
    assert isinstance(tables, ModuleType)
    assert "sqlalchemy" not in tables.__dict__
    assert "psycopg2" not in tables.__dict__
