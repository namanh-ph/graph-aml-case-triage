"""Tests for persisted case readers."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CasePersistenceError,
    read_case_alerts,
    read_case_detail,
    read_case_entities,
    read_case_summary,
    read_cases,
)


class FakeEngine:
    pass


def test_case_readers_query_and_filter_expected_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    params_seen: list[dict[str, object] | None] = []

    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        seen.append(str(sql))
        params_seen.append(params)
        return pd.DataFrame({"case_count": [0]}) if "COUNT(*)" in str(sql) else pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    engine = FakeEngine()
    read_cases(
        engine,
        status="New",
        severity="high",
        case_version="v1",
        account_id="A1",
        customer_id="C1",
        limit=5,
    )
    read_case_alerts(engine, case_id="CASE1")
    read_case_entities(engine, case_id="CASE1", entity_type="account")
    text = "\n".join(seen)
    assert "aml.cases" in text
    assert "aml.case_alerts" in text
    assert "aml.case_entities" in text
    assert params_seen[0]["status"] == "New"
    assert params_seen[0]["limit"] == 5


def test_case_detail_returns_dictionary_of_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *args, **kwargs: pd.DataFrame())
    detail = read_case_detail(FakeEngine(), "CASE1")
    assert set(detail) == {"case", "alerts", "entities"}


def test_case_summary_is_json_serialisable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_sql(sql, engine, params=None):  # noqa: ANN001
        text = str(sql)
        if "COUNT(*) AS case_count" in text:
            return pd.DataFrame(
                {
                    "case_count": [1],
                    "unique_primary_account_count": [1],
                    "max_priority_score": [80],
                    "mean_priority_score": [80],
                }
            )
        if "status" in text:
            return pd.DataFrame({"status": ["New"], "count": [1]})
        if "severity" in text:
            return pd.DataFrame({"severity": ["high"], "count": [1]})
        return pd.DataFrame({"grouping_strategy": ["account"], "count": [1]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    assert read_case_summary(FakeEngine())["case_count"] == 1


def test_case_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd, "read_sql_query", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(CasePersistenceError):
        read_cases(FakeEngine())


def test_case_readers_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pd, "read_sql_query", lambda *args, **kwargs: pd.DataFrame())
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    read_cases(FakeEngine())
