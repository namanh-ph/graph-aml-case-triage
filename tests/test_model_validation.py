"""Tests for model validation helpers."""

import pandas as pd
import pytest

from graph_aml.models import (
    ModelValidationError,
    build_anomaly_score_quality_summary,
    compare_anomaly_score_row_counts,
    validate_anomaly_score_frame,
    validate_model_feature_frame,
    validate_prepared_anomaly_score_frame,
)


def feature_frame() -> pd.DataFrame:
    return pd.DataFrame({"account_id": ["A1", "A2"], "f1": [1.0, 2.0]})


def scores() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "account_id": ["A1", "A2"],
            "anomaly_score": [10.0, 99.0],
            "anomaly_score_raw": [-0.1, -0.3],
            "is_anomaly": [False, True],
            "anomaly_rank": [2, 1],
            "risk_band": ["low", "high"],
        }
    )


def prepared_scores() -> pd.DataFrame:
    frame = scores()
    for column, value in {
        "score_date": "2026-01-01",
        "model_name": "m",
        "model_version": "v",
        "model_run_id": "run",
        "feature_date": None,
        "account_feature_version": None,
        "graph_feature_version": None,
        "graph_build_id": None,
        "feature_names": [[]],
        "model_parameters": [{}],
        "preprocessing_metadata": [{}],
        "metrics": [{}],
        "metadata": [{}],
        "scored_at": "2026-01-01T00:00:00Z",
    }.items():
        if isinstance(value, list | dict):
            frame[column] = [value for _ in range(len(frame))]
        else:
            frame[column] = value
    return frame


def test_valid_frames_pass_validation() -> None:
    validate_model_feature_frame(feature_frame())
    validate_anomaly_score_frame(scores())
    validate_prepared_anomaly_score_frame(prepared_scores())


def test_invalid_feature_and_score_frames_raise() -> None:
    missing = feature_frame()
    missing.loc[0, "account_id"] = None
    with pytest.raises(ModelValidationError):
        validate_model_feature_frame(missing)
    duplicate = scores()
    duplicate.loc[1, "account_id"] = "A1"
    with pytest.raises(ModelValidationError):
        validate_anomaly_score_frame(duplicate)
    invalid_score = scores()
    invalid_score.loc[0, "anomaly_score"] = 101
    with pytest.raises(ModelValidationError):
        validate_anomaly_score_frame(invalid_score)
    invalid_band = scores()
    invalid_band.loc[0, "risk_band"] = "critical"
    with pytest.raises(ModelValidationError):
        validate_anomaly_score_frame(invalid_band)


def test_prepared_frame_missing_metadata_fails() -> None:
    with pytest.raises(ModelValidationError):
        validate_prepared_anomaly_score_frame(prepared_scores().drop(columns=["metadata"]))


def test_row_count_comparison_and_quality_summary() -> None:
    assert compare_anomaly_score_row_counts(scores(), scores())["status"] == "ok"
    assert compare_anomaly_score_row_counts(scores(), scores().head(1))["status"] == "warning"
    summary = build_anomaly_score_quality_summary(scores())
    assert summary["row_count"] == 2
    assert summary["risk_band_counts"] == {"high": 1, "low": 1}
