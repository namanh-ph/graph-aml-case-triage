"""Tests for graph analytics influence features."""

import networkx as nx
import pytest

from graph_aml.graph import (
    GraphAnalyticsConfig,
    GraphAnalyticsError,
    compute_influence_features,
)


def test_influence_features_compute_pagerank_and_betweenness() -> None:
    graph = nx.DiGraph()
    graph.add_edges_from([("A1", "A2"), ("A2", "A3"), ("A1", "A3")])

    frame = compute_influence_features(graph, ["A1", "A2", "A4"])

    by_account = frame.set_index("account_id")
    assert by_account.loc["A1", "pagerank_score"] > 0
    assert by_account.loc["A2", "betweenness_centrality"] >= 0
    assert by_account.loc["A4", "pagerank_score"] == 0
    assert list(frame["account_id"]) == ["A1", "A2", "A4"]


def test_influence_features_handle_empty_graph_and_deterministic_sampling() -> None:
    empty = compute_influence_features(nx.DiGraph(), ["A1"])
    graph = nx.path_graph(["A1", "A2", "A3"], create_using=nx.DiGraph)
    sampled = compute_influence_features(
        graph,
        ["A1", "A2", "A3"],
        GraphAnalyticsConfig(betweenness_sample_size=1),
    )

    assert empty.loc[0, "pagerank_score"] == 0
    assert sampled["betweenness_centrality"].ge(0).all()


def test_invalid_graph_input_raises_graph_analytics_error() -> None:
    with pytest.raises(GraphAnalyticsError):
        compute_influence_features(object(), ["A1"])
