"""Tests for staging audit event writing."""

import json

import pytest

from graph_aml.staging import StagingAuditError, write_staging_audit_event


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.executions: list[tuple[str, dict[str, object]]] = []

    def __enter__(self) -> "FakeConnection":
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


def test_write_staging_audit_event_inserts_into_governance_audit_events() -> None:
    engine = FakeEngine()

    write_staging_audit_event(engine, {"transactions": 10}, "completed")

    assert "INSERT INTO governance.audit_events" in engine.connection.executions[0][0]


def test_audit_event_uses_event_type_staging_transformation() -> None:
    engine = FakeEngine()

    write_staging_audit_event(engine, {"transactions": 10}, "completed")

    assert engine.connection.executions[0][1]["event_type"] == "staging_transformation"


def test_audit_event_uses_component_staging() -> None:
    engine = FakeEngine()

    write_staging_audit_event(engine, {"transactions": 10}, "completed")

    assert engine.connection.executions[0][1]["component"] == "staging"


def test_audit_event_uses_action_transform_raw_to_staging() -> None:
    engine = FakeEngine()

    write_staging_audit_event(engine, {"transactions": 10}, "completed")

    assert engine.connection.executions[0][1]["action"] == "transform_raw_to_staging"


def test_audit_details_include_row_counts() -> None:
    engine = FakeEngine()

    write_staging_audit_event(engine, {"transactions": 10}, "completed")

    details = json.loads(str(engine.connection.executions[0][1]["details"]))
    assert details["row_counts"] == {"transactions": 10}


def test_audit_failures_raise_staging_audit_error() -> None:
    with pytest.raises(StagingAuditError):
        write_staging_audit_event(FakeEngine(fail=True), {"transactions": 10}, "failed")
