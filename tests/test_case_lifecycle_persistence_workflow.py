"""Tests for lifecycle persistence workflow."""

from datetime import UTC, datetime

import pytest

from graph_aml.cases import (
    CaseLifecycleAction,
    CaseLifecyclePersistenceConfig,
    CaseLifecyclePersistenceError,
    CaseLifecyclePersistenceResult,
    apply_case_lifecycle_action,
    insert_case_lifecycle_event,
    update_case_status_snapshot,
    upsert_case_assignment,
    validate_case_lifecycle_persistence_config,
    write_case_lifecycle_audit_event,
)


class FakeConnection:
    def __init__(self) -> None:
        self.executions: list[tuple[object, object]] = []

    def execute(self, statement, params=None):  # noqa: ANN001
        self.executions.append((statement, params))


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self):
        engine = self

        class Context:
            def __enter__(self_inner):
                return engine.connection

            def __exit__(self_inner, exc_type, exc, tb):  # noqa: ANN001
                return False

        return Context()


def action(**overrides) -> CaseLifecycleAction:
    payload = {
        "case_id": "CASE1",
        "action_type": "status_change",
        "analyst_id": "analyst",
        "from_status": "New",
        "to_status": "In review",
        "decision_reason": "Start review",
        "action_timestamp": datetime(2026, 1, 1, tzinfo=UTC),
    }
    payload.update(overrides)
    return CaseLifecycleAction(**payload)


def test_persistence_config_validation() -> None:
    validate_case_lifecycle_persistence_config(CaseLifecyclePersistenceConfig())
    with pytest.raises(CaseLifecyclePersistenceError):
        CaseLifecyclePersistenceConfig(lifecycle_version="")
    with pytest.raises(CaseLifecyclePersistenceError):
        CaseLifecyclePersistenceConfig(write_audit="yes")  # type: ignore[arg-type]


def test_insert_update_and_assignment_return_counts() -> None:
    engine = FakeEngine()
    record = {
        "action_id": "ACT1",
        "case_id": "CASE1",
        "action_type": "assign",
        "analyst_id": "lead",
        "from_status": None,
        "to_status": None,
        "assigned_to": "analyst",
        "queue": "AML Review",
        "decision_reason": None,
        "comment": None,
        "metadata": {},
        "action_timestamp": datetime(2026, 1, 1, tzinfo=UTC),
    }
    assert insert_case_lifecycle_event(engine, record) == 1
    assert update_case_status_snapshot(engine, record) == 0
    assert upsert_case_assignment(engine, record) == 1


def test_apply_action_returns_result_and_skips_audit() -> None:
    engine = FakeEngine()
    result = apply_case_lifecycle_action(
        engine,
        action(),
        persistence_config=CaseLifecyclePersistenceConfig(write_audit=False),
    )
    assert isinstance(result, CaseLifecyclePersistenceResult)
    assert result.persisted
    assert result.case_updated


def test_audit_writer_inserts_audit_event() -> None:
    engine = FakeEngine()
    write_case_lifecycle_audit_event(
        engine,
        CaseLifecyclePersistenceResult(
            action_id="A1",
            case_id="CASE1",
            action_type="comment",
            analyst_id="analyst",
        ),
    )
    statement, params = engine.connection.executions[0]
    assert "governance.audit_events" in str(statement)
    assert params["event_type"] == "case_lifecycle_action"


def test_persistence_functions_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    apply_case_lifecycle_action(
        FakeEngine(),
        action(),
        persistence_config=CaseLifecyclePersistenceConfig(write_audit=False),
    )
