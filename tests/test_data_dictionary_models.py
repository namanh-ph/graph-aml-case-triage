"""Tests for data dictionary models and catalogue construction."""

from graph_aml.database.tables import get_qualified_table_names
from graph_aml.documentation.data_dictionary import (
    LIFECYCLE_STAGE_BY_SCHEMA,
    ColumnDefinition,
    DataDictionary,
    TableDefinition,
    build_data_dictionary,
)


def test_column_definition_stores_expected_fields() -> None:
    column = ColumnDefinition(
        column_name="transaction_id",
        data_type="TEXT",
        nullable=False,
        primary_key=True,
        description="Transaction identifier.",
    )

    assert column.column_name == "transaction_id"
    assert column.primary_key is True


def test_table_definition_stores_expected_fields() -> None:
    table = TableDefinition(
        schema_name="staging",
        table_name="transactions",
        qualified_name="staging.transactions",
        description="Transactions.",
        lifecycle_stage="Cleaned",
        primary_key=("transaction_id",),
    )

    assert table.qualified_name == "staging.transactions"
    assert table.primary_key == ("transaction_id",)


def test_data_dictionary_stores_expected_fields() -> None:
    dictionary = DataDictionary(
        project_name="graph-aml-case-triage",
        generated_at="2025-01-01T00:00:00+00:00",
        version="1.0",
        tables=(),
    )

    assert dictionary.project_name == "graph-aml-case-triage"
    assert dictionary.version == "1.0"


def test_build_data_dictionary_returns_data_dictionary() -> None:
    assert isinstance(build_data_dictionary(), DataDictionary)


def test_every_database_table_appears_in_data_dictionary() -> None:
    dictionary = build_data_dictionary()

    assert {table.qualified_name for table in dictionary.tables} == set(get_qualified_table_names())


def test_every_table_definition_has_at_least_one_column() -> None:
    dictionary = build_data_dictionary()

    assert all(table.columns for table in dictionary.tables)


def test_every_column_has_name_and_data_type() -> None:
    dictionary = build_data_dictionary()

    assert all(
        column.column_name and column.data_type
        for table in dictionary.tables
        for column in table.columns
    )


def test_schema_lifecycle_stages_cover_project_schemas() -> None:
    assert set(LIFECYCLE_STAGE_BY_SCHEMA) == {"raw", "staging", "mart", "aml", "governance"}


def test_table_descriptions_are_populated() -> None:
    dictionary = build_data_dictionary()

    assert all(table.description for table in dictionary.tables)
