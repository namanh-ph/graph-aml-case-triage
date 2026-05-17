from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.models import (
    SupervisedPersistenceError,
    read_supervised_model_runs,
    read_supervised_model_scores,
    read_supervised_model_summary,
)


class FakeEngine:
    pass


@pytest.fixture
def capture_sql(monkeypatch):
    calls = []

    def fake_read(sql, engine, params=None):
        calls.append((str(sql), params))
        if "supervised_model_scores" in str(sql):
            return pd.DataFrame(
                {"entity_level": ["case"], "predicted_label": [1], "supervised_score": [0.9]}
            )
        return pd.DataFrame({"model_version": ["v1"], "trained_at": ["2026-01-01"]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    return calls


def test_score_reader_queries_score_table(capture_sql) -> None:
    read_supervised_model_scores(FakeEngine())  # type: ignore[arg-type]
    assert "mart.supervised_model_scores" in capture_sql[0][0]


def test_model_run_reader_queries_run_table(capture_sql) -> None:
    read_supervised_model_runs(FakeEngine())  # type: ignore[arg-type]
    assert "governance.supervised_model_runs" in capture_sql[0][0]


def test_score_reader_filters_and_limits(capture_sql) -> None:
    read_supervised_model_scores(
        FakeEngine(),  # type: ignore[arg-type]
        entity_level="case",
        model_version="v1",
        dataset_version="d1",
        predicted_label=1,
        limit=10,
    )
    sql, params = capture_sql[0]
    assert ":entity_level" in sql
    assert params["limit"] == 10
    assert params["predicted_label"] == 1


def test_run_reader_filters(capture_sql) -> None:
    read_supervised_model_runs(FakeEngine(), model_version="v1", entity_level="case")  # type: ignore[arg-type]
    assert capture_sql[0][1]["model_version"] == "v1"


def test_summary_reader_returns_json_payload(capture_sql) -> None:
    summary = read_supervised_model_summary(FakeEngine())  # type: ignore[arg-type]
    assert summary["score_row_count"] == 1
    assert summary["model_run_count"] == 1


def test_reader_failures_raise(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise Exception("x")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(SupervisedPersistenceError):
        read_supervised_model_scores(FakeEngine())  # type: ignore[arg-type]


def test_readers_do_not_create_engines(monkeypatch, capture_sql) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *args, **kwargs: pytest.fail("no engine"),
    )
    read_supervised_model_runs(FakeEngine())  # type: ignore[arg-type]
