"""Tests for case lifecycle readers."""

import json

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseLifecyclePersistenceError,
    read_case_assignments,
    read_case_current_status,
    read_case_lifecycle_events,
    read_case_lifecycle_summary,
)


class FakeEngine:
    pass


def test_current_status_reader_queries_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_read(sql, engine, params=None):  # noqa: ANN001
        captured["sql"] = str(sql)
        captured["params"] = params
        return pd.DataFrame({"status": ["New"]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    assert read_case_current_status(FakeEngine(), "CASE1") == "New"
    assert "aml.cases" in captured["sql"]
    assert captured["params"]["case_id"] == "CASE1"


def test_event_reader_filters_and_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_read(sql, engine, params=None):  # noqa: ANN001
        captured["sql"] = str(sql)
        captured["params"] = params
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    read_case_lifecycle_events(
        FakeEngine(),
        case_id="CASE1",
        analyst_id="analyst",
        action_type="comment",
        limit=10,
    )
    assert "aml.case_lifecycle_events" in captured["sql"]
    assert "ORDER BY action_timestamp DESC" in captured["sql"]
    assert captured["params"]["limit"] == 10


def test_assignment_reader_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        pd,
        "read_sql_query",
        lambda sql, engine, params=None: (
            captured.setdefault("sql", str(sql))
            or captured.setdefault("params", params)
            or pd.DataFrame()
        ),
    )
    read_case_assignments(FakeEngine(), assigned_to="analyst", queue="AML Review", limit=5)
    assert "aml.case_assignments" in captured["sql"]


def test_summary_reader_returns_json_serialisable(monkeypatch: pytest.MonkeyPatch) -> None:
    frames = [
        pd.DataFrame(
            {
                "lifecycle_event_count": [1],
                "lifecycle_case_count": [1],
                "latest_action_timestamp": ["2026-01-01"],
            }
        ),
        pd.DataFrame({"assigned_case_count": [1]}),
        pd.DataFrame({"action_type": ["comment"], "count": [1]}),
        pd.DataFrame({"analyst_id": ["analyst"], "count": [1]}),
        pd.DataFrame({"status": ["New"], "count": [1]}),
    ]
    monkeypatch.setattr(pd, "read_sql_query", lambda *args, **kwargs: frames.pop(0))
    summary = read_case_lifecycle_summary(FakeEngine())
    json.dumps(summary)
    assert summary["lifecycle_event_count"] == 1


def test_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd,
        "read_sql_query",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(CaseLifecyclePersistenceError):
        read_case_lifecycle_events(FakeEngine())
