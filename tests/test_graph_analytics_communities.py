"""Tests for graph analytics community features."""

import networkx as nx

from graph_aml.graph import GraphAnalyticsConfig, compute_community_features


def test_connected_component_communities_are_deterministic() -> None:
    graph = nx.Graph()
    graph.add_edges_from([("A1", "A2"), ("A3", "X1")])

    frame = compute_community_features(graph, ["A1", "A2", "A3", "A4"])
    by_account = frame.set_index("account_id")

    assert by_account.loc["A1", "community_id"] == by_account.loc["A2", "community_id"]
    assert by_account.loc["A1", "community_size"] == 2
    assert by_account.loc["A3", "graph_component_size"] == 2
    assert by_account.loc["A4", "community_size"] == 1
    assert by_account.loc["A1", "clustering_coefficient"] >= 0


def test_greedy_modularity_communities_are_supported() -> None:
    graph = nx.Graph()
    graph.add_edges_from([("A1", "A2"), ("A2", "A3"), ("A4", "A5")])

    frame = compute_community_features(
        graph,
        ["A1", "A2", "A3", "A4", "A5"],
        GraphAnalyticsConfig(community_algorithm="greedy_modularity"),
    )

    assert frame["community_id"].min() == 1
    assert frame["community_size"].ge(1).all()


def test_empty_graph_assigns_singleton_communities() -> None:
    frame = compute_community_features(nx.Graph(), ["A2", "A1"])

    assert list(frame["account_id"]) == ["A1", "A2"]
    assert frame["community_size"].tolist() == [1, 1]
