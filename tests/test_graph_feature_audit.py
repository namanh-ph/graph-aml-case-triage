"""Tests for graph feature persistence audit events."""

import json

import pytest

from graph_aml.graph import (
    GraphFeaturePersistenceError,
    GraphFeaturePersistenceResult,
    write_graph_feature_persistence_audit_event,
)


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


def _result() -> GraphFeaturePersistenceResult:
    return GraphFeaturePersistenceResult(
        rows_prepared=2,
        rows_persisted=2,
        unique_account_count=2,
        feature_version="graph_features_v1",
        graph_build_id="build_1",
        metadata={"job": "unit"},
    )


def _write(engine: FakeEngine) -> dict[str, object]:
    write_graph_feature_persistence_audit_event(engine, _result())
    return engine.connection.executions[0][1]


def test_graph_feature_audit_inserts_into_governance_audit_events() -> None:
    engine = FakeEngine()

    _write(engine)

    assert "INSERT INTO governance.audit_events" in engine.connection.executions[0][0]


def test_graph_feature_audit_event_fields_and_details() -> None:
    params = _write(FakeEngine())
    details = json.loads(str(params["details"]))

    assert params["event_type"] == "graph_feature_persistence"
    assert params["component"] == "graph"
    assert params["action"] == "persist_graph_features"
    assert details["rows_prepared"] == 2
    assert details["rows_persisted"] == 2
    assert details["feature_version"] == "graph_features_v1"
    assert details["graph_build_id"] == "build_1"


def test_graph_feature_audit_failures_raise() -> None:
    with pytest.raises(GraphFeaturePersistenceError):
        _write(FakeEngine(fail=True))
