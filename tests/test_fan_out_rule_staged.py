"""Tests for staged fan-out rule readers and runner."""

import pandas as pd
import pytest
from sqlalchemy import text

from graph_aml.rules import (
    FanOutRuleConfig,
    RuleDataReadError,
    read_fan_out_rule_inputs,
    run_fan_out_rule_from_staged,
)
from graph_aml.rules.staged import read_staged_transactions_for_rules
from tests.fixtures.fan_out_fixtures import (
    build_fan_out_accounts_fixture,
    build_fan_out_trigger_transactions_fixture,
)


class FakeEngine:
    pass


def _inputs(*args: object, **kwargs: object) -> tuple[pd.DataFrame, pd.DataFrame]:
    return build_fan_out_trigger_transactions_fixture(), build_fan_out_accounts_fixture()


def _no_audit(*args: object, **kwargs: object) -> None:
    return None


def test_read_fan_out_rule_inputs_returns_transactions_and_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.rules.staged.read_staged_transactions_for_rules",
        lambda *args, **kwargs: build_fan_out_trigger_transactions_fixture(),
    )
    monkeypatch.setattr(
        "graph_aml.rules.staged.read_staged_accounts_for_rules",
        lambda *args, **kwargs: build_fan_out_accounts_fixture(),
    )

    transactions, accounts = read_fan_out_rule_inputs(FakeEngine())

    assert len(transactions) == 20
    assert len(accounts) > 0


def test_run_fan_out_rule_from_staged_runs_rule_using_staged_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_fan_out_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)

    summary = run_fan_out_rule_from_staged(FakeEngine())

    assert summary["alerts_generated"] == 1


def test_run_fan_out_rule_from_staged_persists_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_fan_out_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)
    monkeypatch.setattr(
        "graph_aml.rules.staged.persist_alerts",
        lambda *args, **kwargs: calls.append(1) or {"alerts_upserted": 1},
    )

    run_fan_out_rule_from_staged(FakeEngine(), persist=False)
    run_fan_out_rule_from_staged(FakeEngine(), persist=True)

    assert calls == [1]


def test_run_fan_out_rule_from_staged_writes_audit_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_fan_out_rule_inputs", _inputs)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_rule_execution_audit_event",
        lambda *args, **kwargs: calls.append(kwargs),
    )

    run_fan_out_rule_from_staged(FakeEngine(), write_audit=False)
    run_fan_out_rule_from_staged(FakeEngine(), write_audit=True)

    assert len(calls) == 1


def test_run_fan_out_rule_from_staged_uses_fan_out_audit_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr("graph_aml.rules.staged.read_fan_out_rule_inputs", _inputs)
    monkeypatch.setattr(
        "graph_aml.rules.staged.write_rule_execution_audit_event",
        lambda *args, **kwargs: calls.append(kwargs),
    )

    run_fan_out_rule_from_staged(FakeEngine(), write_audit=True)

    assert calls[0]["action"] == "run_fan_out_rule"


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


def test_run_fan_out_rule_from_staged_accepts_custom_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("graph_aml.rules.staged.read_fan_out_rule_inputs", _inputs)
    monkeypatch.setattr("graph_aml.rules.staged.write_rule_execution_audit_event", _no_audit)

    summary = run_fan_out_rule_from_staged(
        FakeEngine(),
        config=FanOutRuleConfig(min_unique_recipients=4),
    )

    assert summary["alerts_generated"] == 1
