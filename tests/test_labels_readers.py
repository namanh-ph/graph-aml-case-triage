from __future__ import annotations

import json

import pandas as pd
import pytest

from graph_aml.labels import (
    LabelPersistenceError,
    read_account_labels,
    read_account_supervised_dataset,
    read_case_labels,
    read_case_supervised_dataset,
    read_label_summary,
)


class FakeEngine:
    pass


@pytest.fixture
def capture_sql(monkeypatch):
    queries: list[tuple[str, object]] = []

    def fake_read_sql_query(sql, engine, params=None):  # noqa: ANN001
        queries.append((str(sql), params))
        return pd.DataFrame({"case_label": [1], "label_timestamp": ["2026-01-01"]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    return queries


def test_case_label_reader_queries_table(capture_sql) -> None:
    read_case_labels(FakeEngine())  # type: ignore[arg-type]
    assert "aml.case_labels" in capture_sql[0][0]


def test_account_label_reader_queries_table(capture_sql) -> None:
    read_account_labels(FakeEngine())  # type: ignore[arg-type]
    assert "aml.account_labels" in capture_sql[0][0]


def test_case_dataset_reader_queries_table(capture_sql) -> None:
    read_case_supervised_dataset(FakeEngine())  # type: ignore[arg-type]
    assert "mart.case_supervised_dataset" in capture_sql[0][0]


def test_account_dataset_reader_queries_table(capture_sql) -> None:
    read_account_supervised_dataset(FakeEngine())  # type: ignore[arg-type]
    assert "mart.account_supervised_dataset" in capture_sql[0][0]


def test_readers_filter_by_version(capture_sql) -> None:
    read_case_labels(FakeEngine(), label_version="v1")  # type: ignore[arg-type]
    assert "label_version = :version" in capture_sql[0][0]


def test_readers_filter_by_binary_label(capture_sql) -> None:
    read_case_labels(FakeEngine(), case_label=1)  # type: ignore[arg-type]
    assert "case_label = :label" in capture_sql[0][0]


def test_readers_apply_validated_limits(capture_sql) -> None:
    read_case_labels(FakeEngine(), limit=5)  # type: ignore[arg-type]
    assert "LIMIT :limit" in capture_sql[0][0]


def test_summary_reader_returns_json_serialisable_payload(capture_sql) -> None:
    json.dumps(read_label_summary(FakeEngine()), default=str)  # type: ignore[arg-type]


def test_reader_failures_raise_label_persistence_error(monkeypatch) -> None:
    def fail_read_sql_query(sql, engine, params=None):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)
    with pytest.raises(LabelPersistenceError):
        read_case_labels(FakeEngine())  # type: ignore[arg-type]


def test_readers_do_not_create_engines(monkeypatch, capture_sql) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *args, **kwargs: pytest.fail("no engine"),
    )
    read_case_labels(FakeEngine())  # type: ignore[arg-type]
