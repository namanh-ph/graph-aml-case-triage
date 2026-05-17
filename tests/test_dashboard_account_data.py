"""Tests for dashboard account profile readers."""

import pandas as pd
import pytest
from sqlalchemy.sql.elements import TextClause

from graph_aml.dashboard.account_data import (
    read_account_profile,
    read_account_profile_alerts,
    read_account_profile_cases,
    read_account_profile_counterparties,
    read_account_profile_features,
    read_account_profile_header,
    read_account_profile_transactions,
)
from graph_aml.dashboard.exceptions import DashboardDataError


def test_account_readers_query_expected_tables_and_params(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_read(
        sql: TextClause,
        engine: object,
        params: dict[str, object] | None = None,
    ) -> pd.DataFrame:
        calls.append((str(sql), params))
        text = str(sql)
        if "staging.transactions" in text and "GROUP BY" in text:
            return pd.DataFrame({"counterparty_key": ["A2"], "transaction_count": [1]})
        if "staging.transactions" in text:
            return pd.DataFrame(
                {
                    "transaction_id": ["T1"],
                    "sender_account_id": ["A1"],
                    "receiver_account_id": ["A2"],
                    "amount": [100.0],
                }
            )
        if "aml.alerts" in text:
            return pd.DataFrame({"alert_id": ["AL1"], "severity": ["high"]})
        if "aml.cases" in text:
            return pd.DataFrame({"case_id": ["CASE1"], "case_risk_score": [90.0]})
        if "mart.features_account_daily" in text:
            return pd.DataFrame({"account_id": ["A1"], "txn_count_7d": [1]})
        if "mart.graph_features" in text:
            return pd.DataFrame({"account_id": ["A1"], "community_id": [1]})
        if "mart.account_anomaly_scores" in text:
            return pd.DataFrame({"account_id": ["A1"], "anomaly_score": [88.0]})
        if "mart.account_risk_scores" in text:
            return pd.DataFrame({"account_id": ["A1"], "account_risk_score": [91.0]})
        return pd.DataFrame({"account_id": ["A1"], "customer_id": ["C1"]})

    monkeypatch.setattr("graph_aml.dashboard.account_data.pd.read_sql_query", fake_read)
    engine = object()

    read_account_profile_header(engine, "A1")  # type: ignore[arg-type]
    read_account_profile_transactions(engine, "A1", limit=5)  # type: ignore[arg-type]
    read_account_profile_alerts(engine, "A1", limit=5)  # type: ignore[arg-type]
    read_account_profile_cases(engine, "A1", limit=5)  # type: ignore[arg-type]
    read_account_profile_features(engine, "A1")  # type: ignore[arg-type]
    read_account_profile_counterparties(engine, "A1", limit=5)  # type: ignore[arg-type]
    profile = read_account_profile(engine, "A1")  # type: ignore[arg-type]

    all_sql = "\n".join(sql for sql, _ in calls)
    assert "staging.accounts" in all_sql
    assert "staging.customers" in all_sql
    assert "staging.transactions" in all_sql
    assert "aml.alerts" in all_sql
    assert "aml.cases" in all_sql
    assert "aml.case_risk_scores" in all_sql
    assert "mart.features_account_daily" in all_sql
    assert "mart.graph_features" in all_sql
    assert "mart.account_anomaly_scores" in all_sql
    assert "mart.account_risk_scores" in all_sql
    assert any(params and params.get("limit") == 5 for _, params in calls)
    assert any(params and params.get("account_id") == "A1" for _, params in calls)
    assert {
        "header",
        "transactions",
        "alerts",
        "cases",
        "counterparties",
        "behavioural_features",
        "graph_features",
        "anomaly_scores",
        "account_risk_scores",
    }.issubset(profile)


def test_account_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.dashboard.account_data.pd.read_sql_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(DashboardDataError):
        read_account_profile_header(object(), "A1")  # type: ignore[arg-type]


def test_account_readers_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.dashboard.database.create_dashboard_engine",
        lambda: (_ for _ in ()).throw(AssertionError("engine")),
    )
    monkeypatch.setattr(
        "graph_aml.dashboard.account_data.pd.read_sql_query",
        lambda *_args, **_kwargs: pd.DataFrame({"account_id": ["A1"]}),
    )

    assert not read_account_profile_header(object(), "A1").empty  # type: ignore[arg-type]
