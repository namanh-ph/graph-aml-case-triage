"""Tests for graph feature persistence configuration and metadata."""

from datetime import date

import pytest

from graph_aml.graph import (
    DEFAULT_GRAPH_FEATURE_VERSION,
    GraphFeaturePersistenceConfig,
    GraphFeaturePersistenceError,
    build_graph_feature_build_id,
    build_graph_feature_metadata,
    validate_graph_feature_persistence_config,
)


def test_default_graph_feature_persistence_config_is_valid() -> None:
    config = GraphFeaturePersistenceConfig()

    validate_graph_feature_persistence_config(config)
    assert config.feature_version == DEFAULT_GRAPH_FEATURE_VERSION


@pytest.mark.parametrize(
    "kwargs",
    [
        {"feature_version": ""},
        {"graph_build_id": ""},
        {"batch_size": 0},
        {"write_audit": "yes"},
    ],
)
def test_invalid_graph_feature_persistence_config_raises(kwargs: dict[str, object]) -> None:
    with pytest.raises(GraphFeaturePersistenceError):
        GraphFeaturePersistenceConfig(**kwargs)


def test_graph_feature_build_id_is_deterministic_and_safe() -> None:
    build_id = build_graph_feature_build_id(
        date(2025, 1, 25),
        "Graph Features V1",
        "neo4j/local",
    )

    assert build_id == "graph_features_v1_2025_01_25_neo4j_local"
    assert build_id == build_graph_feature_build_id(
        date(2025, 1, 25),
        "Graph Features V1",
        "neo4j/local",
    )


def test_graph_feature_metadata_preserves_inputs_without_mutation() -> None:
    summary = {"account_count": 2}
    metadata = {"projection": {"node_count": 5}}
    extra = {"job": "unit"}

    payload = build_graph_feature_metadata(summary, metadata, extra)

    assert payload["analytics_summary"] == summary
    assert payload["analytics_metadata"] == metadata
    assert payload["extra_metadata"] == extra
    summary["account_count"] = 99
    assert payload["analytics_summary"] == {"account_count": 2}
