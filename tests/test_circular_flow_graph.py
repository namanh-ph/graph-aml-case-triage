"""Tests for circular flow NetworkX graph construction."""

import networkx as nx
import pandas as pd

from graph_aml.rules import (
    CIRCULAR_FLOW_EDGE_COLUMNS,
    build_circular_flow_edges,
    build_circular_flow_graph,
)
from tests.fixtures.circular_flow_fixtures import (
    build_circular_flow_two_hop_transactions_fixture,
)


def test_build_circular_flow_graph_returns_multidigraph() -> None:
    edges = build_circular_flow_edges(build_circular_flow_two_hop_transactions_fixture())

    graph = build_circular_flow_graph(edges)

    assert isinstance(graph, nx.MultiDiGraph)


def test_empty_edge_input_returns_empty_graph() -> None:
    edges = pd.DataFrame(columns=CIRCULAR_FLOW_EDGE_COLUMNS)

    graph = build_circular_flow_graph(edges)

    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0


def test_graph_contains_expected_nodes_and_directed_edges() -> None:
    edges = build_circular_flow_edges(build_circular_flow_two_hop_transactions_fixture())

    graph = build_circular_flow_graph(edges)

    assert {"ACC_CF_A", "ACC_CF_B"} <= set(graph.nodes)
    assert graph.has_edge("ACC_CF_A", "ACC_CF_B")
    assert graph.has_edge("ACC_CF_B", "ACC_CF_A")


def test_graph_preserves_multiple_transactions_between_same_accounts() -> None:
    transactions = build_circular_flow_two_hop_transactions_fixture()
    duplicate = transactions.iloc[[0]].copy()
    duplicate.loc[:, "transaction_id"] = "TXN_CF_PARALLEL"
    transactions = pd.concat([transactions, duplicate], ignore_index=True)
    edges = build_circular_flow_edges(transactions)

    graph = build_circular_flow_graph(edges)

    assert graph.number_of_edges("ACC_CF_A", "ACC_CF_B") == 2


def test_graph_edge_attributes_include_transaction_metadata() -> None:
    edges = build_circular_flow_edges(build_circular_flow_two_hop_transactions_fixture())

    graph = build_circular_flow_graph(edges)
    attributes = next(iter(graph.get_edge_data("ACC_CF_A", "ACC_CF_B").values()))

    assert attributes["transaction_id"] == "TXN_CF_2HOP_001"
    assert "transaction_timestamp" in attributes
    assert attributes["amount"] == 5000.0
    assert attributes["transaction_type"] == "transfer"
    assert "counterparty_id" in attributes


def test_graph_construction_is_deterministic_for_same_edge_input() -> None:
    edges = build_circular_flow_edges(build_circular_flow_two_hop_transactions_fixture())

    first = build_circular_flow_graph(edges)
    second = build_circular_flow_graph(edges)

    assert sorted(first.edges(keys=True)) == sorted(second.edges(keys=True))
