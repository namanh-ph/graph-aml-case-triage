"""Tests for graph analytics alert proximity features."""

import networkx as nx

from graph_aml.graph import GraphAnalyticsConfig, compute_alert_proximity_features


def test_alert_proximity_counts_direct_alerts_and_shortest_paths() -> None:
    graph = nx.Graph()
    graph.add_node("A1", node_type="Account")
    graph.add_node("A2", node_type="Account")
    graph.add_node("A3", node_type="Account")
    graph.add_node("AL1", node_type="Alert", severity="high")
    graph.add_node("AL2", node_type="Alert", severity="medium")
    graph.add_edges_from([("A1", "AL1"), ("A1", "AL2"), ("A2", "A1")])

    frame = compute_alert_proximity_features(
        graph,
        ["A1", "A2", "A3"],
        GraphAnalyticsConfig(max_shortest_path_depth=2),
    )
    by_account = frame.set_index("account_id")

    assert by_account.loc["A1", "alert_count"] == 2
    assert by_account.loc["A1", "high_risk_alert_count"] == 1
    assert by_account.loc["A1", "shortest_path_to_flagged"] == 1
    assert by_account.loc["A2", "shortest_path_to_flagged"] == 2
    assert by_account.loc["A3", "shortest_path_to_flagged"] is None


def test_alert_proximity_respects_max_depth_and_empty_graph() -> None:
    graph = nx.path_graph(["A1", "X1", "AL1"])
    graph.nodes["AL1"]["node_type"] = "Alert"
    graph.nodes["AL1"]["severity"] = "critical"

    frame = compute_alert_proximity_features(
        graph,
        ["A1"],
        GraphAnalyticsConfig(max_shortest_path_depth=1),
    )
    empty = compute_alert_proximity_features(nx.Graph(), ["A1"])

    assert frame.loc[0, "shortest_path_to_flagged"] is None
    assert empty.loc[0, "alert_count"] == 0
