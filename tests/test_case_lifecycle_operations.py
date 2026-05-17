"""Tests for high-level lifecycle operations."""

import pytest

from graph_aml.cases import add_case_comment, assign_case, change_case_status
from graph_aml.cases.lifecycle_persistence import CaseLifecyclePersistenceResult


def test_change_case_status_reads_status_and_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "graph_aml.cases.lifecycle_readers.read_case_current_status",
        lambda engine, case_id: calls.append(case_id) or "New",
        raising=False,
    )

    def fake_apply(engine, action, config=None):  # noqa: ANN001
        assert action.from_status == "New"
        assert action.to_status == "In review"
        return CaseLifecyclePersistenceResult(case_id=action.case_id, persisted=True)

    monkeypatch.setattr(
        "graph_aml.cases.lifecycle_persistence.apply_case_lifecycle_action",
        fake_apply,
    )
    result = change_case_status(
        object(),
        "CASE1",
        "In review",
        decision_reason="Start review",
    )
    assert result.persisted
    assert calls == ["CASE1"]


def test_assign_and_comment_operations_persist(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_apply(engine, action, config=None):  # noqa: ANN001
        seen.append(action.action_type)
        return CaseLifecyclePersistenceResult(case_id=action.case_id, persisted=True)

    monkeypatch.setattr(
        "graph_aml.cases.lifecycle_persistence.apply_case_lifecycle_action",
        fake_apply,
    )
    assert assign_case(object(), "CASE1", "analyst").persisted
    assert add_case_comment(object(), "CASE1", comment="Reviewed").persisted
    assert seen == ["assign", "comment"]


def test_operations_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    monkeypatch.setattr(
        "graph_aml.cases.lifecycle_persistence.apply_case_lifecycle_action",
        lambda engine, action, config=None: CaseLifecyclePersistenceResult(persisted=True),
        raising=False,
    )
    assign_case(object(), "CASE1", "analyst")
