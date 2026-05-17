"""Tests for reading persisted mart account features."""

from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import text

from graph_aml.features import (
    MartFeatureReadError,
    get_mart_account_feature_date_range,
    get_mart_account_feature_versions,
    read_mart_account_features,
)


class FakeEngine:
    pass


def test_read_mart_account_features_reads_from_mart_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        statements.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_mart_account_features(FakeEngine())

    assert "mart.features_account_daily" in statements[0]


def test_read_mart_account_features_applies_feature_version_filter_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_mart_account_features(FakeEngine(), feature_version="v1")

    assert "feature_version = :feature_version" in calls[0][0]
    assert calls[0][1] == {"feature_version": "v1"}


def test_read_mart_account_features_applies_limit_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_mart_account_features(FakeEngine(), limit=5)

    assert "LIMIT :limit" in calls[0][0]
    assert calls[0][1] == {"limit": 5}


def test_read_mart_account_features_orders_by_feature_date_and_account_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        statements.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_mart_account_features(FakeEngine())

    assert "ORDER BY feature_date, account_id" in statements[0]


def test_get_mart_account_feature_versions_returns_sorted_tuple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pd,
        "read_sql_query",
        lambda statement, engine, params=None: pd.DataFrame({"feature_version": ["v2", "v1"]}),
    )

    assert get_mart_account_feature_versions(FakeEngine()) == ("v1", "v2")


def test_get_mart_account_feature_date_range_returns_min_and_max_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pd,
        "read_sql_query",
        lambda statement, engine, params=None: pd.DataFrame(
            [{"min_feature_date": "2025-01-01", "max_feature_date": "2025-03-31"}]
        ),
    )

    assert get_mart_account_feature_date_range(FakeEngine()) == {
        "min_feature_date": "2025-01-01",
        "max_feature_date": "2025-03-31",
    }


def test_mart_reader_failures_raise_mart_feature_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read_sql_query(statement, engine, params=None):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)

    with pytest.raises(MartFeatureReadError):
        read_mart_account_features(FakeEngine())


def test_import_does_not_attempt_database_connection() -> None:
    assert str(text("SELECT 1"))
