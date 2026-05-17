from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.models import (
    SupervisedDatasetConfig,
    SupervisedFeatureError,
    SupervisedModelConfig,
    SupervisedTrainingError,
    SupervisedTrainingResult,
    build_supervised_estimator,
    build_supervised_feature_matrix,
    build_supervised_preprocessing_pipeline,
    split_supervised_feature_matrix,
    train_supervised_model,
)


def _dataset() -> pd.DataFrame:
    rows = 20
    return pd.DataFrame(
        {
            "case_id": [f"C{i}" for i in range(rows)],
            "case_label": [0, 1] * 10,
            "label_timestamp": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "case_risk_score": [float(i) for i in range(rows)],
            "alert_count": [i % 3 + 1 for i in range(rows)],
        }
    )


def _split(config: SupervisedModelConfig | None = None):
    matrix = build_supervised_feature_matrix(_dataset(), config)
    return split_supervised_feature_matrix(matrix, config)


def test_preprocessing_pipeline_is_built() -> None:
    assert hasattr(build_supervised_preprocessing_pipeline(), "fit_transform")


def test_logistic_regression_estimator_is_default() -> None:
    assert build_supervised_estimator().__class__.__name__ == "LogisticRegression"


def test_random_forest_estimator_is_built() -> None:
    config = SupervisedModelConfig(model_family="random_forest")
    assert build_supervised_estimator(config).__class__.__name__ == "RandomForestClassifier"


def test_model_trains_on_compact_fixture() -> None:
    config = SupervisedModelConfig(dataset=SupervisedDatasetConfig(min_rows=10))
    result = train_supervised_model(_split(config), config)
    assert isinstance(result, SupervisedTrainingResult)
    assert hasattr(result.estimator, "predict")


def test_training_result_contains_features_and_metrics() -> None:
    result = train_supervised_model(_split())
    assert result.feature_names
    assert "precision" in result.validation_metrics


def test_single_class_training_raises_unless_allowed() -> None:
    frame = _dataset()
    frame["case_label"] = 1
    config = SupervisedModelConfig(
        dataset=SupervisedDatasetConfig(allow_single_class_training=False)
    )
    with pytest.raises(SupervisedFeatureError):
        split_supervised_feature_matrix(build_supervised_feature_matrix(frame, config), config)


def test_training_does_not_mutate_inputs() -> None:
    split = _split()
    expected = split["train"].features.copy(deep=True)
    train_supervised_model(split)
    pd.testing.assert_frame_equal(split["train"].features, expected)


def test_training_failures_raise() -> None:
    with pytest.raises(SupervisedTrainingError):
        train_supervised_model({"train": object(), "validation": object()})
