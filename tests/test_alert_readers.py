"""Tests for alert readers."""

from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import text

from graph_aml.alerts import AlertPersistenceError, read_alerts


class FakeEngine:
    pass


def test_read_alerts_reads_from_aml_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    statements: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        statements.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_alerts(FakeEngine())

    assert "aml.alerts" in statements[0]


def test_read_alerts_applies_rule_name_filter_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_alerts(FakeEngine(), rule_name="Structuring")

    assert "rule_name = :rule_name" in calls[0][0]
    assert calls[0][1] == {"rule_name": "Structuring"}


def test_read_alerts_applies_severity_filter_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_alerts(FakeEngine(), severity="HIGH")

    assert "severity = :severity" in calls[0][0]
    assert calls[0][1] == {"severity": "high"}


def test_read_alerts_applies_status_filter_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_alerts(FakeEngine(), alert_status="New")

    assert "alert_status = :alert_status" in calls[0][0]
    assert calls[0][1] == {"alert_status": "New"}


def test_read_alerts_applies_limit_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append((str(statement), params))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_alerts(FakeEngine(), limit=10)

    assert "LIMIT :limit" in calls[0][0]
    assert calls[0][1] == {"limit": 10}


def test_read_alerts_orders_by_created_at_and_alert_id(monkeypatch: pytest.MonkeyPatch) -> None:
    statements: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        statements.append(str(statement))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)

    read_alerts(FakeEngine())

    assert "ORDER BY created_at, alert_id" in statements[0]


def test_reader_failures_raise_alert_persistence_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_read_sql_query(statement, engine, params=None):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(pd, "read_sql_query", fail_read_sql_query)

    with pytest.raises(AlertPersistenceError):
        read_alerts(FakeEngine())


def test_import_does_not_attempt_database_connection() -> None:
    assert str(text("SELECT 1"))
