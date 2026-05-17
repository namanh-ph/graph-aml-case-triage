"""Tests for Neo4j graph projection query builders."""

import pytest

from graph_aml.graph import (
    GraphProjectionError,
    build_graph_projection_node_query,
    build_graph_projection_relationship_query,
)


def test_node_query_returns_node_identity_payload() -> None:
    query = build_graph_projection_node_query()

    assert "id:" in query
    assert "labels:" in query
    assert "properties:" in query
    assert "Account" in query


def test_node_query_respects_include_flags() -> None:
    query = build_graph_projection_node_query(
        include_counterparties=False,
        include_alert_nodes=False,
        include_transaction_nodes=False,
    )

    assert "Counterparty" not in query
    assert "Alert" not in query
    assert "Transaction" not in query


def test_relationship_query_filters_configured_types() -> None:
    query = build_graph_projection_relationship_query(("SENT", "RECEIVED"))

    assert "type(r) IN ['SENT', 'RECEIVED']" in query
    assert "source_id:" in query
    assert "target_id:" in query


def test_invalid_relationship_type_raises_projection_error() -> None:
    with pytest.raises(GraphProjectionError):
        build_graph_projection_relationship_query(("SENT;MATCH",))


def test_projection_query_generation_is_deterministic() -> None:
    assert build_graph_projection_node_query() == build_graph_projection_node_query()
    assert build_graph_projection_relationship_query(("SENT",)) == (
        build_graph_projection_relationship_query(("SENT",))
    )
