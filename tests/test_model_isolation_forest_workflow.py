"""Tests for end-to-end Isolation Forest train, score, and persist workflow."""

import pandas as pd
import pytest

from graph_aml.models import (
    AnomalyScorePersistenceResult,
    AnomalyScoreResult,
    IsolationForestModelConfig,
    IsolationForestTrainingResult,
    ModelTrainingError,
    train_score_and_persist_isolation_forest,
)
from graph_aml.models.preprocessing import ModelPreprocessingResult


def test_train_score_and_persist_workflow_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_read(
        engine: object,
        config: object = None,
        limit: int | None = None,
    ) -> dict[str, pd.DataFrame]:
        calls.append(f"read:{limit}")
        return {
            "account_features": pd.DataFrame({"account_id": ["A1"], "f1": [1]}),
            "graph_features": pd.DataFrame(),
        }

    def fake_build(
        account: pd.DataFrame,
        graph: pd.DataFrame,
        config: object = None,
    ) -> pd.DataFrame:
        calls.append("build")
        return pd.DataFrame({"account_id": ["A1"], "f1": [1]})

    training = IsolationForestTrainingResult(
        model=object(),
        preprocessing=ModelPreprocessingResult(
            account_ids=("A1",),
            feature_names=("f1",),
            matrix=[],
        ),
        model_name="m",
        model_version="v",
        trained_at=pd.Timestamp("2026-01-01", tz="UTC").to_pydatetime(),
        training_row_count=1,
        feature_names=("f1",),
    )
    scores = AnomalyScoreResult(scores=pd.DataFrame({"account_id": ["A1"]}))
    persisted = AnomalyScorePersistenceResult(rows_persisted=1)

    def fake_train_score(frame: pd.DataFrame, config: object = None) -> tuple[object, object]:
        calls.append("train_score")
        return training, scores

    def fake_persist(*args: object, **kwargs: object) -> object:
        calls.append("persist")
        return persisted

    monkeypatch.setattr("graph_aml.models.isolation_forest.read_model_feature_inputs", fake_read)
    monkeypatch.setattr("graph_aml.models.isolation_forest.build_model_feature_frame", fake_build)
    monkeypatch.setattr(
        "graph_aml.models.isolation_forest.train_and_score_isolation_forest",
        fake_train_score,
    )
    monkeypatch.setattr("graph_aml.models.persistence.persist_anomaly_scores", fake_persist)

    result = train_score_and_persist_isolation_forest(
        object(),
        IsolationForestModelConfig(min_training_rows=1, mlflow_enabled=False),
        limit=25,
    )
    assert result == (training, scores, persisted)
    assert calls == ["read:25", "build", "train_score", "persist"]


def test_workflow_failures_raise_controlled_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> dict[str, pd.DataFrame]:
        raise RuntimeError("boom")

    monkeypatch.setattr("graph_aml.models.isolation_forest.read_model_feature_inputs", fail)
    with pytest.raises(ModelTrainingError):
        train_score_and_persist_isolation_forest(object(), IsolationForestModelConfig())
