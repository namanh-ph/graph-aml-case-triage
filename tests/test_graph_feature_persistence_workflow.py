"""Tests for graph feature persistence workflow."""

import pandas as pd
import pytest

import graph_aml.graph.feature_persistence as persistence_module
from graph_aml.graph import (
    GRAPH_ANALYTICS_FEATURE_COLUMNS,
    GraphFeaturePersistenceConfig,
    GraphFeaturePersistenceError,
    GraphFeaturePersistenceResult,
    persist_graph_features,
    prepare_graph_features_for_persistence,
    upsert_graph_features,
)


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.executions: list[tuple[str, object]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object, parameters: object | None = None) -> None:
        if self.fail:
            raise RuntimeError("upsert failed")
        self.executions.append((str(statement), parameters))


class FakeEngine:
    def __init__(self, fail: bool = False) -> None:
        self.connection = FakeConnection(fail=fail)

    def begin(self) -> FakeConnection:
        return self.connection


def _features() -> pd.DataFrame:
    row = {column: 0 for column in GRAPH_ANALYTICS_FEATURE_COLUMNS}
    row.update({"account_id": "A1", "pagerank_score": 0.4})
    return pd.DataFrame([row], columns=GRAPH_ANALYTICS_FEATURE_COLUMNS)


def test_upsert_graph_features_returns_zero_for_empty_input() -> None:
    assert upsert_graph_features(FakeEngine(), pd.DataFrame()) == 0


def test_upsert_graph_features_writes_rows_in_batches() -> None:
    features = pd.concat([_features().assign(account_id=f"A{i}") for i in range(3)])
    prepared = prepare_graph_features_for_persistence(features)
    engine = FakeEngine()

    count = upsert_graph_features(engine, prepared, batch_size=2)

    assert count == 3
    assert len(engine.connection.executions) == 2
    assert isinstance(engine.connection.executions[0][1], list)
    assert "INSERT INTO mart.graph_features" in engine.connection.executions[0][0]


def test_persist_graph_features_prepares_upserts_and_returns_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        persistence_module,
        "upsert_graph_features",
        lambda engine, prepared, batch_size=1000: calls.append("upsert") or len(prepared),
    )
    monkeypatch.setattr(
        persistence_module,
        "write_graph_feature_persistence_audit_event",
        lambda *args, **kwargs: calls.append("audit"),
    )

    result = persist_graph_features(FakeEngine(), _features())

    assert isinstance(result, GraphFeaturePersistenceResult)
    assert calls == ["upsert", "audit"]
    assert result.rows_persisted == 1


def test_persist_graph_features_skips_audit_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        persistence_module,
        "upsert_graph_features",
        lambda engine, prepared, batch_size=1000: len(prepared),
    )
    monkeypatch.setattr(
        persistence_module,
        "write_graph_feature_persistence_audit_event",
        lambda *args, **kwargs: calls.append("audit"),
    )

    persist_graph_features(
        FakeEngine(),
        _features(),
        GraphFeaturePersistenceConfig(write_audit=False),
    )

    assert calls == []


def test_persistence_failures_raise_graph_feature_persistence_error() -> None:
    prepared = prepare_graph_features_for_persistence(_features())

    with pytest.raises(GraphFeaturePersistenceError):
        upsert_graph_features(FakeEngine(fail=True), prepared)
