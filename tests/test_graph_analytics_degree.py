"""Tests for graph analytics degree features."""

import networkx as nx

from graph_aml.graph import (
    GRAPH_ANALYTICS_FEATURE_COLUMNS,
    compute_degree_features,
    initialise_account_feature_frame,
)


def test_feature_initialisation_returns_expected_columns_and_order() -> None:
    frame = initialise_account_feature_frame(["A2", "A1", "A1"])

    assert list(frame["account_id"]) == ["A1", "A2"]
    assert tuple(frame.columns) == GRAPH_ANALYTICS_FEATURE_COLUMNS
    assert frame.loc[0, "degree"] == 0
    assert frame.loc[0, "shortest_path_to_flagged"] is None


def test_degree_features_compute_directed_degrees_and_centrality() -> None:
    graph = nx.DiGraph()
    graph.add_edge("A1", "A2")
    graph.add_node("A3")
    before_edges = list(graph.edges())

    frame = compute_degree_features(graph, ["A1", "A2", "A3", "A4"])

    row_a1 = frame.set_index("account_id").loc["A1"]
    row_a2 = frame.set_index("account_id").loc["A2"]
    row_a4 = frame.set_index("account_id").loc["A4"]
    assert row_a1["degree"] == 1
    assert row_a1["out_degree"] == 1
    assert row_a2["in_degree"] == 1
    assert row_a4["degree"] == 0
    assert isinstance(row_a1["degree_centrality"], float)
    assert list(graph.edges()) == before_edges
