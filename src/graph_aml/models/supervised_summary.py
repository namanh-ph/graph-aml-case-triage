"""Summary helpers for supervised AML model outputs."""

from __future__ import annotations

import pandas as pd

from graph_aml.models.supervised_training import SupervisedTrainingResult


def summarise_supervised_scores(scores: pd.DataFrame) -> dict[str, object]:
    """Summarise supervised score distribution."""

    if scores.empty or "supervised_score" not in scores.columns:
        return {
            "score_count": 0,
            "min_score": None,
            "max_score": None,
            "mean_score": None,
            "predicted_label_counts": {},
        }
    series = pd.to_numeric(scores["supervised_score"], errors="coerce").dropna()
    return {
        "score_count": int(len(scores)),
        "min_score": None if series.empty else float(series.min()),
        "max_score": None if series.empty else float(series.max()),
        "mean_score": None if series.empty else float(series.mean()),
        "predicted_label_counts": scores.get("predicted_label", pd.Series(dtype=object))
        .dropna()
        .astype(int)
        .value_counts()
        .sort_index()
        .astype(int)
        .to_dict(),
    }


def summarise_supervised_training_result(
    result: SupervisedTrainingResult,
) -> dict[str, object]:
    """Summarise supervised model training result."""

    return {
        "model_name": result.model_name,
        "model_version": result.model_version,
        "model_family": result.model_family,
        "feature_count": len(result.feature_names),
        "feature_names": list(result.feature_names),
        "train_metrics": result.train_metrics,
        "validation_metrics": result.validation_metrics,
        "threshold_metric_count": int(len(result.threshold_metrics)),
        "top_k_metric_count": int(len(result.top_k_metrics)),
        "metadata": result.metadata,
    }


def supervised_training_result_to_dict(
    result: SupervisedTrainingResult,
) -> dict[str, object]:
    """Convert training result to JSON-serialisable metadata."""

    payload = summarise_supervised_training_result(result)
    payload["threshold_metrics"] = result.threshold_metrics.to_dict(orient="records")
    payload["top_k_metrics"] = result.top_k_metrics.to_dict(orient="records")
    return payload
