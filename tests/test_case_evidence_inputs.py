"""Tests for case evidence input readers."""

import pandas as pd
import pytest

from graph_aml.cases import (
    CaseEvidenceInputError,
    read_case_evidence_inputs,
    read_evidence_account_risk_scores,
    read_evidence_alerts,
    read_evidence_anomaly_scores,
    read_evidence_case_alerts,
    read_evidence_case_entities,
    read_evidence_case_risk_scores,
    read_evidence_cases,
    read_evidence_graph_features,
    read_evidence_transactions,
)


class FakeEngine:
    pass


def test_case_evidence_readers_query_expected_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    queries: list[str] = []

    def fake_read_sql(statement, engine, params=None):  # noqa: ANN001
        queries.append(str(statement))
        return pd.DataFrame(
            {"case_id": ["CASE_001"], "alert_id": ["ALERT_001"], "account_id": ["ACC_001"]}
        )

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    engine = FakeEngine()
    read_evidence_cases(engine)
    read_evidence_case_alerts(engine)
    read_evidence_case_entities(engine)
    read_evidence_alerts(engine)
    read_evidence_transactions(engine)
    read_evidence_account_risk_scores(engine)
    read_evidence_case_risk_scores(engine)
    read_evidence_graph_features(engine)
    read_evidence_anomaly_scores(engine)
    joined = "\n".join(queries)
    for table in (
        "aml.cases",
        "aml.case_alerts",
        "aml.case_entities",
        "aml.alerts",
        "staging.transactions",
        "mart.account_risk_scores",
        "aml.case_risk_scores",
        "mart.graph_features",
        "mart.account_anomaly_scores",
    ):
        assert table in joined


def test_case_evidence_readers_apply_limits_and_params(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, object] | None] = []

    def fake_read_sql(statement, engine, params=None):  # noqa: ANN001
        captured.append(params)
        assert "LIMIT :limit" in str(statement)
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    read_evidence_cases(FakeEngine(), case_ids=["CASE_001"], limit=5)
    assert captured[0] == {"case_ids": ["CASE_001"], "limit": 5}


def test_read_case_evidence_inputs_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_sql(statement, engine, params=None):  # noqa: ANN001
        sql = str(statement)
        if "aml.cases" in sql:
            return pd.DataFrame({"case_id": ["CASE_001"], "primary_account_id": ["ACC_001"]})
        if "aml.case_alerts" in sql:
            return pd.DataFrame({"case_id": ["CASE_001"], "alert_id": ["ALERT_001"]})
        if "aml.alerts" in sql:
            return pd.DataFrame(
                {
                    "alert_id": ["ALERT_001"],
                    "account_id": ["ACC_001"],
                    "evidence_ids": [["TXN_001"]],
                }
            )
        return pd.DataFrame()

    monkeypatch.setattr(pd, "read_sql_query", fake_read_sql)
    result = read_case_evidence_inputs(FakeEngine())
    assert set(result) == {
        "cases",
        "case_alerts",
        "case_entities",
        "alerts",
        "transactions",
        "account_risk_scores",
        "case_risk_scores",
        "graph_features",
        "anomaly_scores",
    }


def test_reader_failures_raise_and_do_not_create_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pd, "read_sql_query", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setattr(
        "graph_aml.database.create_database_engine",
        lambda: (_ for _ in ()).throw(AssertionError("should not create engine")),
        raising=False,
    )
    with pytest.raises(CaseEvidenceInputError):
        read_evidence_cases(FakeEngine())
    with pytest.raises(CaseEvidenceInputError):
        read_evidence_cases(FakeEngine(), limit=-1)
