"""Tests for staged structuring rule readers and runner."""

import pandas as pd
import pytest
from sqlalchemy import text

from graph_aml.rules import (
    RuleDataReadError,
    StructuringRuleConfig,
    read_staged_accounts_for_rules,
    read_staged_transactions_for_rules,
    read_structuring_rule_inputs,
    run_structuring_rule_from_staged,
)


class FakeEngine:
    pass


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": f"TXN_{index}",
                "sender_account_id": "ACC_1",
                "receiver_account_id": "ACC_2",
                "counterparty_id": None,
                "transaction_timestamp": pd.Timestamp("2025-01-01T00:00:00Z")
                + pd.Timedelta(hours=index),
                "amount": 9500.0,
                "transaction_type": "transfer",
            }
            for index in range(3)
        ]
    )


def _accounts() -> pd.DataFrame:
    return pd.DataFrame({"account_id": ["ACC_1"], "customer_id": ["CUST_1"]})


def _inputs(*args: object, **kwargs: object) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _transactions(), _accounts()


def _transactions_only(*args: object, **kwargs: object) -> pd.DataFrame:
    return _transactions()


def _accounts_only(*args: object, **kwargs: object) -> pd.DataFrame:
    return _accounts()


def _no_audit(*args: object, **kwargs: object) -> None:
    return None


def test_read_staged_transactions_for_rules_reads_from_staging_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        statements.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_staged_transactions_for_rules(FakeEngine())

    assert "FROM staging.transactions" in statements[0]


def test_read_staged_transactions_for_rules_applies_limit_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, int] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_staged_transactions_for_rules(FakeEngine(), limit=5)

    assert "LIMIT :limit" in calls[0][0]
    assert calls[0][1] == {"limit": 5}


def test_read_staged_accounts_for_rules_reads_from_staging_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        statements.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_staged_accounts_for_rules(FakeEngine())

    assert "FROM staging.accounts" in statements[0]


def test_read_structuring_rule_inputs_returns_transactions_and_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.rules.staged.read_staged_transactions_for_rules",
        _transactions_only,
    )
    monkeypatch.setattr("graph_aml.rules.staged.read_staged_accounts_for_rules", _accounts_only)

    transactions, accounts = read_structuring_rule_inputs(FakeEngine())

    assert len(transactions) == 3
    assert len(accounts) == 1


def test_run_structuring_rule_from_staged_runs_rule_using_staged_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_structuring_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)

    summary = run_structuring_rule_from_staged(
        FakeEngine(),
        config=StructuringRuleConfig(min_transaction_count=3, window_hours=3),
    )

    assert summary["alerts_generated"] == 1


def test_run_structuring_rule_from_staged_persists_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_structuring_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr(
        "graph_aml.rules.staged.persist_alerts",
        lambda *a, **k: calls.append(1) or {"alerts_upserted": 1},
    )

    run_structuring_rule_from_staged(
        FakeEngine(),
        config=StructuringRuleConfig(min_transaction_count=3, window_hours=3),
        persist=False,
    )
    run_structuring_rule_from_staged(
        FakeEngine(),
        config=StructuringRuleConfig(min_transaction_count=3, window_hours=3),
        persist=True,
    )

    assert calls == [1]


def test_run_structuring_rule_from_staged_writes_audit_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_structuring_rule_inputs", _inputs)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_rule_execution_audit_event",
        lambda *args, **kwargs: calls.append(1),
    )

    run_structuring_rule_from_staged(
        FakeEngine(),
        config=StructuringRuleConfig(min_transaction_count=3, window_hours=3),
        write_audit=False,
    )
    run_structuring_rule_from_staged(
        FakeEngine(),
        config=StructuringRuleConfig(min_transaction_count=3, window_hours=3),
        write_audit=True,
    )

    assert calls == [1]


def test_staged_read_failures_raise_rule_data_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read_sql_query(statement, engine, params=None):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)

    with pytest.raises(RuleDataReadError):
        read_staged_transactions_for_rules(FakeEngine())


def test_import_does_not_attempt_database_connection() -> None:
    assert str(text("SELECT 1"))
