"""Tests for dashboard graph PostgreSQL readers."""

import pandas as pd
import pytest
from sqlalchemy.sql.elements import TextClause

from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.graph_data import (
    read_graph_view_context,
    read_graph_view_postgres_edges,
    read_graph_view_seed_accounts,
)


def test_graph_readers_query_expected_sources_and_params(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read(
        sql: TextClause,
        engine: object,
        params: dict[str, object] | None = None,
    ) -> pd.DataFrame:
        calls.append((str(sql), params))
        text = str(sql)
        if "staging.accounts" in text:
            return pd.DataFrame(
                {
                    "account_id": ["A1"],
                    "customer_id": ["C1"],
                    "account_risk_score": [91.0],
                    "risk_band": ["critical"],
                    "community_id": [7],
                }
            )
        if "staging.transactions" in text:
            return pd.DataFrame(
                {
                    "source_id": ["A1"],
                    "target_id": ["A2"],
                    "edge_type": ["transaction_account"],
                    "weight": [1.0],
                    "transaction_id": ["T1"],
                    "amount": [100.0],
                    "metadata": [{}],
                }
            )
        if "aml.alerts" in text:
            return pd.DataFrame({"alert_id": ["AL1"], "risk_score_rule": [90.0]})
        if "aml.cases" in text:
            return pd.DataFrame({"case_id": ["CASE1"], "priority_score": [90.0]})
        return pd.DataFrame()

    monkeypatch.setattr("graph_aml.dashboard.graph_data.pd.read_sql_query", fake_read)
    engine = object()

    seeds = read_graph_view_seed_accounts(engine, account_id="A1", limit=5)  # type: ignore[arg-type]
    edges = read_graph_view_postgres_edges(engine, ["A1"], limit=5)  # type: ignore[arg-type]
    context = read_graph_view_context(engine, account_id="A1")  # type: ignore[arg-type]

    all_sql = "\n".join(sql for sql, _ in calls)
    assert "mart.account_risk_scores" in all_sql
    assert "mart.graph_features" in all_sql
    assert "staging.transactions" in all_sql
    assert "aml.alerts" in all_sql
    assert "aml.cases" in all_sql
    assert any(params and params.get("limit") == 5 for _, params in calls)
    assert any(params and "account_id" in params for _, params in calls)
    assert not seeds.empty
    assert not edges.empty
    assert {"nodes", "edges"}.issubset(context)


def test_empty_seed_accounts_produce_empty_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.dashboard.graph_data.pd.read_sql_query",
        lambda *_args, **_kwargs: pd.DataFrame(),
    )

    context = read_graph_view_context(object(), account_id="A1")  # type: ignore[arg-type]

    assert context["nodes"].empty
    assert context["edges"].empty


def test_graph_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> pd.DataFrame:
        raise RuntimeError("boom")

    monkeypatch.setattr("graph_aml.dashboard.graph_data.pd.read_sql_query", fail)

    with pytest.raises(DashboardDataError):
        read_graph_view_seed_accounts(object(), account_id="A1")  # type: ignore[arg-type]


def test_graph_readers_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.dashboard.database.create_dashboard_engine",
        lambda: (_ for _ in ()).throw(AssertionError("engine")),
    )
    monkeypatch.setattr(
        "graph_aml.dashboard.graph_data.pd.read_sql_query",
        lambda *_args, **_kwargs: pd.DataFrame({"account_id": ["A1"]}),
    )

    assert not read_graph_view_seed_accounts(object(), account_id="A1").empty  # type: ignore[arg-type]
