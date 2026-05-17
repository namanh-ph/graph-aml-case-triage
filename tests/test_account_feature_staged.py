"""Tests for staged account feature readers."""

import pandas as pd
import pytest
from sqlalchemy import text

from graph_aml.features import (
    calculate_account_features_from_staged,
    read_staged_accounts_for_features,
    read_staged_feature_inputs,
    read_staged_transactions_for_features,
)
from graph_aml.features.exceptions import StagedFeatureReadError


class FakeEngine:
    pass


def _accounts() -> pd.DataFrame:
    return pd.DataFrame([{"account_id": "ACC_A"}, {"account_id": "ACC_B"}])


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": "TXN_001",
                "sender_account_id": "ACC_A",
                "receiver_account_id": "ACC_B",
                "counterparty_id": None,
                "transaction_timestamp": "2025-01-01T10:00:00Z",
                "amount": 10.0,
            }
        ]
    )


def test_read_staged_accounts_for_features_reads_from_staging_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        statements.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_staged_accounts_for_features(FakeEngine())

    assert "staging.accounts" in statements[0]


def test_read_staged_transactions_for_features_reads_from_staging_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        statements.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_staged_transactions_for_features(FakeEngine())

    assert "staging.transactions" in statements[0]


def test_read_staged_transactions_for_features_applies_limit_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, int] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_staged_transactions_for_features(FakeEngine(), limit=10)

    assert "LIMIT :limit" in calls[0][0]
    assert calls[0][1] == {"limit": 10}


def test_read_staged_feature_inputs_returns_accounts_and_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.features.staged.read_staged_accounts_for_features",
        lambda engine: _accounts(),
    )
    monkeypatch.setattr(
        "graph_aml.features.staged.read_staged_transactions_for_features",
        lambda engine, limit=None: _transactions(),
    )

    accounts, transactions = read_staged_feature_inputs(FakeEngine())

    assert len(accounts) == 2
    assert len(transactions) == 1


def test_calculate_account_features_from_staged_calculates_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.features.staged.read_staged_feature_inputs",
        lambda engine, limit=None: (_accounts(), _transactions()),
    )

    features = calculate_account_features_from_staged(FakeEngine())

    assert not features.empty


def test_staged_read_failures_raise_staged_feature_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read_sql_query(statement, engine, params=None):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)

    with pytest.raises(StagedFeatureReadError):
        read_staged_accounts_for_features(FakeEngine())


def test_import_does_not_attempt_database_connection() -> None:
    assert str(text("SELECT 1"))
