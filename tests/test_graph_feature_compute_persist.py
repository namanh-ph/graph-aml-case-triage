"""Tests for combined graph analytics compute and persist workflow."""

import pandas as pd
import pytest

import graph_aml.graph.feature_persistence as persistence_module
from graph_aml.graph import (
    GRAPH_ANALYTICS_FEATURE_COLUMNS,
    GraphAnalyticsError,
    GraphAnalyticsResult,
    GraphFeaturePersistenceConfig,
    GraphFeaturePersistenceError,
    GraphFeaturePersistenceResult,
    compute_and_persist_graph_features_from_neo4j,
)


class FakeEngine:
    pass


class FakeDriver:
    pass


def _features() -> pd.DataFrame:
    row = {column: 0 for column in GRAPH_ANALYTICS_FEATURE_COLUMNS}
    row["account_id"] = "A1"
    return pd.DataFrame([row], columns=GRAPH_ANALYTICS_FEATURE_COLUMNS)


def test_compute_and_persist_graph_features_computes_and_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_compute(driver, config=None, database=None):
        calls.append(f"compute:{database}")
        return GraphAnalyticsResult(
            features=_features(),
            summary={"account_count": 1},
            metadata={"projection": {"node_count": 2}},
        )

    def fake_persist(engine, features, config=None, **kwargs):
        calls.append(f"persist:{config.graph_database}")
        assert kwargs["analytics_summary"] == {"account_count": 1}
        assert kwargs["analytics_metadata"] == {"projection": {"node_count": 2}}
        return GraphFeaturePersistenceResult(rows_persisted=1)

    monkeypatch.setattr(
        persistence_module,
        "compute_graph_analytics_features_from_neo4j",
        fake_compute,
    )
    monkeypatch.setattr(persistence_module, "persist_graph_features", fake_persist)

    result = compute_and_persist_graph_features_from_neo4j(
        FakeEngine(),
        FakeDriver(),
        persistence_config=GraphFeaturePersistenceConfig(write_audit=False),
        database="neo4j",
    )

    assert result.rows_persisted == 1
    assert calls == ["compute:neo4j", "persist:neo4j"]


def test_compute_and_persist_propagates_controlled_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        persistence_module,
        "compute_graph_analytics_features_from_neo4j",
        lambda *args, **kwargs: (_ for _ in ()).throw(GraphAnalyticsError("boom")),
    )

    with pytest.raises(GraphAnalyticsError):
        compute_and_persist_graph_features_from_neo4j(FakeEngine(), FakeDriver())

    monkeypatch.setattr(
        persistence_module,
        "compute_graph_analytics_features_from_neo4j",
        lambda *args, **kwargs: GraphAnalyticsResult(features=_features()),
    )
    monkeypatch.setattr(
        persistence_module,
        "persist_graph_features",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            GraphFeaturePersistenceError("persist failed")
        ),
    )

    with pytest.raises(GraphFeaturePersistenceError):
        compute_and_persist_graph_features_from_neo4j(FakeEngine(), FakeDriver())
