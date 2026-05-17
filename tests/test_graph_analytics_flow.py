"""Tests for graph analytics flow features."""

import networkx as nx

from graph_aml.graph import compute_flow_features


def test_flow_features_compute_counts_and_amounts() -> None:
    graph = nx.DiGraph()
    graph.add_node("A1", node_type="Account")
    graph.add_node("A2", node_type="Account")
    graph.add_node("CP1", node_type="Counterparty")
    graph.add_edge("A2", "A1", amount=40.0, transaction_id="T0", target_node_type="Account")
    graph.add_edge("A1", "A2", amount=100.0, transaction_ids=["T1"], target_node_type="Account")
    graph.add_edge(
        "A1",
        "CP1",
        amount=25.0,
        transaction_ids=["T2"],
        target_node_type="Counterparty",
    )

    frame = compute_flow_features(graph, ["A1", "A3"])
    by_account = frame.set_index("account_id")

    assert by_account.loc["A1", "fan_in_count"] == 1
    assert by_account.loc["A1", "fan_out_count"] == 2
    assert by_account.loc["A1", "neighbour_account_count"] == 1
    assert by_account.loc["A1", "counterparty_count"] == 1
    assert by_account.loc["A1", "transaction_count"] == 3
    assert by_account.loc["A1", "total_sent_amount"] == 125.0
    assert by_account.loc["A1", "total_received_amount"] == 40.0
    assert by_account.loc["A3", "fan_in_count"] == 0


def test_empty_flow_graph_returns_zero_values() -> None:
    frame = compute_flow_features(nx.DiGraph(), ["A1"])

    assert frame.loc[0, "fan_out_count"] == 0
