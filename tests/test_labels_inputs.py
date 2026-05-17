from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.labels import (
    LabelInputError,
    read_label_account_features,
    read_label_account_risk_scores,
    read_label_anomaly_scores,
    read_label_case_entities,
    read_label_case_risk_scores,
    read_label_cases,
    read_label_graph_features,
    read_label_lifecycle_events,
)


class FakeEngine:
    pass


@pytest.fixture
def capture_sql(monkeypatch):
    queries: list[tuple[str, object]] = []

    def fake_read_sql_query(sql, engine, params=None):  # noqa: ANN001
        queries.append((str(sql), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    return queries


def test_case_reader_queries_cases(capture_sql) -> None:
    read_label_cases(FakeEngine())  # type: ignore[arg-type]
    assert "aml.cases" in capture_sql[0][0]


def test_lifecycle_reader_queries_lifecycle_events(capture_sql) -> None:
    read_label_lifecycle_events(FakeEngine())  # type: ignore[arg-type]
    assert "aml.case_lifecycle_events" in capture_sql[0][0]


def test_case_entity_reader_queries_case_entities(capture_sql) -> None:
    read_label_case_entities(FakeEngine())  # type: ignore[arg-type]
    assert "aml.case_entities" in capture_sql[0][0]


def test_case_risk_reader_queries_case_risk_scores(capture_sql) -> None:
    read_label_case_risk_scores(FakeEngine())  # type: ignore[arg-type]
    assert "aml.case_risk_scores" in capture_sql[0][0]


def test_account_feature_reader_queries_mart_features(capture_sql) -> None:
    read_label_account_features(FakeEngine())  # type: ignore[arg-type]
    assert "mart.features_account_daily" in capture_sql[0][0]


def test_account_risk_reader_queries_account_risk(capture_sql) -> None:
    read_label_account_risk_scores(FakeEngine())  # type: ignore[arg-type]
    assert "mart.account_risk_scores" in capture_sql[0][0]


def test_graph_feature_reader_queries_graph_features(capture_sql) -> None:
    read_label_graph_features(FakeEngine())  # type: ignore[arg-type]
    assert "mart.graph_features" in capture_sql[0][0]


def test_anomaly_score_reader_queries_anomaly_scores(capture_sql) -> None:
    read_label_anomaly_scores(FakeEngine())  # type: ignore[arg-type]
    assert "mart.account_anomaly_scores" in capture_sql[0][0]


def test_readers_apply_validated_limits(capture_sql) -> None:
    read_label_cases(FakeEngine(), limit=10)  # type: ignore[arg-type]
    assert "LIMIT :limit" in capture_sql[0][0]
    assert capture_sql[0][1]["limit"] == 10


def test_readers_use_bound_parameters(capture_sql) -> None:
    read_label_lifecycle_events(FakeEngine(), case_ids=("C1",))  # type: ignore[arg-type]
    assert ":case_ids" in capture_sql[0][0]


def test_reader_failures_raise_label_input_error(monkeypatch) -> None:
    def fail_read_sql_query(sql, engine, params=None):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)
    with pytest.raises(LabelInputError):
        read_label_cases(FakeEngine())  # type: ignore[arg-type]


def test_readers_do_not_create_engines(monkeypatch, capture_sql) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *args, **kwargs: pytest.fail("no engine"),
    )
    read_label_cases(FakeEngine())  # type: ignore[arg-type]
