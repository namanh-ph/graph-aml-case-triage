"""Tests for alert persistence preparation and upsert."""

from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.alerts import (
    ALERT_COLUMNS,
    AlertPersistenceError,
    create_alert_record,
    prepare_alerts_for_persistence,
    upsert_alerts,
)


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


def _alert():
    return create_alert_record(
        "AL_001",
        "ACC_001",
        "CUST_001",
        "Structuring",
        "structuring",
        "high",
        80,
        "STRUCTURING",
        ["TXN_001"],
        "2025-01-01T00:00:00Z",
        "2025-01-02T00:00:00Z",
    )


def _frame() -> pd.DataFrame:
    return prepare_alerts_for_persistence([_alert()])


def test_prepare_alerts_for_persistence_returns_alert_columns() -> None:
    assert tuple(prepare_alerts_for_persistence([_alert()]).columns) == ALERT_COLUMNS


def test_prepare_alerts_for_persistence_accepts_alert_records() -> None:
    assert len(prepare_alerts_for_persistence([_alert()])) == 1


def test_prepare_alerts_for_persistence_accepts_alert_dataframes() -> None:
    assert len(prepare_alerts_for_persistence(_frame())) == 1


def test_prepare_alerts_for_persistence_converts_evidence_ids_for_postgresql() -> None:
    prepared = prepare_alerts_for_persistence([_alert()])

    assert prepared.loc[0, "evidence_ids"] == ["TXN_001"]


def test_upsert_alerts_returns_zero_for_empty_alerts() -> None:
    assert upsert_alerts(FakeEngine(), []) == 0


def test_upsert_alerts_builds_sql_targeting_aml_alerts() -> None:
    engine = FakeEngine()

    upsert_alerts(engine, [_alert()])

    assert "INSERT INTO aml.alerts" in engine.connection.executions[0][0]


def test_upsert_alerts_sql_contains_on_conflict() -> None:
    engine = FakeEngine()

    upsert_alerts(engine, [_alert()])

    assert "ON CONFLICT" in engine.connection.executions[0][0]


def test_upsert_alerts_conflict_key_is_alert_id() -> None:
    engine = FakeEngine()

    upsert_alerts(engine, [_alert()])

    assert "ON CONFLICT (alert_id)" in engine.connection.executions[0][0]


def test_upsert_alerts_updates_non_key_columns_on_conflict() -> None:
    engine = FakeEngine()

    upsert_alerts(engine, [_alert()])

    assert "risk_score_rule = EXCLUDED.risk_score_rule" in engine.connection.executions[0][0]


def test_upsert_alerts_uses_bound_parameters() -> None:
    engine = FakeEngine()

    upsert_alerts(engine, [_alert()])

    params = engine.connection.executions[0][1]
    assert isinstance(params, list)
    assert params[0]["alert_id"] == "AL_001"


def test_upsert_alerts_returns_prepared_row_count() -> None:
    assert upsert_alerts(FakeEngine(), [_alert()]) == 1


def test_upsert_failures_raise_alert_persistence_error() -> None:
    with pytest.raises(AlertPersistenceError):
        upsert_alerts(FakeEngine(fail=True), [_alert()])
