"""Tests for dashboard graph transformation helpers."""

import pandas as pd
import pytest

from graph_aml.dashboard.config import DashboardConfig, DashboardGraphViewConfig
from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.graph_data import GRAPH_VIEW_EDGE_COLUMNS, GRAPH_VIEW_NODE_COLUMNS
from graph_aml.dashboard.graph_transform import (
    build_graph_view_frames,
    calculate_node_sizes,
    normalise_graph_edge_frame,
    normalise_graph_node_frame,
    summarise_graph_view,
)


def test_node_and_edge_normalisation_and_deduplication() -> None:
    nodes = pd.DataFrame({"node_id": ["A1", "A1"], "node_type": ["account", "account"]})
    edges = pd.DataFrame({"source_id": ["A1", "A1"], "target_id": ["A2", "A2"]})

    normal_nodes = normalise_graph_node_frame(nodes)
    normal_edges = normalise_graph_edge_frame(edges)

    assert tuple(normal_nodes.columns) == GRAPH_VIEW_NODE_COLUMNS
    assert tuple(normal_edges.columns) == GRAPH_VIEW_EDGE_COLUMNS
    assert len(normal_nodes) == 1
    assert len(normal_edges) == 1


def test_graph_size_clipping_respects_config_and_sizes_use_risk() -> None:
    nodes = pd.DataFrame(
        {"node_id": ["A1", "A2"], "node_type": ["account", "account"], "risk_score": [0, 100]}
    )
    edges = pd.DataFrame({"source_id": ["A1"], "target_id": ["A2"]})
    config = DashboardConfig(graph_view=DashboardGraphViewConfig(max_nodes=1, max_edges=1))

    frames = build_graph_view_frames({"nodes": nodes, "edges": edges}, config)
    sizes = calculate_node_sizes(normalise_graph_node_frame(nodes), 10, 20)

    assert len(frames["nodes"]) == 1
    assert sizes.iloc[0] == 10
    assert sizes.iloc[1] == 20


def test_graph_summary_includes_counts_and_helpers_do_not_mutate() -> None:
    nodes = pd.DataFrame({"node_id": ["A1"], "node_type": ["account"], "risk_score": [90]})
    edges = pd.DataFrame({"source_id": ["A1"], "target_id": ["A2"]})
    original_nodes = nodes.copy(deep=True)

    summary = summarise_graph_view(
        normalise_graph_node_frame(nodes),
        normalise_graph_edge_frame(edges),
    )

    assert summary["node_count"] == 1
    assert summary["edge_count"] == 1
    pd.testing.assert_frame_equal(nodes, original_nodes)


def test_malformed_graph_frames_raise() -> None:
    with pytest.raises(DashboardDataError):
        normalise_graph_node_frame(pd.DataFrame({"bad": ["x"]}))
    with pytest.raises(DashboardDataError):
        normalise_graph_edge_frame(pd.DataFrame({"source_id": ["A1"]}))
