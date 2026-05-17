"""Tests for model feature input readers and frame preparation."""

import pandas as pd
import pytest

from graph_aml.models import (
    MODEL_ACCOUNT_BEHAVIOURAL_FEATURES,
    MODEL_ACCOUNT_JURISDICTION_FEATURES,
    MODEL_GRAPH_FEATURES,
    IsolationForestModelConfig,
    ModelFeatureInputError,
    build_model_feature_frame,
    prepare_account_feature_frame,
    prepare_graph_feature_frame,
    read_model_account_features,
    read_model_graph_features,
    select_model_feature_columns,
)


def account_features() -> pd.DataFrame:
    rows = []
    for idx in range(3):
        row = {"account_id": f"A{idx}", "feature_date": "2026-01-01"}
        for column in (*MODEL_ACCOUNT_BEHAVIOURAL_FEATURES, *MODEL_ACCOUNT_JURISDICTION_FEATURES):
            row[column] = idx + 1
        rows.append(row)
    return pd.DataFrame(rows)


def graph_features() -> pd.DataFrame:
    rows = []
    for idx in range(3):
        row = {"account_id": f"A{idx}", "feature_date": "2026-01-01"}
        for column in MODEL_GRAPH_FEATURES:
            row[column] = idx + 2
        rows.append(row)
    return pd.DataFrame(rows)


def test_account_feature_reader_queries_account_feature_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_read_sql_query(sql: object, engine: object, params: object = None) -> pd.DataFrame:
        seen["sql"] = str(sql)
        seen["params"] = params
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    read_model_account_features(object(), feature_date="2026-01-01", feature_version="v1", limit=5)
    assert "mart.features_account_daily" in str(seen["sql"])
    assert "LIMIT :limit" in str(seen["sql"])
    assert seen["params"] == {"feature_date": "2026-01-01", "feature_version": "v1", "limit": 5}


def test_graph_feature_reader_queries_graph_feature_table(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_read_sql_query(sql: object, engine: object, params: object = None) -> pd.DataFrame:
        seen["sql"] = str(sql)
        seen["params"] = params
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    read_model_graph_features(object(), graph_build_id="build1", limit=10)
    assert "mart.graph_features" in str(seen["sql"])
    assert seen["params"] == {"graph_build_id": "build1", "limit": 10}


def test_readers_reject_invalid_limits() -> None:
    with pytest.raises(ModelFeatureInputError):
        read_model_account_features(object(), limit=-1)


def test_feature_column_selector_respects_enabled_groups() -> None:
    config = IsolationForestModelConfig(use_graph_features=False)
    columns = select_model_feature_columns(config)
    assert MODEL_GRAPH_FEATURES[0] not in columns
    assert MODEL_ACCOUNT_BEHAVIOURAL_FEATURES[0] in columns


def test_account_and_graph_preparation_keep_canonical_columns() -> None:
    account_frame = prepare_account_feature_frame(account_features())
    graph_frame = prepare_graph_feature_frame(graph_features())
    assert list(account_frame.columns)[0] == "account_id"
    assert MODEL_ACCOUNT_BEHAVIOURAL_FEATURES[0] in account_frame.columns
    assert MODEL_GRAPH_FEATURES[0] in graph_frame.columns


def test_model_feature_frame_merges_by_account_id() -> None:
    frame = build_model_feature_frame(account_features(), graph_features())
    assert list(frame.columns)[0] == "account_id"
    assert len(frame) == 3
    assert MODEL_GRAPH_FEATURES[0] in frame.columns


def test_duplicate_or_missing_account_ids_raise() -> None:
    duplicate = account_features()
    duplicate.loc[1, "account_id"] = duplicate.loc[0, "account_id"]
    with pytest.raises(ModelFeatureInputError):
        build_model_feature_frame(duplicate, graph_features())
    missing = account_features()
    missing.loc[1, "account_id"] = None
    with pytest.raises(ModelFeatureInputError):
        build_model_feature_frame(missing, graph_features())


def test_input_dataframes_are_not_mutated() -> None:
    accounts = account_features()
    graphs = graph_features()
    account_copy = accounts.copy(deep=True)
    graph_copy = graphs.copy(deep=True)
    build_model_feature_frame(accounts, graphs)
    pd.testing.assert_frame_equal(accounts, account_copy)
    pd.testing.assert_frame_equal(graphs, graph_copy)


def test_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> pd.DataFrame:
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(ModelFeatureInputError):
        read_model_graph_features(object())
