"""Tests for graph feature mart readers."""

import json

import pandas as pd
import pytest

from graph_aml.graph import (
    GraphFeaturePersistenceError,
    read_graph_feature_summary,
    read_graph_feature_versions,
    read_graph_features,
    read_latest_graph_features,
)


class FakeEngine:
    pass


def test_read_graph_features_queries_mart_table_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read)

    read_graph_features(
        FakeEngine(),
        feature_date="2025-01-25",
        feature_version="v1",
        graph_build_id="build",
        account_ids=["A1", "A2"],
        limit=10,
    )

    statement, params = calls[0]
    assert "mart.graph_features" in statement
    assert "feature_date = :feature_date" in statement
    assert "feature_version = :feature_version" in statement
    assert "graph_build_id = :graph_build_id" in statement
    assert "account_id = ANY(:account_ids)" in statement
    assert "LIMIT :limit" in statement
    assert params == {
        "feature_date": "2025-01-25",
        "feature_version": "v1",
        "graph_build_id": "build",
        "account_ids": ["A1", "A2"],
        "limit": 10,
    }


def test_read_latest_graph_features_selects_latest_computed_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_read(statement, engine, params=None):
        calls.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read)

    read_latest_graph_features(FakeEngine(), limit=5)

    assert "WITH latest AS" in calls[0]
    assert "ORDER BY computed_at DESC" in calls[0]
    assert "LIMIT :limit" in calls[0]


def test_read_graph_feature_versions_returns_dataframe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd,
        "read_sql_query",
        lambda statement, engine, params=None: pd.DataFrame({"feature_version": ["v1"]}),
    )

    assert read_graph_feature_versions(FakeEngine())["feature_version"].tolist() == ["v1"]


def test_read_graph_feature_summary_is_json_serialisable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read(statement, engine, params=None):
        sql = str(statement)
        if "GROUP BY" in sql:
            return pd.DataFrame(
                [
                    {
                        "feature_date": "2025-01-25",
                        "feature_version": "v1",
                        "graph_build_id": "build",
                        "graph_database": "neo4j",
                        "row_count": 2,
                        "max_computed_at": "2025-01-25T00:00:00Z",
                    }
                ]
            )
        return pd.DataFrame(
            [{"row_count": 2, "unique_account_count": 2, "max_computed_at": "2025-01-25"}]
        )

    monkeypatch.setattr(pd, "read_sql_query", fake_read)

    summary = read_graph_feature_summary(FakeEngine())

    json.dumps(summary)
    assert summary["row_count"] == 2
    assert summary["latest_feature_version"] == "v1"


def test_reader_failures_raise_graph_feature_persistence_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(statement, engine, params=None):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(pd, "read_sql_query", fail)

    with pytest.raises(GraphFeaturePersistenceError):
        read_graph_features(FakeEngine())

    with pytest.raises(GraphFeaturePersistenceError):
        read_graph_features(FakeEngine(), limit=-1)
