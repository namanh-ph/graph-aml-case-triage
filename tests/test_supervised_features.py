from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.models import (
    SupervisedDatasetConfig,
    SupervisedFeatureError,
    SupervisedModelConfig,
    SupervisedSplitConfig,
    build_supervised_feature_matrix,
    infer_supervised_feature_columns,
    split_supervised_feature_matrix,
    validate_supervised_training_data,
)


def _dataset(rows: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": [f"C{i:03d}" for i in range(rows)],
            "dataset_version": ["v1"] * rows,
            "case_label": [0, 1] * (rows // 2),
            "label_name": ["n", "s"] * (rows // 2),
            "label_timestamp": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "case_risk_score": list(range(rows)),
            "alert_count": [1] * rows,
            "risk_band": ["high"] * rows,
            "metadata": [{}] * rows,
        }
    )


def test_feature_inference_excludes_ids_labels_and_metadata() -> None:
    columns = infer_supervised_feature_columns(_dataset())
    assert "case_id" not in columns
    assert "case_label" not in columns
    assert "label_timestamp" not in columns
    assert "metadata" not in columns


def test_feature_matrix_contains_numeric_features_only() -> None:
    matrix = build_supervised_feature_matrix(_dataset())
    assert tuple(matrix.features.columns) == ("case_risk_score", "alert_count")


def test_binary_labels_are_validated() -> None:
    matrix = build_supervised_feature_matrix(_dataset())
    validate_supervised_training_data(matrix)


def test_minimum_row_thresholds_are_enforced() -> None:
    config = SupervisedModelConfig(dataset=SupervisedDatasetConfig(min_rows=20))
    with pytest.raises(SupervisedFeatureError):
        validate_supervised_training_data(build_supervised_feature_matrix(_dataset()), config)


def test_minimum_class_thresholds_are_enforced() -> None:
    frame = _dataset()
    frame["case_label"] = 0
    config = SupervisedModelConfig(
        dataset=SupervisedDatasetConfig(min_positive_labels=1, allow_single_class_training=False)
    )
    with pytest.raises(SupervisedFeatureError):
        validate_supervised_training_data(build_supervised_feature_matrix(frame), config)


def test_time_split_uses_latest_rows_for_validation() -> None:
    matrix = build_supervised_feature_matrix(_dataset())
    split = split_supervised_feature_matrix(matrix)
    validation = split["validation"]
    assert list(validation.entity_ids.tail(1))[0] == "C011"


def test_stratified_random_split_is_deterministic() -> None:
    config = SupervisedModelConfig(split=SupervisedSplitConfig(strategy="stratified_random"))
    first = split_supervised_feature_matrix(build_supervised_feature_matrix(_dataset()), config)
    second = split_supervised_feature_matrix(build_supervised_feature_matrix(_dataset()), config)
    assert list(first["validation"].entity_ids) == list(second["validation"].entity_ids)


def test_feature_builders_do_not_mutate_inputs() -> None:
    frame = _dataset()
    expected = frame.copy(deep=True)
    build_supervised_feature_matrix(frame)
    pd.testing.assert_frame_equal(frame, expected)


def test_malformed_inputs_raise() -> None:
    with pytest.raises(SupervisedFeatureError):
        build_supervised_feature_matrix(pd.DataFrame())
