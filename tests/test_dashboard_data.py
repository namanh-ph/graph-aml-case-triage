"""Tests for dashboard database helpers and readers."""

from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy.sql.elements import TextClause

from graph_aml.dashboard.data import (
    read_dashboard_alert_queue,
    read_dashboard_case_detail,
    read_dashboard_case_evidence,
    read_dashboard_case_queue,
    read_dashboard_filter_options,
    read_dashboard_overview_counts,
)
from graph_aml.dashboard.database import check_dashboard_database_health
from graph_aml.dashboard.exceptions import DashboardDataError


class FakeResult:
    def mappings(self) -> FakeResult:
        return self

    def first(self) -> dict[str, int]:
        return {"ok": 1}


class FakeConnection:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, statement: TextClause) -> FakeResult:
        self.executed.append(str(statement))
        return FakeResult()


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def connect(self) -> FakeConnection:
        return self.connection


def test_dashboard_health_check_runs_simple_query() -> None:
    engine = FakeEngine()

    result = check_dashboard_database_health(engine)  # type: ignore[arg-type]

    assert result["status"] == "ok"
    assert "SELECT 1 AS ok" in engine.connection.executed[0]


def test_readers_query_expected_tables_and_use_params(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read_sql(
        sql: TextClause,
        engine: object,
        params: dict[str, object] | None = None,
    ) -> pd.DataFrame:
        calls.append((str(sql), params))
        text = str(sql)
        if "COUNT(*)" in text and "GROUP BY" not in text:
            return pd.DataFrame({"count": [1]})
        if "GROUP BY" in text:
            if "status" in text:
                return pd.DataFrame({"status": ["New"], "row_count": [1]})
            if "risk_band" in text:
                return pd.DataFrame({"risk_band": ["critical"], "row_count": [1]})
            if "severity" in text:
                return pd.DataFrame({"severity": ["high"], "row_count": [1]})
            return pd.DataFrame({"typology": ["fan-in"], "row_count": [1]})
        if "DISTINCT" in text:
            column = text.split("DISTINCT ", 1)[1].split(" ", 1)[0]
            return pd.DataFrame({column: ["x"]})
        if "aml.case_alerts" in text:
            return pd.DataFrame({"case_id": ["CASE1"], "alert_id": ["ALERT1"]})
        if "aml.alerts" in text:
            return pd.DataFrame(
                {"alert_id": ["ALERT1"], "severity": ["high"], "typology": ["fan-in"]}
            )
        if "aml.case_entities" in text:
            return pd.DataFrame(
                {"case_id": ["CASE1"], "entity_type": ["account"], "entity_id": ["A1"]}
            )
        if "aml.case_risk_scores" in text:
            return pd.DataFrame(
                {"case_id": ["CASE1"], "risk_band": ["critical"], "case_risk_score": [91.0]}
            )
        if "aml.case_lifecycle_events" in text:
            return pd.DataFrame({"case_id": ["CASE1"], "action_id": ["ACT1"]})
        if "aml.case_evidence_packs" in text:
            return pd.DataFrame({"case_id": ["CASE1"], "evidence_version": ["v1"]})
        if "aml.case_explanations" in text:
            return pd.DataFrame({"case_id": ["CASE1"], "explanation_version": ["v1"]})
        return pd.DataFrame({"case_id": ["CASE1"], "status": ["New"]})

    monkeypatch.setattr("graph_aml.dashboard.data.pd.read_sql_query", fake_read_sql)
    engine = object()

    overview = read_dashboard_overview_counts(engine)  # type: ignore[arg-type]
    alerts = read_dashboard_alert_queue(engine, severities=["high"], limit=5)  # type: ignore[arg-type]
    cases = read_dashboard_case_queue(engine, statuses=["New"], risk_bands=["critical"], limit=5)  # type: ignore[arg-type]
    detail = read_dashboard_case_detail(engine, "CASE1")  # type: ignore[arg-type]
    evidence = read_dashboard_case_evidence(engine, "CASE1")  # type: ignore[arg-type]
    options = read_dashboard_filter_options(engine)  # type: ignore[arg-type]

    all_sql = "\n".join(sql for sql, _ in calls)
    assert "staging.transactions" in all_sql
    assert "staging.accounts" in all_sql
    assert "aml.alerts" in all_sql
    assert "aml.cases" in all_sql
    assert "aml.case_risk_scores" in all_sql
    assert "aml.case_lifecycle_events" in all_sql
    assert "aml.case_evidence_packs" in all_sql
    assert "aml.case_explanations" in all_sql
    assert any(params and params.get("limit") == 5 for _, params in calls)
    assert any(params and "severities" in params for _, params in calls)
    assert overview["transaction_count"] == 1
    assert not alerts.empty
    assert not cases.empty
    assert set(detail) == {
        "case",
        "case_risk_scores",
        "case_alerts",
        "alerts",
        "case_entities",
        "lifecycle_events",
    }
    assert set(evidence) == {"evidence_packs", "explanations"}
    assert isinstance(options, dict)


def test_reader_failures_raise_dashboard_data_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_read(*_: object, **__: object) -> pd.DataFrame:
        raise RuntimeError("boom")

    monkeypatch.setattr("graph_aml.dashboard.data.pd.read_sql_query", fail_read)

    with pytest.raises(DashboardDataError):
        read_dashboard_alert_queue(object())  # type: ignore[arg-type]


def test_readers_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_engine(*_: object, **__: object) -> object:
        raise AssertionError("engine created")

    monkeypatch.setattr("graph_aml.dashboard.database.create_database_engine", fail_engine)
    monkeypatch.setattr(
        "graph_aml.dashboard.data.pd.read_sql_query",
        lambda *_args, **_kwargs: pd.DataFrame({"alert_id": ["A1"], "severity": ["high"]}),
    )

    assert not read_dashboard_alert_queue(object()).empty  # type: ignore[arg-type]
