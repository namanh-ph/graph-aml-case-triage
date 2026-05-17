"""Tests for case risk input readers."""

import pandas as pd
import pytest

from graph_aml.cases import CaseRiskInputError, read_case_risk_inputs
from graph_aml.cases.risk_inputs import (
    read_case_risk_account_scores,
    read_case_risk_alerts,
    read_case_risk_anomaly_scores,
    read_case_risk_case_alerts,
    read_case_risk_cases,
    read_case_risk_graph_features,
    read_case_risk_transactions,
)


class FakeEngine:
    pass


def test_case_risk_readers_query_expected_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        seen.append(str(sql))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    engine = FakeEngine()
    read_case_risk_cases(engine)
    read_case_risk_case_alerts(engine)
    read_case_risk_alerts(engine)
    read_case_risk_account_scores(engine)
    read_case_risk_graph_features(engine)
    read_case_risk_anomaly_scores(engine)
    read_case_risk_transactions(engine)
    text = "\n".join(seen)
    for table in (
        "aml.cases",
        "aml.case_alerts",
        "aml.alerts",
        "mart.account_risk_scores",
        "mart.graph_features",
        "mart.account_anomaly_scores",
        "staging.transactions",
    ):
        assert table in text


def test_case_risk_readers_apply_limits_and_params(monkeypatch: pytest.MonkeyPatch) -> None:
    params_seen: list[dict[str, object] | None] = []

    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        params_seen.append(params)
        assert "LIMIT :limit" in str(sql)
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    read_case_risk_cases(FakeEngine(), case_version="v1", min_priority_score=5, limit=10)
    assert params_seen[0]["case_version"] == "v1"
    assert params_seen[0]["limit"] == 10


def test_read_case_risk_inputs_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        text = str(sql)
        if "aml.cases" in text and "case_risk_scores" not in text:
            return pd.DataFrame({"case_id": ["C1"], "primary_account_id": ["A1"]})
        if "aml.case_alerts" in text:
            return pd.DataFrame({"case_id": ["C1"], "alert_id": ["AL1"]})
        if "aml.alerts" in text:
            return pd.DataFrame({"alert_id": ["AL1"], "evidence_ids": [["T1"]]})
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    assert set(read_case_risk_inputs(FakeEngine())) == {
        "cases",
        "case_alerts",
        "alerts",
        "account_risk_scores",
        "graph_features",
        "anomaly_scores",
        "transactions",
    }


def test_case_risk_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd, "read_sql_query", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(CaseRiskInputError):
        read_case_risk_cases(FakeEngine())


def test_case_risk_readers_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *args, **kwargs: pd.DataFrame())
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    read_case_risk_cases(FakeEngine())
