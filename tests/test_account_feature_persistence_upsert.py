"""Tests for account feature mart upserts."""

from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.features import FeaturePersistenceError, upsert_account_features


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.executions: list[tuple[str, object]] = []

    def __enter__(self) -> FakeConnection:
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
    return pd.DataFrame(
        [
            {
                "account_id": "ACC_A",
                "feature_date": "2025-01-01",
                "feature_version": "account_features_v1",
                "txn_count_1d": 1,
                "txn_count_7d": 1,
                "total_sent_7d": 10.0,
                "total_received_7d": 0.0,
                "avg_txn_amount_30d": 10.0,
                "max_txn_amount_30d": 10.0,
                "unique_counterparties_7d": 1,
                "in_out_ratio_7d": 999999.0,
                "retained_balance_proxy": -10.0,
                "below_threshold_count_24h": 0,
                "dormant_days_before_activity": None,
                "cross_border_ratio_30d": 0.0,
                "high_risk_country_exposure": 0.0,
                "counterparty_entropy": 0.0,
            }
        ]
    )


def test_upsert_account_features_returns_zero_for_empty_dataframe() -> None:
    assert upsert_account_features(FakeEngine(), pd.DataFrame()) == 0


def test_upsert_account_features_builds_sql_targeting_mart_table() -> None:
    engine = FakeEngine()

    upsert_account_features(engine, _features())

    assert "INSERT INTO mart.features_account_daily" in engine.connection.executions[0][0]


def test_upsert_account_features_sql_contains_on_conflict() -> None:
    engine = FakeEngine()

    upsert_account_features(engine, _features())

    assert "ON CONFLICT" in engine.connection.executions[0][0]


def test_upsert_account_features_conflict_key_includes_account_date_version() -> None:
    engine = FakeEngine()

    upsert_account_features(engine, _features())

    statement = engine.connection.executions[0][0]
    assert "account_id, feature_date, feature_version" in statement


def test_upsert_account_features_updates_non_key_columns_on_conflict() -> None:
    engine = FakeEngine()

    upsert_account_features(engine, _features())

    statement = engine.connection.executions[0][0]
    assert "txn_count_7d = EXCLUDED.txn_count_7d" in statement


def test_upsert_account_features_uses_bound_parameters() -> None:
    engine = FakeEngine()

    upsert_account_features(engine, _features())

    params = engine.connection.executions[0][1]
    assert isinstance(params, list)
    assert params[0]["account_id"] == "ACC_A"


def test_upsert_account_features_returns_prepared_row_count() -> None:
    assert upsert_account_features(FakeEngine(), _features()) == 1


def test_upsert_account_feature_failures_raise_feature_persistence_error() -> None:
    with pytest.raises(FeaturePersistenceError):
        upsert_account_features(FakeEngine(fail=True), _features())
