"""Tests for graph schema metadata."""

import json

import pytest

from graph_aml.graph import (
    GRAPH_NODE_KEY_PROPERTIES,
    GRAPH_NODE_LABELS,
    GRAPH_RELATIONSHIP_TYPES,
    GraphNodeSpec,
    GraphRelationshipSpec,
    GraphSchemaError,
    get_graph_node_specs,
    get_graph_relationship_specs,
    get_graph_schema_summary,
    validate_graph_node_spec,
    validate_graph_relationship_spec,
    validate_graph_schema,
)


def test_graph_node_labels_include_core_labels() -> None:
    assert {"Customer", "Account", "Transaction", "Counterparty", "Country", "Alert"} <= set(
        GRAPH_NODE_LABELS
    )


def test_graph_relationship_types_include_core_relationships() -> None:
    assert {
        "OWNS",
        "SENT",
        "RECEIVED",
        "PAID_TO",
        "LOCATED_IN",
        "TRIGGERS",
        "FLAGS_ACCOUNT",
        "INVOLVES_TRANSACTION",
    } <= set(GRAPH_RELATIONSHIP_TYPES)


def test_node_key_properties_are_defined_for_every_label() -> None:
    assert set(GRAPH_NODE_LABELS) == set(GRAPH_NODE_KEY_PROPERTIES)


def test_node_specs_are_valid() -> None:
    for spec in get_graph_node_specs().values():
        validate_graph_node_spec(spec)


def test_relationship_specs_are_valid() -> None:
    for spec in get_graph_relationship_specs().values():
        validate_graph_relationship_spec(spec)


def test_schema_summary_is_json_serialisable() -> None:
    json.dumps(get_graph_schema_summary())


def test_invalid_node_specs_raise_graph_schema_error() -> None:
    spec = GraphNodeSpec("Bad Label", "id", ("id",))

    with pytest.raises(GraphSchemaError):
        validate_graph_node_spec(spec)


def test_invalid_relationship_specs_raise_graph_schema_error() -> None:
    spec = GraphRelationshipSpec("BAD-TYPE", "Customer", "customer_id", "Account", "account_id")

    with pytest.raises(GraphSchemaError):
        validate_graph_relationship_spec(spec)


def test_full_graph_schema_validation_passes() -> None:
    validate_graph_schema()
