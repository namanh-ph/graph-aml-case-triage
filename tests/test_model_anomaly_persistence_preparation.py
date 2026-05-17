"""Tests for anomaly score persistence config and preparation."""

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from graph_aml.models import (
    AnomalyScorePersistenceConfig,
    AnomalyScoreResult,
    IsolationForestModelConfig,
    ModelPersistenceError,
    build_model_run_id,
    prepare_anomaly_scores_for_persistence,
    train_isolation_forest_model,
)


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
        ),
        summary={"row_count": 3},
        metadata={"source": "unit"},
    )


def test_default_persistence_config_is_valid() -> None:
    assert AnomalyScorePersistenceConfig().model_name == "account_isolation_forest"


@pytest.mark.parametrize(
    "kwargs",
    [{"model_name": ""}, {"model_version": ""}, {"model_run_id": ""}, {"batch_size": 0}],
)
def test_invalid_persistence_config_raises(kwargs: dict[str, object]) -> None:
    with pytest.raises(ModelPersistenceError):
        AnomalyScorePersistenceConfig(**kwargs)


def test_model_run_id_is_deterministic_and_safe() -> None:
    run_id = build_model_run_id(date(2026, 1, 25), "Account IF", "v/1")
    assert run_id == "account_if_v_1_2026_01_25"


def test_prepared_scores_include_database_columns() -> None:
    prepared = prepare_anomaly_scores_for_persistence(
        score_result(),
        training_result(),
        AnomalyScorePersistenceConfig(score_date=date(2026, 1, 25)),
        scored_at=datetime(2026, 1, 25, tzinfo=UTC),
    )
    for column in [
        "score_date",
        "model_name",
        "model_version",
        "model_run_id",
        "feature_names",
        "model_parameters",
        "preprocessing_metadata",
        "metrics",
        "metadata",
        "scored_at",
    ]:
        assert column in prepared.columns
    assert prepared.loc[0, "feature_names"] == ["f1", "f2"]


def test_duplicate_accounts_are_deduplicated_and_inputs_are_not_mutated() -> None:
    result = score_result()
    result.scores.loc[1, "account_id"] = "A1"
    original = result.scores.copy(deep=True)
    prepared = prepare_anomaly_scores_for_persistence(result, training_result())
    assert prepared["account_id"].is_unique
    pd.testing.assert_frame_equal(result.scores, original)
