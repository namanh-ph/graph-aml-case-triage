"""Tests for graph analytics cycle features."""

import networkx as nx

from graph_aml.graph import GraphAnalyticsConfig, compute_cycle_features


def test_cycle_count_is_zero_without_cycles() -> None:
    graph = nx.DiGraph()
    graph.add_edge("A1", "A2")

    frame = compute_cycle_features(graph, ["A1", "A2"])

    assert frame["cycle_count"].tolist() == [0, 0]


def test_cycle_count_is_positive_for_accounts_in_cycle() -> None:
    graph = nx.DiGraph()
    graph.add_edges_from([("A1", "A2"), ("A2", "A3"), ("A3", "A1")])

    frame = compute_cycle_features(graph, ["A1", "A2", "A3"])

    assert frame["cycle_count"].tolist() == [1, 1, 1]


def test_cycle_count_respects_hop_limit_and_does_not_mutate_graph() -> None:
    graph = nx.DiGraph()
    graph.add_edges_from([("A1", "A2"), ("A2", "A3"), ("A3", "A4"), ("A4", "A1")])
    before = list(graph.edges())

    frame = compute_cycle_features(graph, ["A1", "A2"], GraphAnalyticsConfig(cycle_max_hops=3))

    assert frame["cycle_count"].tolist() == [0, 0]
    assert list(graph.edges()) == before


def test_empty_graph_cycle_features_are_zero() -> None:
    frame = compute_cycle_features(nx.DiGraph(), ["A1"])

    assert frame.loc[0, "cycle_count"] == 0
