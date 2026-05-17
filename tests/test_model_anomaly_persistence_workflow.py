"""Tests for anomaly score persistence workflows."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from graph_aml.models import (
    AnomalyScorePersistenceConfig,
    AnomalyScoreResult,
    IsolationForestModelConfig,
    ModelPersistenceError,
    persist_anomaly_scores,
    prepare_anomaly_scores_for_persistence,
    train_isolation_forest_model,
    upsert_anomaly_scores,
)


class FakeConnection:
    def __init__(self) -> None:
        self.executions: list[tuple[object, object]] = []

    def execute(self, statement: object, params: object = None) -> None:
        self.executions.append((statement, params))


class FakeBegin:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, *args: object) -> None:
        return None


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self) -> FakeBegin:
        return FakeBegin(self.connection)


def training_result():
    frame = pd.DataFrame(
        {"account_id": [f"A{i}" for i in range(5)], "f1": range(5), "f2": range(5)}
    )
    return train_isolation_forest_model(
        frame,
        IsolationForestModelConfig(min_training_rows=5, n_estimators=5, mlflow_enabled=False),
        trained_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def score_result() -> AnomalyScoreResult:
    return AnomalyScoreResult(
        scores=pd.DataFrame(
            {
                "account_id": ["A1", "A2", "A3"],
                "anomaly_score": [10.0, 85.0, 98.0],
                "anomaly_score_raw": [-0.1, -0.2, -0.3],
                "is_anomaly": [False, True, True],
                "anomaly_rank": [3, 2, 1],
                "risk_band": ["low", "medium", "high"],
            }
        )
    )


def test_upsert_returns_zero_for_empty_input() -> None:
    assert upsert_anomaly_scores(FakeEngine(), pd.DataFrame()) == 0


def test_upsert_writes_rows_in_batches() -> None:
    engine = FakeEngine()
    prepared = prepare_anomaly_scores_for_persistence(score_result(), training_result())
    assert upsert_anomaly_scores(engine, prepared, batch_size=2) == 3
    assert len(engine.connection.executions) == 2


def test_persist_prepares_upserts_and_optionally_audits() -> None:
    engine = FakeEngine()
    result = persist_anomaly_scores(
        engine,
        score_result(),
        training_result(),
        AnomalyScorePersistenceConfig(write_audit=True),
    )
    assert result.rows_prepared == 3
    assert result.rows_persisted == 3
    assert len(engine.connection.executions) == 2


def test_persist_skips_audit_when_configured() -> None:
    engine = FakeEngine()
    persist_anomaly_scores(
        engine,
        score_result(),
        training_result(),
        AnomalyScorePersistenceConfig(write_audit=False),
    )
    assert len(engine.connection.executions) == 1


def test_persistence_failures_raise() -> None:
    class BrokenEngine:
        def begin(self) -> object:
            raise RuntimeError("boom")

    prepared = prepare_anomaly_scores_for_persistence(score_result(), training_result())
    with pytest.raises(ModelPersistenceError):
        upsert_anomaly_scores(BrokenEngine(), prepared)
