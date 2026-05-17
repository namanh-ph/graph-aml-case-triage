"""Tests for case generation input readers."""

import pandas as pd
import pytest

from graph_aml.cases import CaseInputError, read_case_inputs
from graph_aml.cases.inputs import (
    read_case_account_risk_scores,
    read_case_accounts,
    read_case_alerts,
    read_case_graph_features,
    read_case_transactions,
)


class FakeEngine:
    pass


def test_case_input_readers_query_expected_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        seen.append(str(sql))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    engine = FakeEngine()
    read_case_alerts(engine)
    read_case_accounts(engine)
    read_case_account_risk_scores(engine)
    read_case_graph_features(engine)
    read_case_transactions(engine)
    text = "\n".join(seen)
    assert "aml.alerts" in text
    assert "staging.accounts" in text
    assert "mart.account_risk_scores" in text
    assert "mart.graph_features" in text
    assert "staging.transactions" in text


def test_case_input_readers_apply_limits_and_bound_params(monkeypatch: pytest.MonkeyPatch) -> None:
    params_seen: list[dict[str, object] | None] = []

    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        params_seen.append(params)
        assert "LIMIT :limit" in str(sql)
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    read_case_alerts(FakeEngine(), lookback_days=3, limit=10)
    assert params_seen[0]["limit"] == 10
    assert params_seen[0]["lookback_days"] == 3


def test_read_case_inputs_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *args, **kwargs: pd.DataFrame())
    result = read_case_inputs(FakeEngine(), limit=1)
    assert set(result) == {
        "alerts",
        "accounts",
        "account_risk_scores",
        "graph_features",
        "transactions",
    }


def test_case_input_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(CaseInputError):
        read_case_alerts(FakeEngine())


def test_case_input_readers_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *args, **kwargs: pd.DataFrame())
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    read_case_alerts(FakeEngine())


def test_case_input_reader_rejects_negative_limit() -> None:
    with pytest.raises(CaseInputError):
        read_case_alerts(FakeEngine(), limit=-1)
