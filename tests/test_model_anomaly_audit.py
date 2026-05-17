"""Tests for anomaly score audit event writing."""

import pytest

from graph_aml.models import (
    AnomalyScorePersistenceResult,
    ModelPersistenceError,
    write_anomaly_score_persistence_audit_event,
)


class FakeConnection:
    def __init__(self) -> None:
        self.statement: object | None = None
        self.params: dict[str, object] | None = None

    def execute(self, statement: object, params: dict[str, object]) -> None:
        self.statement = statement
        self.params = params


class FakeBegin:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, *args: object) -> None:
        return None


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self) -> FakeBegin:
        return FakeBegin(self.connection)


def test_audit_writer_inserts_expected_event_details() -> None:
    engine = FakeEngine()
    result = AnomalyScorePersistenceResult(
        rows_prepared=3,
        rows_persisted=3,
        unique_account_count=3,
        model_version="v1",
        model_run_id="run1",
    )
    write_anomaly_score_persistence_audit_event(engine, result)
    assert "governance.audit_events" in str(engine.connection.statement)
    assert engine.connection.params is not None
    assert engine.connection.params["event_type"] == "model_scoring"
    assert engine.connection.params["component"] == "models"
    assert engine.connection.params["action"] == "persist_account_anomaly_scores"
    details = str(engine.connection.params["details"])
    assert "rows_prepared" in details
    assert "rows_persisted" in details
    assert "model_version" in details
    assert "model_run_id" in details


def test_audit_failures_raise() -> None:
    class BrokenEngine:
        def begin(self) -> object:
            raise RuntimeError("boom")

    with pytest.raises(ModelPersistenceError):
        write_anomaly_score_persistence_audit_event(
            BrokenEngine(),
            AnomalyScorePersistenceResult(),
        )
