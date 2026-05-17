from __future__ import annotations

import pandas as pd
import pytest

from graph_aml.models import (
    SUPERVISED_SCORE_COLUMNS,
    SupervisedScoringError,
    build_supervised_feature_matrix,
    compute_binary_classification_metrics,
    compute_precision_recall_at_k,
    compute_threshold_metrics,
    score_supervised_dataset,
    split_supervised_feature_matrix,
    train_supervised_model,
)


def _dataset() -> pd.DataFrame:
    rows = 20
    return pd.DataFrame(
        {
            "case_id": [f"C{i:02d}" for i in range(rows)],
            "case_label": [0, 1] * 10,
            "label_timestamp": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "case_risk_score": [float(i) for i in range(rows)],
            "alert_count": [i % 4 for i in range(rows)],
        }
    )


def test_binary_metrics_include_auc_values() -> None:
    metrics = compute_binary_classification_metrics(
        pd.Series([0, 1, 0, 1]),
        pd.Series([0.1, 0.9, 0.2, 0.8]),
    )
    assert "precision" in metrics
    assert "roc_auc" in metrics
    assert "pr_auc" in metrics


def test_single_class_metrics_warn() -> None:
    metrics = compute_binary_classification_metrics(pd.Series([1, 1]), pd.Series([0.8, 0.9]))
    assert metrics["warning"] == "single_class_labels"


def test_threshold_metrics_are_computed() -> None:
    frame = compute_threshold_metrics(pd.Series([0, 1]), pd.Series([0.2, 0.8]), [0.5, 0.7])
    assert len(frame) == 2


def test_precision_at_k_is_deterministic_and_handles_large_k() -> None:
    frame = compute_precision_recall_at_k(pd.Series([1, 0]), pd.Series([0.9, 0.1]), [1, 10])
    assert float(frame.iloc[0]["precision_at_k"]) == 1.0
    assert int(frame.iloc[1]["row_count"]) == 2


def test_score_frame_columns_scores_and_ranks() -> None:
    matrix = build_supervised_feature_matrix(_dataset())
    result = train_supervised_model(split_supervised_feature_matrix(matrix))
    scores = score_supervised_dataset(result, matrix)
    assert tuple(scores.columns) == SUPERVISED_SCORE_COLUMNS
    assert scores["supervised_score"].between(0, 1).all()
    assert list(scores["risk_rank"]) == list(range(1, len(scores) + 1))


def test_scoring_failures_raise() -> None:
    matrix = build_supervised_feature_matrix(_dataset())
    result = train_supervised_model(split_supervised_feature_matrix(matrix))
    broken = matrix.features.drop(columns=list(matrix.features.columns))
    bad_matrix = type(matrix)(
        matrix.entity_ids,
        matrix.labels,
        broken,
        matrix.timestamps,
        (),
        {},
    )
    with pytest.raises(SupervisedScoringError):
        score_supervised_dataset(result, bad_matrix)
