"""Tests for model summary helpers."""

from datetime import UTC, datetime

import pandas as pd

from graph_aml.models import (
    AnomalyScoreResult,
    IsolationForestModelConfig,
    anomaly_score_result_to_dict,
    summarise_anomaly_scores,
    summarise_training_result,
    train_isolation_forest_model,
)


def scores() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": ["A1", "A2", "A3"],
            "anomaly_score": [10.0, 85.0, 98.0],
            "anomaly_score_raw": [-0.1, -0.2, -0.3],
            "is_anomaly": [False, True, True],
            "anomaly_rank": [3, 2, 1],
            "risk_band": ["low", "medium", "high"],
        }
    )


def test_score_summary_contains_counts_and_distribution() -> None:
    summary = summarise_anomaly_scores(scores())
    assert summary["row_count"] == 3
    assert summary["anomaly_count"] == 2
    assert summary["high_risk_count"] == 1
    assert summary["min_score"] == 10.0


def test_training_summary_contains_model_metadata() -> None:
    frame = pd.DataFrame(
        {"account_id": [f"A{i}" for i in range(5)], "f1": range(5), "f2": range(5)}
    )
    training = train_isolation_forest_model(
        frame,
        IsolationForestModelConfig(min_training_rows=5, n_estimators=5, mlflow_enabled=False),
        trained_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    summary = summarise_training_result(training)
    assert summary["model_name"] == "account_isolation_forest"
    assert summary["training_row_count"] == 5
    assert summary["feature_count"] == 2


def test_anomaly_score_result_to_dict_is_json_ready() -> None:
    result = AnomalyScoreResult(scores=scores(), summary={"row_count": 3})
    payload = anomaly_score_result_to_dict(result)
    assert payload["summary"]["row_count"] == 3
    assert len(payload["scores"]) == 3


def test_empty_score_frames_are_handled() -> None:
    assert summarise_anomaly_scores(pd.DataFrame())["row_count"] == 0
