"""Tests for scoring input readers."""

import pandas as pd
import pytest

from graph_aml.scoring import (
    AccountRiskScoringConfig,
    ScoringInputError,
    read_scoring_accounts,
    read_scoring_alerts,
    read_scoring_anomaly_scores,
    read_scoring_feature_inputs,
    read_scoring_graph_features,
)


class FakeEngine:
    pass


def test_input_readers_query_expected_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append(str(statement))
        return pd.DataFrame({"account_id": ["A1"]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    read_scoring_accounts(FakeEngine(), limit=1)  # type: ignore[arg-type]
    read_scoring_alerts(FakeEngine(), limit=1)  # type: ignore[arg-type]
    read_scoring_graph_features(FakeEngine(), limit=1)  # type: ignore[arg-type]
    read_scoring_anomaly_scores(FakeEngine(), limit=1)  # type: ignore[arg-type]

    combined = "\n".join(calls)
    assert "staging.accounts" in combined
    assert "aml.alerts" in combined
    assert "mart.graph_features" in combined
    assert "mart.account_anomaly_scores" in combined


def test_read_scoring_feature_inputs_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.scoring.inputs.read_scoring_accounts", lambda *a, **k: pd.DataFrame()
    )
    monkeypatch.setattr(
        "graph_aml.scoring.inputs.read_scoring_alerts", lambda *a, **k: pd.DataFrame()
    )
    monkeypatch.setattr(
        "graph_aml.scoring.inputs.read_scoring_graph_features", lambda *a, **k: pd.DataFrame()
    )
    monkeypatch.setattr(
        "graph_aml.scoring.inputs.read_scoring_anomaly_scores", lambda *a, **k: pd.DataFrame()
    )
    inputs = read_scoring_feature_inputs(FakeEngine(), AccountRiskScoringConfig(), limit=10)  # type: ignore[arg-type]
    assert set(inputs) == {"accounts", "alerts", "graph_features", "anomaly_scores"}


def test_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(ScoringInputError):
        read_scoring_alerts(FakeEngine())  # type: ignore[arg-type]


def test_invalid_limit_raises() -> None:
    with pytest.raises(ScoringInputError):
        read_scoring_alerts(FakeEngine(), limit=-1)  # type: ignore[arg-type]
