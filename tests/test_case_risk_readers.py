"""Tests for case risk score readers."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseRiskPersistenceError,
    read_case_risk_score_summary,
    read_case_risk_score_versions,
    read_case_risk_scores,
    read_latest_case_risk_scores,
)


class FakeEngine:
    pass


def test_case_risk_readers_query_and_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    params_seen: list[dict[str, object] | None] = []

    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        seen.append(str(sql))
        params_seen.append(params)
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    read_case_risk_scores(
        FakeEngine(),
        score_date="2026-01-01",
        score_name="score",
        score_version="v1",
        risk_band="high",
        case_ids=["C1"],
        limit=10,
    )
    read_latest_case_risk_scores(FakeEngine(), case_ids=["C1"])
    read_case_risk_score_versions(FakeEngine())
    text = "\n".join(seen)
    assert "aml.case_risk_scores" in text
    assert params_seen[0]["score_version"] == "v1"
    assert params_seen[0]["case_ids"] == ["C1"]
    assert params_seen[0]["limit"] == 10


def test_case_risk_summary_is_serialisable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        text = str(sql)
        if "COUNT(*) AS row_count" in text:
            return pd.DataFrame(
                {
                    "row_count": [1],
                    "unique_case_count": [1],
                    "latest_score_date": ["2026-01-01"],
                    "max_scored_at": ["2026-01-01"],
                }
            )
        if "SELECT score_name" in text:
            return pd.DataFrame({"score_name": ["score"], "score_version": ["v1"]})
        return pd.DataFrame({"risk_band": ["high"], "count": [1]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    assert read_case_risk_score_summary(FakeEngine())["row_count"] == 1


def test_case_risk_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd, "read_sql_query", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(CaseRiskPersistenceError):
        read_case_risk_scores(FakeEngine())


def test_case_risk_readers_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    read_case_risk_scores(FakeEngine())
