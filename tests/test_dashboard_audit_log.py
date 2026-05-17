"""Tests for dashboard audit log readers and helpers."""

import json

import pandas as pd
import pytest
from sqlalchemy.sql.elements import TextClause

from graph_aml.dashboard.audit_components import (
    build_audit_event_summary,
    flatten_audit_details_for_display,
)
from graph_aml.dashboard.audit_data import (
    read_dashboard_audit_events,
    read_dashboard_audit_filter_options,
    read_dashboard_audit_summary,
)
from graph_aml.dashboard.exceptions import DashboardDataError


def test_audit_readers_query_expected_table_and_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read(
        sql: TextClause,
        engine: object,
        params: dict[str, object] | None = None,
    ) -> pd.DataFrame:
        calls.append((str(sql), params))
        text = str(sql)
        if "SELECT DISTINCT component" in text:
            return pd.DataFrame({"component": ["rules"]})
        if "SELECT DISTINCT event_type" in text:
            return pd.DataFrame({"event_type": ["rule_engine"]})
        if "SELECT DISTINCT status" in text:
            return pd.DataFrame({"status": ["success"]})
        return pd.DataFrame(
            {
                "audit_event_id": [1],
                "event_type": ["rule_engine"],
                "component": ["rules"],
                "action": ["run"],
                "status": ["success"],
                "run_id": ["RUN1"],
                "details": [{"rows": 1}],
                "event_timestamp": ["2026-01-01"],
            }
        )

    monkeypatch.setattr("graph_aml.dashboard.audit_data.pd.read_sql_query", fake_read)
    engine = object()

    events = read_dashboard_audit_events(
        engine,  # type: ignore[arg-type]
        components=["rules"],
        event_types=["rule_engine"],
        statuses=["success"],
        run_id="RUN1",
        search_text="run",
        limit=5,
    )
    options = read_dashboard_audit_filter_options(engine)  # type: ignore[arg-type]
    summary = read_dashboard_audit_summary(engine)  # type: ignore[arg-type]

    all_sql = "\n".join(sql for sql, _ in calls)
    assert "governance.audit_events" in all_sql
    assert "details::text ILIKE" in all_sql
    assert any(params and params.get("components") == ["rules"] for _, params in calls)
    assert any(params and params.get("event_types") == ["rule_engine"] for _, params in calls)
    assert any(params and params.get("statuses") == ["success"] for _, params in calls)
    assert any(params and params.get("run_id") == "RUN1" for _, params in calls)
    assert not events.empty
    assert options["components"] == ["rules"]
    json.dumps(summary, default=str)


def test_audit_helpers_build_counts_and_flatten_details() -> None:
    events = pd.DataFrame(
        {
            "component": ["rules", "models"],
            "event_type": ["rule", "model"],
            "status": ["success", "failed"],
            "details": [{"a": 1}, {"b": 2}],
            "event_timestamp": ["2026-01-01", "2026-01-02"],
        }
    )

    summary = build_audit_event_summary(events)
    flat = flatten_audit_details_for_display(events)

    assert summary["event_count"] == 2
    assert summary["failure_count"] == 1
    assert isinstance(flat.iloc[0]["details"], str)


def test_audit_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.dashboard.audit_data.pd.read_sql_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(DashboardDataError):
        read_dashboard_audit_events(object())  # type: ignore[arg-type]
