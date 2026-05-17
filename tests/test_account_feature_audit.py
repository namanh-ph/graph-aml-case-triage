"""Tests for account feature persistence audit events."""

from __future__ import annotations

import json

import pytest

from graph_aml.features import FeatureAuditError, write_feature_persistence_audit_event


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.executions: list[tuple[str, dict[str, object]]] = []

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object, parameters: dict[str, object]) -> None:
        if self.fail:
            raise RuntimeError("audit failed")
        self.executions.append((str(statement), parameters))


class FakeEngine:
    def __init__(self, fail: bool = False) -> None:
        self.connection = FakeConnection(fail=fail)

    def begin(self) -> FakeConnection:
        return self.connection


def _write(engine: FakeEngine) -> None:
    write_feature_persistence_audit_event(
        engine,
        row_count=10,
        account_count=2,
        feature_date_count=5,
        feature_version="account_features_v1",
        status="completed",
        metadata={"source": "unit-test"},
    )


def test_write_feature_persistence_audit_event_inserts_into_audit_events() -> None:
    engine = FakeEngine()

    _write(engine)

    assert "INSERT INTO governance.audit_events" in engine.connection.executions[0][0]


def test_feature_audit_event_uses_event_type_feature_persistence() -> None:
    engine = FakeEngine()

    _write(engine)

    assert engine.connection.executions[0][1]["event_type"] == "feature_persistence"


def test_feature_audit_event_uses_component_features() -> None:
    engine = FakeEngine()

    _write(engine)

    assert engine.connection.executions[0][1]["component"] == "features"


def test_feature_audit_event_uses_action_persist_account_features() -> None:
    engine = FakeEngine()

    _write(engine)

    assert engine.connection.executions[0][1]["action"] == "persist_account_features"


def test_feature_audit_details_include_counts_version_and_metadata() -> None:
    engine = FakeEngine()

    _write(engine)

    details = json.loads(str(engine.connection.executions[0][1]["details"]))
    assert details["row_count"] == 10
    assert details["account_count"] == 2
    assert details["feature_date_count"] == 5
    assert details["feature_version"] == "account_features_v1"
    assert details["metadata"] == {"source": "unit-test"}


def test_feature_audit_failures_raise_feature_audit_error() -> None:
    with pytest.raises(FeatureAuditError):
        _write(FakeEngine(fail=True))
