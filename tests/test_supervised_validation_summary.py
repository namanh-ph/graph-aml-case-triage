from __future__ import annotations

import json

import pandas as pd
import pytest

from graph_aml.models import (
    SupervisedValidationError,
    build_supervised_model_quality_summary,
    compare_supervised_score_row_counts,
    summarise_supervised_scores,
    validate_supervised_score_frame,
    validate_supervised_training_result,
)
from graph_aml.models.supervised_scoring import SUPERVISED_SCORE_COLUMNS
from graph_aml.models.supervised_training import SupervisedTrainingResult


def _scores() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "entity_id": "C1",
                "entity_level": "case",
                "model_name": "m",
                "model_version": "v",
                "model_family": "logistic_regression",
                "score_date": "2026-01-01",
                "supervised_score": 0.8,
                "predicted_label": 1,
                "risk_rank": 1,
                "label": 1,
                "label_name": "suspicious",
                "label_timestamp": "2026-01-01",
                "dataset_version": "d",
                "metadata": {},
            }
        ],
        columns=SUPERVISED_SCORE_COLUMNS,
    )


def _result() -> SupervisedTrainingResult:
    return SupervisedTrainingResult(
        model_name="m",
        model_version="v",
        model_family="logistic_regression",
        estimator=object(),
        preprocessing_pipeline=object(),
        feature_names=("a",),
        validation_metrics={"precision": 1.0},
        threshold_metrics=pd.DataFrame({"threshold": [0.5]}),
        top_k_metrics=pd.DataFrame({"top_k": [10]}),
    )


def test_valid_score_frame_and_training_result_pass() -> None:
    validate_supervised_score_frame(_scores())
    validate_supervised_training_result(_result())


def test_invalid_scores_fail() -> None:
    scores = _scores()
    scores.loc[0, "supervised_score"] = 2
    with pytest.raises(SupervisedValidationError):
        validate_supervised_score_frame(scores)


def test_invalid_predicted_labels_fail() -> None:
    scores = _scores()
    scores.loc[0, "predicted_label"] = 3
    with pytest.raises(SupervisedValidationError):
        validate_supervised_score_frame(scores)


def test_invalid_risk_ranks_fail() -> None:
    scores = _scores()
    scores.loc[0, "risk_rank"] = 0
    with pytest.raises(SupervisedValidationError):
        validate_supervised_score_frame(scores)


def test_quality_summary_and_summaries_are_json_serialisable() -> None:
    payload = build_supervised_model_quality_summary(_result(), _scores())
    json.dumps(payload, default=str)
    json.dumps(summarise_supervised_scores(_scores()), default=str)


def test_row_count_comparison_warns_when_counts_differ() -> None:
    comparison = compare_supervised_score_row_counts(_scores(), pd.DataFrame())
    assert comparison["ok"] is False
    assert comparison["warning"] == "row_count_mismatch"
