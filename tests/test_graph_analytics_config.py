"""Tests for graph analytics configuration."""

import pytest

from graph_aml.graph import (
    GraphAnalyticsConfig,
    GraphAnalyticsConfigurationError,
    graph_analytics_config_from_mapping,
    load_graph_analytics_config,
    validate_graph_analytics_config,
)


def test_default_graph_analytics_config_is_valid() -> None:
    config = GraphAnalyticsConfig()

    validate_graph_analytics_config(config)
    assert config.pagerank_alpha == 0.85


@pytest.mark.parametrize(
    "payload",
    [
        {"projection_relationship_types": ("bad-name",)},
        {"account_flow_relationship_types": ("bad-name",)},
        {"max_shortest_path_depth": 0},
        {"pagerank_alpha": 1.5},
        {"betweenness_sample_size": 0},
        {"community_algorithm": "unsupported"},
        {"cycle_max_hops": 1},
    ],
)
def test_invalid_graph_analytics_config_raises(payload: dict[str, object]) -> None:
    with pytest.raises(GraphAnalyticsConfigurationError):
        graph_analytics_config_from_mapping(payload)


def test_graph_analytics_config_can_be_built_from_mapping() -> None:
    config = graph_analytics_config_from_mapping(
        {
            "projection_relationship_types": ["SENT"],
            "account_flow_relationship_types": ["SENT"],
            "max_shortest_path_depth": 3,
            "pagerank_alpha": 0.7,
            "betweenness_sample_size": 2,
            "community_algorithm": "greedy_modularity",
            "include_counterparties": False,
            "include_alert_nodes": "false",
            "include_transaction_nodes": True,
            "cycle_max_hops": 3,
            "high_risk_severities": ["critical"],
        }
    )

    assert config.projection_relationship_types == ("SENT",)
    assert config.include_counterparties is False
    assert config.include_alert_nodes is False
    assert config.community_algorithm == "greedy_modularity"


def test_graph_analytics_config_can_be_loaded_from_yaml(tmp_path) -> None:
    path = tmp_path / "graph.yaml"
    path.write_text(
        """
analytics:
  projection_relationship_types: [SENT, RECEIVED]
  account_flow_relationship_types: [SENT]
  max_shortest_path_depth: 2
  pagerank_alpha: 0.6
  include_counterparties: false
  include_alert_nodes: true
  include_transaction_nodes: false
  cycle_max_hops: 3
  high_risk_severities: [high]
""",
        encoding="utf-8",
    )

    config = load_graph_analytics_config(path)

    assert config.projection_relationship_types == ("SENT", "RECEIVED")
    assert config.include_transaction_nodes is False


def test_config_loading_does_not_connect_to_neo4j(tmp_path) -> None:
    path = tmp_path / "missing.yaml"

    config = load_graph_analytics_config(path)

    assert isinstance(config, GraphAnalyticsConfig)
