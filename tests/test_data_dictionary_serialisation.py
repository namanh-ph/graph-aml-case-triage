"""Tests for data dictionary serialisation helpers."""

import json

from graph_aml.documentation import (
    build_data_dictionary,
    data_dictionary_to_dataframe,
    data_dictionary_to_dict,
)


def test_data_dictionary_to_dict_returns_json_serialisable_dictionary() -> None:
    payload = data_dictionary_to_dict(build_data_dictionary())

    json.dumps(payload, default=str)


def test_dictionary_output_includes_project_timestamp_version_and_tables() -> None:
    payload = data_dictionary_to_dict(build_data_dictionary())

    assert payload["project_name"]
    assert payload["generated_at"]
    assert payload["version"]
    assert payload["tables"]


def test_data_dictionary_to_dataframe_returns_non_empty_dataframe() -> None:
    frame = data_dictionary_to_dataframe(build_data_dictionary())

    assert not frame.empty


def test_dataframe_output_has_one_row_per_column() -> None:
    dictionary = build_data_dictionary()
    frame = data_dictionary_to_dataframe(dictionary)

    assert len(frame) == sum(len(table.columns) for table in dictionary.tables)


def test_dataframe_output_includes_required_columns() -> None:
    frame = data_dictionary_to_dataframe(build_data_dictionary())

    assert {
        "schema_name",
        "table_name",
        "qualified_name",
        "column_name",
        "data_type",
        "nullable",
        "primary_key",
        "foreign_key",
        "description",
        "business_meaning",
        "validation_rules",
        "example_value",
        "lineage_source",
        "lifecycle_stage",
    }.issubset(frame.columns)


def test_validation_rules_are_represented_consistently() -> None:
    frame = data_dictionary_to_dataframe(build_data_dictionary())

    assert frame["validation_rules"].map(lambda value: isinstance(value, str)).all()


def test_dataframe_includes_all_schema_names() -> None:
    frame = data_dictionary_to_dataframe(build_data_dictionary())

    assert set(frame["schema_name"]) == {"raw", "staging", "mart", "aml", "governance"}
