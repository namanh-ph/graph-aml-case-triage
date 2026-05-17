"""Scoring and metric helpers for supervised AML models."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, cast

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from graph_aml.models.supervised_config import SupervisedModelConfig
from graph_aml.models.supervised_exceptions import SupervisedScoringError
from graph_aml.models.supervised_features import SupervisedFeatureMatrix

if TYPE_CHECKING:
    from graph_aml.models.supervised_training import SupervisedTrainingResult


SUPERVISED_SCORE_COLUMNS = (
    "entity_id",
    "entity_level",
    "model_name",
    "model_version",
    "model_family",
    "score_date",
    "supervised_score",
    "predicted_label",
    "risk_rank",
    "label",
    "label_name",
    "label_timestamp",
    "dataset_version",
    "metadata",
)


def _series(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").fillna(0)


def compute_binary_classification_metrics(
    y_true: pd.Series,
    y_score: pd.Series,
    threshold: float = 0.5,
) -> dict[str, object]:
    """Compute binary classification metrics with single-class safeguards."""

    try:
        labels = _series(y_true).astype(int)
        scores = _series(y_score).clip(0, 1)
        predicted = (scores >= threshold).astype(int)
        metrics: dict[str, object] = {
            "row_count": int(len(labels)),
            "threshold": float(threshold),
            "accuracy": float(accuracy_score(labels, predicted)) if len(labels) else None,
            "precision": float(precision_score(labels, predicted, zero_division=0)),
            "recall": float(recall_score(labels, predicted, zero_division=0)),
            "f1": float(f1_score(labels, predicted, zero_division=0)),
        }
        cm = confusion_matrix(labels, predicted, labels=[0, 1])
        metrics.update(
            {
                "true_negative": int(cm[0, 0]),
                "false_positive": int(cm[0, 1]),
                "false_negative": int(cm[1, 0]),
                "true_positive": int(cm[1, 1]),
            }
        )
        if labels.nunique(dropna=True) == 2:
            metrics["roc_auc"] = float(roc_auc_score(labels, scores))
            metrics["pr_auc"] = float(average_precision_score(labels, scores))
            metrics["warning"] = None
        else:
            metrics["roc_auc"] = None
            metrics["pr_auc"] = None
            metrics["warning"] = "single_class_labels"
        return metrics
    except Exception as exc:
        raise SupervisedScoringError(f"failed to compute metrics: {exc}") from exc


def compute_threshold_metrics(
    y_true: pd.Series,
    y_score: pd.Series,
    thresholds: tuple[float, ...] | list[float],
) -> pd.DataFrame:
    """Compute metrics across a threshold grid."""

    rows = [
        compute_binary_classification_metrics(y_true, y_score, float(value))
        for value in thresholds
    ]
    return pd.DataFrame(rows)


def compute_precision_recall_at_k(
    y_true: pd.Series,
    y_score: pd.Series,
    top_k_values: tuple[int, ...] | list[int],
) -> pd.DataFrame:
    """Compute precision and recall at each K."""

    labels = _series(y_true).astype(int).reset_index(drop=True)
    scores = _series(y_score).reset_index(drop=True)
    ranked = pd.DataFrame({"label": labels, "score": scores}).sort_values(
        ["score"],
        ascending=False,
        kind="mergesort",
    )
    total_positive = int((labels == 1).sum())
    rows: list[dict[str, object]] = []
    for value in top_k_values:
        top_k = int(value)
        window = ranked.head(top_k)
        hits = int((window["label"] == 1).sum())
        denominator = max(1, len(window))
        rows.append(
            {
                "top_k": top_k,
                "row_count": int(len(window)),
                "positive_count": hits,
                "precision_at_k": float(hits / denominator),
                "recall_at_k": float(hits / total_positive) if total_positive else None,
                "status": "computed" if len(window) else "empty",
            }
        )
    return pd.DataFrame(rows)


def _predict_scores(training_result: SupervisedTrainingResult, features: pd.DataFrame) -> pd.Series:
    estimator = cast(Any, training_result.estimator)
    pipeline = cast(Any, training_result.preprocessing_pipeline)
    transformed = pipeline.transform(features)
    if hasattr(estimator, "predict_proba"):
        probabilities = estimator.predict_proba(transformed)
        if probabilities.shape[1] == 1:
            return pd.Series([float(probabilities[0, 0])] * len(features))
        return pd.Series(probabilities[:, 1])
    if hasattr(estimator, "decision_function"):
        raw = pd.Series(estimator.decision_function(transformed))
        minimum = float(raw.min())
        maximum = float(raw.max())
        if maximum == minimum:
            return pd.Series([0.5] * len(raw))
        return (raw - minimum) / (maximum - minimum)
    return pd.Series(estimator.predict(transformed)).astype(float)


def score_supervised_dataset(
    training_result: SupervisedTrainingResult,
    matrix: SupervisedFeatureMatrix,
    config: SupervisedModelConfig | None = None,
) -> pd.DataFrame:
    """Score a supervised feature matrix with a fitted training result."""

    resolved = config or SupervisedModelConfig()
    try:
        scores = _predict_scores(training_result, matrix.features).clip(0, 1)
        frame = pd.DataFrame(
            {
                "entity_id": matrix.entity_ids.astype(str),
                "entity_level": resolved.dataset.level,
                "model_name": training_result.model_name,
                "model_version": training_result.model_version,
                "model_family": training_result.model_family,
                "score_date": date.today().isoformat(),
                "supervised_score": scores.astype(float),
                "predicted_label": (scores >= 0.5).astype(int),
                "label": matrix.labels.astype(int),
                "label_name": matrix.labels.map({1: "suspicious", 0: "not_suspicious"}),
                "label_timestamp": matrix.timestamps,
                "dataset_version": resolved.dataset.dataset_version,
                "metadata": [{"feature_count": len(matrix.feature_names)}] * len(scores),
            }
        )
        frame = frame.sort_values(
            ["supervised_score", "entity_id"],
            ascending=[False, True],
            kind="mergesort",
        ).reset_index(drop=True)
        frame["risk_rank"] = range(1, len(frame) + 1)
        return frame.reindex(columns=SUPERVISED_SCORE_COLUMNS)
    except Exception as exc:
        raise SupervisedScoringError(f"failed to score supervised dataset: {exc}") from exc
