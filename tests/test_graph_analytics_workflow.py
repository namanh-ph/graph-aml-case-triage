"""Tests for high-level graph analytics workflows."""

import pytest

import graph_aml.graph.analytics as analytics_module
from graph_aml.graph import (
    GraphAnalyticsError,
    GraphAnalyticsResult,
    ProjectedGraphData,
    compute_graph_analytics_features,
    compute_graph_analytics_features_from_neo4j,
)


class FakeDriver:
    pass


def _projected() -> ProjectedGraphData:
    return ProjectedGraphData(
        nodes=[
            {"id": "A1", "labels": ["Account"], "properties": {}},
            {"id": "A2", "labels": ["Account"], "properties": {}},
            {"id": "AL1", "labels": ["Alert"], "properties": {"severity": "high"}},
            {"id": "T1", "labels": ["Transaction"], "properties": {"amount": 100.0}},
        ],
        relationships=[
            {"source_id": "A1", "target_id": "T1", "type": "SENT", "properties": {}},
            {"source_id": "T1", "target_id": "A2", "type": "RECEIVED", "properties": {}},
            {"source_id": "AL1", "target_id": "A1", "type": "FLAGS_ACCOUNT", "properties": {}},
        ],
        account_ids=("A1", "A2"),
        alert_ids=("AL1",),
        transaction_ids=("T1",),
        metadata={"node_count": 4, "relationship_count": 3},
    )


def test_compute_graph_analytics_features_returns_result_with_summary() -> None:
    result = compute_graph_analytics_features(_projected())

    assert isinstance(result, GraphAnalyticsResult)
    assert list(result.features["account_id"]) == ["A1", "A2"]
    assert result.summary["account_count"] == 2
    assert result.summary["community_count"] >= 1
    assert result.summary["nonzero_pagerank_count"] >= 1
    assert result.metadata["projection"]["node_count"] == 4


def test_empty_projected_graph_data_is_handled() -> None:
    result = compute_graph_analytics_features(ProjectedGraphData())

    assert result.features.empty
    assert result.summary["account_count"] == 0


def test_compute_features_from_neo4j_reads_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        analytics_module,
        "read_projected_graph_data",
        lambda driver, config, database=None: _projected(),
    )

    result = compute_graph_analytics_features_from_neo4j(FakeDriver(), database="neo4j")

    assert result.summary["account_count"] == 2


def test_high_level_workflow_failures_raise_graph_analytics_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        analytics_module,
        "build_networkx_graph",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(GraphAnalyticsError):
        compute_graph_analytics_features(_projected())
