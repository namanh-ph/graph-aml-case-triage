"""Tests for Isolation Forest training and scoring."""

import pandas as pd
import pytest
from sklearn.ensemble import IsolationForest

from graph_aml.models import (
    AnomalyScoreResult,
    IsolationForestModelConfig,
    IsolationForestTrainingResult,
    ModelTrainingError,
    build_isolation_forest_model,
    score_isolation_forest_model,
    train_and_score_isolation_forest,
    train_isolation_forest_model,
)


def feature_frame(rows: int = 30) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": [f"A{i:03d}" for i in range(rows)],
            "txn_count_7d": list(range(rows)),
            "total_sent_7d": [float(i * 10) for i in range(rows)],
            "pagerank_score": [float(i % 5) for i in range(rows)],
        }
    )


def config() -> IsolationForestModelConfig:
    return IsolationForestModelConfig(min_training_rows=5, n_estimators=20, mlflow_enabled=False)


def test_model_builder_returns_isolation_forest() -> None:
    assert isinstance(build_isolation_forest_model(config()), IsolationForest)


def test_training_returns_result_with_features_and_parameters() -> None:
    result = train_isolation_forest_model(feature_frame(), config())
    assert isinstance(result, IsolationForestTrainingResult)
    assert result.feature_names == ("txn_count_7d", "total_sent_7d", "pagerank_score")
    assert result.parameters["n_estimators"] == 20


def test_training_checks_minimum_row_count() -> None:
    with pytest.raises(ModelTrainingError):
        train_isolation_forest_model(feature_frame(3), config())


def test_scoring_returns_required_columns_and_valid_scores() -> None:
    training = train_isolation_forest_model(feature_frame(), config())
    scores = score_isolation_forest_model(training, feature_frame(), config())
    assert isinstance(scores, AnomalyScoreResult)
    assert set(
        [
            "account_id",
            "anomaly_score",
            "anomaly_score_raw",
            "is_anomaly",
            "anomaly_rank",
            "risk_band",
        ]
    ).issubset(scores.scores.columns)
    assert scores.scores["anomaly_score"].between(0, 100).all()
    assert set(scores.scores["risk_band"]).issubset({"low", "medium", "high"})


def test_training_and_scoring_are_deterministic() -> None:
    first = train_and_score_isolation_forest(feature_frame(), config())[1].scores
    second = train_and_score_isolation_forest(feature_frame(), config())[1].scores
    pd.testing.assert_frame_equal(first, second)


def test_training_failures_raise() -> None:
    frame = feature_frame()
    frame = frame.drop(columns=["account_id"])
    with pytest.raises(ModelTrainingError):
        train_isolation_forest_model(frame, config())
