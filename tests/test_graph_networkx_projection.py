"""Tests for NetworkX graph projection helpers."""

import networkx as nx
import pytest

from graph_aml.graph import (
    GraphProjectionError,
    ProjectedGraphData,
    build_account_flow_graph,
    build_networkx_graph,
)


def _projected() -> ProjectedGraphData:
    return ProjectedGraphData(
        nodes=[
            {"id": "A1", "labels": ["Account"], "properties": {"status": "open"}},
            {"id": "A2", "labels": ["Account"], "properties": {}},
            {"id": "CP1", "labels": ["Counterparty"], "properties": {}},
            {"id": "T1", "labels": ["Transaction"], "properties": {"amount": 100.0}},
            {"id": "T2", "labels": ["Transaction"], "properties": {"amount": 25.0}},
        ],
        relationships=[
            {"source_id": "A1", "target_id": "T1", "type": "SENT", "properties": {}},
            {"source_id": "T1", "target_id": "A2", "type": "RECEIVED", "properties": {}},
            {"source_id": "A1", "target_id": "T2", "type": "SENT", "properties": {}},
            {"source_id": "T2", "target_id": "CP1", "type": "PAID_TO", "properties": {}},
        ],
        account_ids=("A1", "A2"),
    )


def test_build_networkx_graph_preserves_attributes() -> None:
    graph = build_networkx_graph(_projected())

    assert isinstance(graph, nx.DiGraph)
    assert graph.nodes["A1"]["node_type"] == "Account"
    assert graph.nodes["A1"]["status"] == "open"
    assert graph["A1"]["T1"]["relationship_type"] == "SENT"


def test_build_networkx_graph_can_return_undirected_graph() -> None:
    graph = build_networkx_graph(_projected(), directed=False)

    assert not graph.is_directed()


def test_empty_projected_data_returns_empty_graph() -> None:
    assert build_networkx_graph(ProjectedGraphData()).number_of_nodes() == 0


def test_build_account_flow_graph_collapses_transaction_paths() -> None:
    graph = build_account_flow_graph(_projected())

    assert graph.has_edge("A1", "A2")
    assert graph["A1"]["A2"]["transaction_id"] == "T1"
    assert graph["A1"]["A2"]["amount"] == 100.0
    assert graph.has_edge("A1", "CP1")


def test_malformed_projected_data_raises() -> None:
    projected = ProjectedGraphData(nodes=[{"id": "A1", "labels": object(), "properties": {}}])

    with pytest.raises(GraphProjectionError):
        build_networkx_graph(projected)
