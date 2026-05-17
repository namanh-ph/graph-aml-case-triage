"""Tests for AML rule execution audit events."""

import pytest

from graph_aml.rules import RuleAuditError, write_rule_execution_audit_event


class FakeConnection:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.executions: list[tuple[str, object]] = []

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: object, parameters: object | None = None) -> None:
        if self.fail:
            raise RuntimeError("audit failed")
        self.executions.append((str(statement), parameters))


class FakeEngine:
    def __init__(self, fail: bool = False) -> None:
        self.connection = FakeConnection(fail=fail)

    def begin(self) -> FakeConnection:
        return self.connection


def test_rule_audit_inserts_into_governance_audit_events() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(engine, "Structuring", 2, 2, "completed")

    assert "INSERT INTO governance.audit_events" in engine.connection.executions[0][0]


def test_rule_audit_event_uses_rule_execution_event_type() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(engine, "Structuring", 2, 2, "completed")

    params = engine.connection.executions[0][1]
    assert params["event_type"] == "rule_execution"


def test_rule_audit_event_uses_rules_component() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(engine, "Structuring", 2, 2, "completed")

    params = engine.connection.executions[0][1]
    assert params["component"] == "rules"


def test_rule_audit_event_uses_run_structuring_rule_action() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(engine, "Structuring", 2, 2, "completed")

    params = engine.connection.executions[0][1]
    assert params["action"] == "run_structuring_rule"


def test_rule_audit_accepts_custom_action() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(
        engine,
        "Fan-in",
        2,
        2,
        "completed",
        action="run_fan_in_rule",
    )

    params = engine.connection.executions[0][1]
    assert params["action"] == "run_fan_in_rule"


def test_rule_audit_accepts_fan_out_action() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(
        engine,
        "Fan-out",
        2,
        2,
        "completed",
        action="run_fan_out_rule",
    )

    params = engine.connection.executions[0][1]
    assert params["action"] == "run_fan_out_rule"


def test_rule_audit_accepts_rapid_movement_action() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(
        engine,
        "Rapid movement",
        2,
        2,
        "completed",
        action="run_rapid_movement_rule",
    )

    params = engine.connection.executions[0][1]
    assert params["action"] == "run_rapid_movement_rule"


def test_rule_audit_accepts_dormant_reactivation_action() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(
        engine,
        "Dormant reactivation",
        2,
        2,
        "completed",
        action="run_dormant_reactivation_rule",
    )

    params = engine.connection.executions[0][1]
    assert params["action"] == "run_dormant_reactivation_rule"


def test_rule_audit_accepts_circular_flow_detection_action() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(
        engine,
        "Circular flow",
        0,
        0,
        "completed",
        action="detect_circular_flows",
    )

    params = engine.connection.executions[0][1]
    assert params["action"] == "detect_circular_flows"


def test_rule_audit_accepts_circular_flow_rule_action() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(
        engine,
        "Circular flow",
        2,
        2,
        "completed",
        action="run_circular_flow_rule",
    )

    params = engine.connection.executions[0][1]
    assert params["action"] == "run_circular_flow_rule"


def test_rule_audit_details_include_counts_and_metadata() -> None:
    engine = FakeEngine()

    write_rule_execution_audit_event(
        engine,
        "Structuring",
        2,
        1,
        "completed",
        metadata={"threshold": 10000},
    )

    params = engine.connection.executions[0][1]
    assert '"rule_name": "Structuring"' in params["details"]
    assert '"alerts_generated": 2' in params["details"]
    assert '"alerts_persisted": 1' in params["details"]
    assert '"threshold": 10000' in params["details"]


def test_rule_audit_failures_raise_rule_audit_error() -> None:
    with pytest.raises(RuleAuditError):
        write_rule_execution_audit_event(FakeEngine(fail=True), "Structuring", 2, 2, "failed")
