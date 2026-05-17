"""Tests for account risk score persistence workflow and audit."""

from datetime import date

import pandas as pd
import pytest

from graph_aml.scoring import (
    AccountRiskScorePersistenceConfig,
    AccountRiskScorePersistenceResult,
    ScoringPersistenceError,
    compute_account_risk_scores,
    persist_account_risk_scores,
    upsert_account_risk_scores,
    write_account_risk_score_audit_event,
)


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def execute(self, statement, params=None):
        self.calls.append(params)


class FakeBegin:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self) -> FakeBegin:
        return FakeBegin(self.connection)


def scoring_result():
    frame = pd.DataFrame(
        {
            "account_id": ["A1"],
            "rule_risk_score": [100],
            "graph_risk_score": [0],
            "anomaly_risk_score": [0],
            "customer_risk_score": [0],
            "jurisdiction_risk_score": [0],
            "alert_count": [1],
            "high_severity_alert_count": [1],
            "critical_severity_alert_count": [0],
            "max_rule_alert_score": [100],
            "mean_rule_alert_score": [100],
            "max_anomaly_score": [0],
            "graph_percentile_score": [0],
            "component_coverage": [0.2],
        }
    )
    return compute_account_risk_scores(frame, score_date=date(2026, 5, 7))


def test_upsert_returns_zero_for_empty() -> None:
    assert upsert_account_risk_scores(FakeEngine(), pd.DataFrame()) == 0  # type: ignore[arg-type]


def test_persist_prepares_upserts_and_audits() -> None:
    engine = FakeEngine()
    result = persist_account_risk_scores(engine, scoring_result())  # type: ignore[arg-type]
    assert isinstance(result, AccountRiskScorePersistenceResult)
    assert result.rows_persisted == 1
    assert len(engine.connection.calls) >= 2


def test_persist_skips_audit_when_configured() -> None:
    engine = FakeEngine()
    result = persist_account_risk_scores(
        engine,  # type: ignore[arg-type]
        scoring_result(),
        AccountRiskScorePersistenceConfig(write_audit=False),
    )
    assert result.rows_persisted == 1
    assert len(engine.connection.calls) == 1


def test_audit_writer_inserts_expected_event() -> None:
    engine = FakeEngine()
    write_account_risk_score_audit_event(
        engine,  # type: ignore[arg-type]
        AccountRiskScorePersistenceResult(rows_prepared=1, rows_persisted=1, score_version="v1"),
    )
    payload = engine.connection.calls[0]
    assert payload["event_type"] == "risk_scoring"
    assert payload["component"] == "scoring"
    assert payload["action"] == "persist_account_risk_scores"


def test_persistence_failures_raise() -> None:
    class BadEngine:
        def begin(self):
            raise RuntimeError("boom")

    with pytest.raises(ScoringPersistenceError):
        persist_account_risk_scores(BadEngine(), scoring_result())  # type: ignore[arg-type]
