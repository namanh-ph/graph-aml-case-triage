"""Tests for unified rule engine audit events."""

import json

import pytest

from graph_aml.rules import RuleAuditError, write_rule_engine_audit_event


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


def _write_event(engine: FakeEngine) -> dict[str, object]:
    write_rule_engine_audit_event(
        engine,
        rules_run=("structuring", "fan_in"),
        alerts_generated=3,
        alerts_persisted=2,
        status="completed",
        metadata={"persisted": True},
    )
    return engine.connection.executions[0][1]


def test_rule_engine_audit_inserts_into_governance_audit_events() -> None:
    engine = FakeEngine()

    _write_event(engine)

    assert "INSERT INTO governance.audit_events" in engine.connection.executions[0][0]


def test_audit_event_uses_rule_engine_execution_event_type() -> None:
    assert _write_event(FakeEngine())["event_type"] == "rule_engine_execution"


def test_audit_event_uses_rules_component() -> None:
    assert _write_event(FakeEngine())["component"] == "rules"


def test_audit_event_uses_run_aml_rule_engine_action() -> None:
    assert _write_event(FakeEngine())["action"] == "run_aml_rule_engine"


def test_audit_details_include_rules_run() -> None:
    details = json.loads(str(_write_event(FakeEngine())["details"]))

    assert details["rules_run"] == ["structuring", "fan_in"]


def test_audit_details_include_alerts_generated() -> None:
    details = json.loads(str(_write_event(FakeEngine())["details"]))

    assert details["alerts_generated"] == 3


def test_audit_details_include_alerts_persisted() -> None:
    details = json.loads(str(_write_event(FakeEngine())["details"]))

    assert details["alerts_persisted"] == 2


def test_audit_details_include_metadata() -> None:
    details = json.loads(str(_write_event(FakeEngine())["details"]))

    assert details["metadata"]["persisted"] is True


def test_audit_failures_raise_rule_audit_error() -> None:
    with pytest.raises(RuleAuditError):
        _write_event(FakeEngine(fail=True))
