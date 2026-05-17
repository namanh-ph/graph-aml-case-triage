"""Tests for dashboard lifecycle action adapters."""

from dataclasses import dataclass, field

import pytest

from graph_aml.dashboard.exceptions import DashboardActionError
from graph_aml.dashboard.lifecycle_actions import (
    require_dashboard_action_allowed,
    submit_dashboard_assignment,
    submit_dashboard_comment,
    submit_dashboard_status_change,
)
from graph_aml.security import SecurityControlConfig


@dataclass(frozen=True)
class FakeResult:
    action_id: str = "ACT1"
    case_id: str = "CASE1"
    action_type: str = "status_change"
    persisted: bool = True
    metadata: dict[str, object] = field(default_factory=dict)


def test_status_change_adapter_calls_case_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_change(*args: object, **kwargs: object) -> FakeResult:
        called["args"] = args
        called["kwargs"] = kwargs
        return FakeResult()

    monkeypatch.setattr("graph_aml.dashboard.lifecycle_actions.change_case_status", fake_change)

    result = submit_dashboard_status_change(object(), "CASE1", "In review", "analyst")

    assert result["action_id"] == "ACT1"
    assert called["args"][1:4] == ("CASE1", "In review")


def test_assignment_and_comment_adapters_call_case_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "graph_aml.dashboard.lifecycle_actions.assign_case",
        lambda *_args, **_kwargs: FakeResult(action_type="assign"),
    )
    monkeypatch.setattr(
        "graph_aml.dashboard.lifecycle_actions.add_case_comment",
        lambda *_args, **_kwargs: FakeResult(action_type="comment"),
    )

    assert (
        submit_dashboard_assignment(object(), "CASE1", "analyst2", "analyst")["action_type"]
        == "assign"
    )
    assert (
        submit_dashboard_comment(object(), "CASE1", "analyst", "Reviewed")["action_type"]
        == "comment"
    )


def test_adapters_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.dashboard.lifecycle_actions.change_case_status",
        lambda *_args, **_kwargs: FakeResult(),
    )
    monkeypatch.setattr(
        "graph_aml.dashboard.database.create_dashboard_engine",
        lambda: (_ for _ in ()).throw(AssertionError("engine")),
    )

    assert (
        submit_dashboard_status_change(object(), "CASE1", "In review", "analyst")["persisted"]
        is True
    )


def test_lifecycle_failures_raise_dashboard_action_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> FakeResult:
        raise RuntimeError("boom")

    monkeypatch.setattr("graph_aml.dashboard.lifecycle_actions.change_case_status", fail)

    with pytest.raises(DashboardActionError):
        submit_dashboard_status_change(object(), "CASE1", "In review", "analyst")


def test_dashboard_action_authorisation_blocks_unauthorised_role() -> None:
    with pytest.raises(DashboardActionError):
        require_dashboard_action_allowed("viewer", "case_close", SecurityControlConfig())
