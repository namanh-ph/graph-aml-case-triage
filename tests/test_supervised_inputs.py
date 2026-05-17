from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.models import (
    SupervisedDatasetConfig,
    SupervisedModelConfig,
    SupervisedModelInputError,
    read_account_supervised_training_dataset,
    read_case_supervised_training_dataset,
    read_supervised_training_dataset,
)


class FakeEngine:
    pass


@pytest.fixture
def capture_sql(monkeypatch):
    calls = []

    def fake_read(sql, engine, params=None):
        calls.append((str(sql), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    return calls


def test_case_reader_queries_case_dataset(capture_sql) -> None:
    read_case_supervised_training_dataset(FakeEngine())  # type: ignore[arg-type]
    assert "mart.case_supervised_dataset" in capture_sql[0][0]


def test_account_reader_queries_account_dataset(capture_sql) -> None:
    read_account_supervised_training_dataset(FakeEngine())  # type: ignore[arg-type]
    assert "mart.account_supervised_dataset" in capture_sql[0][0]


def test_generic_reader_selects_case(capture_sql) -> None:
    read_supervised_training_dataset(FakeEngine())  # type: ignore[arg-type]
    assert "mart.case_supervised_dataset" in capture_sql[0][0]


def test_generic_reader_selects_account(capture_sql) -> None:
    config = SupervisedModelConfig(dataset=SupervisedDatasetConfig(level="account"))
    read_supervised_training_dataset(FakeEngine(), config)  # type: ignore[arg-type]
    assert "mart.account_supervised_dataset" in capture_sql[0][0]


def test_readers_apply_limits(capture_sql) -> None:
    read_case_supervised_training_dataset(FakeEngine(), limit=5)  # type: ignore[arg-type]
    assert capture_sql[0][1]["limit"] == 5


def test_readers_use_bound_parameters(capture_sql) -> None:
    read_case_supervised_training_dataset(
        FakeEngine(),  # type: ignore[arg-type]
        dataset_version="v1",
    )
    assert ":dataset_version" in capture_sql[0][0]
    assert capture_sql[0][1]["dataset_version"] == "v1"


def test_reader_failures_raise(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise Exception("x")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(SupervisedModelInputError):
        read_case_supervised_training_dataset(FakeEngine())  # type: ignore[arg-type]


def test_readers_do_not_create_engines(monkeypatch, capture_sql) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *args, **kwargs: pytest.fail("no engine"),
    )
    read_case_supervised_training_dataset(FakeEngine())  # type: ignore[arg-type]
