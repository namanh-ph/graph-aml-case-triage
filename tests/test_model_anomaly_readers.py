"""Tests for anomaly score readback utilities."""

import pandas as pd
import pytest

from graph_aml.models import (
    ModelPersistenceError,
    read_anomaly_score_summary,
    read_anomaly_score_versions,
    read_anomaly_scores,
    read_latest_anomaly_scores,
)


def test_read_anomaly_scores_builds_filtered_query(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_read_sql_query(sql: object, engine: object, params: object = None) -> pd.DataFrame:
        seen["sql"] = str(sql)
        seen["params"] = params
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    read_anomaly_scores(
        object(),
        score_date="2026-01-01",
        model_name="m",
        model_version="v",
        model_run_id="run",
        risk_band="high",
        account_ids=["A1"],
        limit=5,
    )
    assert "mart.account_anomaly_scores" in str(seen["sql"])
    assert "account_id = ANY(:account_ids)" in str(seen["sql"])
    assert seen["params"] == {
        "score_date": "2026-01-01",
        "model_name": "m",
        "model_version": "v",
        "model_run_id": "run",
        "risk_band": "high",
        "account_ids": ["A1"],
        "limit": 5,
    }


def test_latest_reader_selects_latest_set(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_read_sql_query(sql: object, engine: object, params: object = None) -> pd.DataFrame:
        seen["sql"] = str(sql)
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    read_latest_anomaly_scores(object())
    assert "WITH latest" in str(seen["sql"])


def test_versions_reader_returns_dataframe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *args, **kwargs: pd.DataFrame())
    assert isinstance(read_anomaly_score_versions(object()), pd.DataFrame)


def test_summary_reader_returns_json_serialisable_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        pd.DataFrame({"row_count": [3], "unique_account_count": [2], "max_scored_at": ["now"]}),
        pd.DataFrame({"risk_band": ["high"], "row_count": [1]}),
        pd.DataFrame(
            {
                "score_date": ["2026-01-01"],
                "model_name": ["m"],
                "model_version": ["v"],
                "model_run_id": ["run"],
                "row_count": [3],
                "max_scored_at": ["now"],
            }
        ),
    ]

    def fake_read_sql_query(sql: object, engine: object, params: object = None) -> pd.DataFrame:
        return responses.pop(0)

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    summary = read_anomaly_score_summary(object())
    assert summary["row_count"] == 3
    assert summary["risk_band_counts"] == {"high": 1}


def test_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> pd.DataFrame:
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(ModelPersistenceError):
        read_anomaly_scores(object())


def test_invalid_reader_inputs_raise() -> None:
    with pytest.raises(ModelPersistenceError):
        read_anomaly_scores(object(), risk_band="critical")
    with pytest.raises(ModelPersistenceError):
        read_anomaly_scores(object(), limit=-1)
