"""Tests for case evidence readback utilities."""

import json

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseEvidencePersistenceError,
    read_case_evidence_detail,
    read_case_evidence_packs,
    read_case_evidence_summary,
    read_case_explanations,
)


class FakeEngine:
    pass


def test_evidence_readers_query_and_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    queries: list[str] = []
    params_seen: list[dict[str, object] | None] = []

    def fake_read_sql(statement, engine, params=None):  # noqa: ANN001
        queries.append(str(statement))
        params_seen.append(params)
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    read_case_evidence_packs(FakeEngine(), case_id="CASE_001", evidence_version="v1", limit=5)
    read_case_explanations(FakeEngine(), case_id="CASE_001", explanation_version="x1", limit=5)
    assert "aml.case_evidence_packs" in queries[0]
    assert "aml.case_explanations" in queries[1]
    assert params_seen[0]["case_id"] == "CASE_001"
    assert params_seen[0]["evidence_version"] == "v1"
    assert params_seen[0]["limit"] == 5
    assert params_seen[1]["explanation_version"] == "x1"


def test_detail_and_summary_readers(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_sql(statement, engine, params=None):  # noqa: ANN001
        sql = str(statement)
        if "COUNT(*) FROM aml.case_evidence_packs" in sql:
            return pd.DataFrame(
                [
                    {
                        "evidence_pack_count": 1,
                        "explanation_count": 1,
                        "unique_case_count": 1,
                        "max_evidence_created_at": "2026-01-01",
                        "max_explanation_created_at": "2026-01-02",
                    }
                ]
            )
        if "GROUP BY evidence_version" in sql:
            return pd.DataFrame({"evidence_version": ["v1"], "row_count": [1]})
        if "GROUP BY explanation_version" in sql:
            return pd.DataFrame({"explanation_version": ["x1"], "row_count": [1]})
        return pd.DataFrame({"case_id": ["CASE_001"]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    detail = read_case_evidence_detail(FakeEngine(), "CASE_001")
    assert set(detail) == {"evidence_packs", "explanations"}
    summary = read_case_evidence_summary(FakeEngine())
    assert summary["evidence_pack_count"] == 1
    json.dumps(summary, default=str)


def test_reader_failures_raise_and_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd, "read_sql_query", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    with pytest.raises(CaseEvidencePersistenceError):
        read_case_evidence_packs(FakeEngine())
    with pytest.raises(CaseEvidencePersistenceError):
        read_case_evidence_packs(FakeEngine(), limit=-1)
