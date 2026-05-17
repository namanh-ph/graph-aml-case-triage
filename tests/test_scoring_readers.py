"""Tests for account risk score readers."""

import pandas as pd
import pytest

from graph_aml.scoring import (
    ScoringPersistenceError,
    read_account_risk_score_summary,
    read_account_risk_score_versions,
    read_account_risk_scores,
    read_latest_account_risk_scores,
)


class FakeEngine:
    pass


def test_readers_query_risk_score_table(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_read_sql_query(statement, engine, params=None):
        calls.append(str(statement))
        return pd.DataFrame(
            {"row_count": [0], "unique_account_count": [0], "max_scored_at": [None]}
        )

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    read_account_risk_scores(FakeEngine(), risk_band="high", account_ids=["A1"], limit=1)  # type: ignore[arg-type]
    read_latest_account_risk_scores(FakeEngine(), limit=1)  # type: ignore[arg-type]
    read_account_risk_score_versions(FakeEngine())  # type: ignore[arg-type]
    assert all("mart.account_risk_scores" in call for call in calls)


def test_summary_is_json_serialisable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_sql_query(statement, engine, params=None):
        sql = str(statement)
        if "GROUP BY score_date" in sql:
            return pd.DataFrame()
        if "GROUP BY risk_band" in sql:
            return pd.DataFrame(columns=["risk_band", "row_count"])
        return pd.DataFrame(
            {"row_count": [0], "unique_account_count": [0], "max_scored_at": [None]}
        )

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql_query)
    assert read_account_risk_score_summary(FakeEngine())["row_count"] == 0  # type: ignore[arg-type]


def test_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd, "read_sql_query", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(ScoringPersistenceError):
        read_account_risk_scores(FakeEngine())  # type: ignore[arg-type]
