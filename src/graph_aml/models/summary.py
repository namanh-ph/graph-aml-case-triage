"""Summary helpers for Isolation Forest model outputs."""

from __future__ import annotations

from typing import Any

import pandas as pd


def summarise_anomaly_scores(scores: pd.DataFrame) -> dict[str, object]:
    """Return compact anomaly score distribution metrics."""

    if scores.empty or "anomaly_score" not in scores:
        return {
            "row_count": 0,
            "anomaly_count": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "min_score": None,
            "max_score": None,
            "mean_score": None,
        }
    values = pd.to_numeric(scores["anomaly_score"], errors="coerce")
    bands = scores.get("risk_band", pd.Series(dtype="object")).astype(str)
    return {
        "row_count": int(len(scores)),
        "anomaly_count": int(scores.get("is_anomaly", pd.Series(dtype=bool)).fillna(False).sum()),
        "high_risk_count": int((bands == "high").sum()),
        "medium_risk_count": int((bands == "medium").sum()),
        "low_risk_count": int((bands == "low").sum()),
        "min_score": float(values.min()) if not values.empty else None,
        "max_score": float(values.max()) if not values.empty else None,
        "mean_score": float(values.mean()) if not values.empty else None,
    }


def summarise_training_result(training_result: Any) -> dict[str, object]:
    """Return JSON-serialisable training metadata."""

    return {
        "model_name": str(training_result.model_name),
        "model_version": str(training_result.model_version),
        "trained_at": training_result.trained_at.isoformat(),
        "training_row_count": int(training_result.training_row_count),
        "feature_count": int(len(training_result.feature_names)),
        "feature_names": list(training_result.feature_names),
        "parameters": dict(training_result.parameters),
        "metrics": dict(training_result.metrics),
    }


def anomaly_score_result_to_dict(result: Any) -> dict[str, object]:
    """Convert an anomaly score result to a JSON-ready dictionary."""

    records = (
        result.scores.astype(object).where(pd.notna(result.scores), None).to_dict(orient="records")
    )
    return {
        "scores": records,
        "summary": dict(result.summary),
        "metadata": dict(result.metadata),
    }
