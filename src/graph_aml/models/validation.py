"""Validation helpers for model feature frames and anomaly scores."""

from __future__ import annotations

import json

import pandas as pd

from graph_aml.models.exceptions import ModelValidationError

ANOMALY_SCORE_COLUMNS = (
    "account_id",
    "anomaly_score",
    "anomaly_score_raw",
    "is_anomaly",
    "anomaly_rank",
    "risk_band",
)

PREPARED_ANOMALY_SCORE_COLUMNS = (
    "account_id",
    "score_date",
    "model_name",
    "model_version",
    "model_run_id",
    "feature_date",
    "account_feature_version",
    "graph_feature_version",
    "graph_build_id",
    "anomaly_score",
    "anomaly_score_raw",
    "anomaly_rank",
    "is_anomaly",
    "risk_band",
    "feature_names",
    "model_parameters",
    "preprocessing_metadata",
    "metrics",
    "metadata",
    "scored_at",
)


def _json_safe(value: object) -> object:
    try:
        json.dumps(value, default=str)
        return value
    except TypeError:
        return str(value)


def validate_model_feature_frame(feature_frame: pd.DataFrame) -> None:
    """Validate a model feature frame before preprocessing."""

    if not isinstance(feature_frame, pd.DataFrame):
        raise ModelValidationError("feature_frame must be a DataFrame")
    if "account_id" not in feature_frame.columns:
        raise ModelValidationError("feature_frame must include account_id")
    if feature_frame["account_id"].isna().any():
        raise ModelValidationError("account_id values must be non-null")
    if feature_frame["account_id"].duplicated().any():
        raise ModelValidationError("account_id values must be unique")
    if len([column for column in feature_frame.columns if column != "account_id"]) == 0:
        raise ModelValidationError("feature_frame must include model features")


def validate_anomaly_score_frame(scores: pd.DataFrame) -> None:
    """Validate anomaly score output rows."""

    if not isinstance(scores, pd.DataFrame):
        raise ModelValidationError("scores must be a DataFrame")
    missing = set(ANOMALY_SCORE_COLUMNS).difference(scores.columns)
    if missing:
        raise ModelValidationError(f"scores missing required columns: {sorted(missing)}")
    if scores["account_id"].isna().any():
        raise ModelValidationError("account_id values must be non-null")
    if scores["account_id"].duplicated().any():
        raise ModelValidationError("account_id values must be unique")
    anomaly_score = pd.to_numeric(scores["anomaly_score"], errors="coerce")
    if anomaly_score.isna().any() or (anomaly_score < 0).any() or (anomaly_score > 100).any():
        raise ModelValidationError("anomaly_score values must be between 0 and 100")
    ranks = pd.to_numeric(scores["anomaly_rank"], errors="coerce")
    if ranks.isna().any() or (ranks < 1).any() or (ranks % 1 != 0).any():
        raise ModelValidationError("anomaly_rank values must be positive integers")
    invalid_bands = set(scores["risk_band"].astype(str)).difference({"low", "medium", "high"})
    if invalid_bands:
        raise ModelValidationError(f"invalid risk bands: {sorted(invalid_bands)}")


def validate_prepared_anomaly_score_frame(prepared_scores: pd.DataFrame) -> None:
    """Validate anomaly scores prepared for database persistence."""

    missing = set(PREPARED_ANOMALY_SCORE_COLUMNS).difference(prepared_scores.columns)
    if missing:
        raise ModelValidationError(f"prepared scores missing required columns: {sorted(missing)}")
    validate_anomaly_score_frame(prepared_scores)
    required_text = ("score_date", "model_name", "model_version", "model_run_id", "scored_at")
    for column in required_text:
        if prepared_scores[column].isna().any():
            raise ModelValidationError(f"{column} values must be non-null")


def build_anomaly_score_quality_summary(scores: pd.DataFrame) -> dict[str, object]:
    """Build JSON-serialisable anomaly score quality diagnostics."""

    if scores.empty:
        return {
            "row_count": 0,
            "unique_account_count": 0,
            "anomaly_count": 0,
            "risk_band_counts": {},
            "min_score": None,
            "max_score": None,
            "mean_score": None,
            "missing_account_ids": 0,
            "duplicate_account_ids": 0,
        }
    score_values = pd.to_numeric(scores.get("anomaly_score"), errors="coerce")
    risk_band_counts = (
        scores.get("risk_band", pd.Series(dtype="object"))
        .astype(str)
        .value_counts()
        .sort_index()
        .to_dict()
    )
    return {
        "row_count": int(len(scores)),
        "unique_account_count": int(scores["account_id"].nunique(dropna=True))
        if "account_id" in scores
        else 0,
        "anomaly_count": int(scores.get("is_anomaly", pd.Series(dtype=bool)).fillna(False).sum()),
        "risk_band_counts": {str(key): int(value) for key, value in risk_band_counts.items()},
        "min_score": float(score_values.min()) if not score_values.empty else None,
        "max_score": float(score_values.max()) if not score_values.empty else None,
        "mean_score": float(score_values.mean()) if not score_values.empty else None,
        "missing_account_ids": int(scores["account_id"].isna().sum())
        if "account_id" in scores
        else 0,
        "duplicate_account_ids": int(scores["account_id"].duplicated().sum())
        if "account_id" in scores
        else 0,
    }


def compare_anomaly_score_row_counts(
    source_scores: pd.DataFrame,
    persisted_scores: pd.DataFrame,
) -> dict[str, object]:
    """Compare source and persisted anomaly score row counts."""

    source_count = int(len(source_scores))
    persisted_count = int(len(persisted_scores))
    warnings: list[str] = []
    if source_count != persisted_count:
        warnings.append(
            f"source row count {source_count} differs from persisted row count {persisted_count}"
        )
    return {
        "source_row_count": source_count,
        "persisted_row_count": persisted_count,
        "status": "ok" if not warnings else "warning",
        "warnings": warnings,
    }
