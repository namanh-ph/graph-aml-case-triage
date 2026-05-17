"""Tests for release readiness readers."""

import json

import pandas as pd
import pytest

from graph_aml.release import (
    ReleasePersistenceError,
    read_release_artefact_checks,
    read_release_evidence_index,
    read_release_portfolio_pack,
    read_release_readiness_runs,
    read_release_readiness_summary,
    read_release_repository_checks,
)


class DummyEngine:
    pass


def test_release_readers_query_expected_tables(monkeypatch) -> None:
    calls: list[str] = []

    def fake_read_sql(query, engine, params=None):
        calls.append(str(query))
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    engine = DummyEngine()
    read_release_readiness_runs(engine, limit=1)  # type: ignore[arg-type]
    read_release_repository_checks(engine, release_run_id="run", limit=1)  # type: ignore[arg-type]
    read_release_artefact_checks(engine, status="pass", limit=1)  # type: ignore[arg-type]
    read_release_evidence_index(engine, evidence_type="index", limit=1)  # type: ignore[arg-type]
    read_release_portfolio_pack(engine, release_run_id="run", limit=1)  # type: ignore[arg-type]

    joined = "\n".join(calls)
    assert "governance.release_readiness_runs" in joined
    assert "governance.release_repository_checks" in joined
    assert "governance.release_artefact_checks" in joined
    assert "governance.release_evidence_index" in joined
    assert "governance.release_portfolio_pack" in joined
    assert ":limit" in joined


def test_release_reader_failures_raise(monkeypatch) -> None:
    def fake_read_sql(query, engine, params=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    with pytest.raises(ReleasePersistenceError):
        read_release_readiness_runs(DummyEngine())  # type: ignore[arg-type]


def test_release_summary_is_json_serialisable(monkeypatch) -> None:
    def fake_read_sql(query, engine, params=None):
        sql = str(query)
        if "release_readiness_runs" in sql:
            return pd.DataFrame(
                [
                    {
                        "release_run_id": "run",
                        "release_version": "v1",
                        "failed_check_count": 0,
                        "warning_check_count": 1,
                    }
                ]
            )
        return pd.DataFrame([{"row": 1}])

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    payload = read_release_readiness_summary(DummyEngine())  # type: ignore[arg-type]
    json.dumps(payload)
    assert payload["latest_release_run_id"] == "run"
