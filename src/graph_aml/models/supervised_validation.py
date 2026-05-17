"""Validation helpers for supervised AML model outputs."""

from __future__ import annotations

import pandas as pd

from graph_aml.models.supervised_exceptions import SupervisedValidationError
from graph_aml.models.supervised_scoring import SUPERVISED_SCORE_COLUMNS
from graph_aml.models.supervised_summary import summarise_supervised_scores
from graph_aml.models.supervised_training import SupervisedTrainingResult


def validate_supervised_score_frame(scores: pd.DataFrame) -> None:
    """Validate supervised score frame shape and bounded values."""

    if not isinstance(scores, pd.DataFrame):
        raise SupervisedValidationError("scores must be a DataFrame")
    missing = set(SUPERVISED_SCORE_COLUMNS).difference(scores.columns)
    if missing:
        raise SupervisedValidationError(f"supervised scores missing columns: {sorted(missing)}")
    if scores.empty:
        return
    score_values = pd.to_numeric(scores["supervised_score"], errors="coerce")
    if score_values.isna().any() or not score_values.between(0, 1).all():
        raise SupervisedValidationError("supervised scores must be in [0, 1]")
    labels = pd.to_numeric(scores["predicted_label"], errors="coerce")
    if not set(labels.dropna().astype(int).unique()).issubset({0, 1}):
        raise SupervisedValidationError("predicted labels must be 0 or 1")
    ranks = pd.to_numeric(scores["risk_rank"], errors="coerce")
    if ranks.isna().any() or (ranks < 1).any():
        raise SupervisedValidationError("risk ranks must be positive")
    for column in ("entity_id", "entity_level", "model_name", "model_version", "model_family"):
        if scores[column].astype(str).str.strip().eq("").any():
            raise SupervisedValidationError(f"{column} must be non-empty")


def validate_supervised_training_result(result: SupervisedTrainingResult) -> None:
    """Validate fitted supervised training result metadata."""

    if not result.model_name.strip() or not result.model_version.strip():
        raise SupervisedValidationError("model metadata must be non-empty")
    if result.model_family not in {"logistic_regression", "random_forest"}:
        raise SupervisedValidationError("invalid model family")
    if not result.feature_names:
        raise SupervisedValidationError("training result must include features")
    if result.estimator is None or result.preprocessing_pipeline is None:
        raise SupervisedValidationError("training result must include fitted objects")


def build_supervised_model_quality_summary(
    training_result: SupervisedTrainingResult,
    scores: pd.DataFrame,
) -> dict[str, object]:
    """Build JSON-serialisable supervised quality summary."""

    validate_supervised_training_result(training_result)
    validate_supervised_score_frame(scores)
    return {
        **summarise_supervised_scores(scores),
        "model_family": training_result.model_family,
        "feature_count": len(training_result.feature_names),
        "validation_metrics": training_result.validation_metrics,
        "threshold_metrics": training_result.threshold_metrics.to_dict(orient="records"),
        "top_k_metrics": training_result.top_k_metrics.to_dict(orient="records"),
    }


def compare_supervised_score_row_counts(
    source_scores: pd.DataFrame,
    persisted_scores: pd.DataFrame,
) -> dict[str, object]:
    """Compare generated and persisted score counts."""

    source_count = int(len(source_scores))
    persisted_count = int(len(persisted_scores))
    return {
        "source_count": source_count,
        "persisted_count": persisted_count,
        "ok": source_count == persisted_count,
        "warning": None if source_count == persisted_count else "row_count_mismatch",
    }
