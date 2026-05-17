from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from graph_aml.models import (
    generate_supervised_model_artefacts,
    write_supervised_metrics_json,
    write_supervised_model_artifact,
    write_supervised_model_card_md,
    write_supervised_scores_csv,
    write_supervised_threshold_metrics_csv,
    write_supervised_top_k_metrics_csv,
)
from graph_aml.models.supervised_scoring import SUPERVISED_SCORE_COLUMNS
from graph_aml.models.supervised_training import SupervisedTrainingResult


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
        metadata={"dataset_version": "d"},
    )


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


def test_csv_and_json_writers(tmp_path) -> None:
    assert write_supervised_scores_csv(_scores(), tmp_path / "scores.csv").exists()
    metrics = write_supervised_metrics_json(_result(), tmp_path / "metrics.json")
    assert json.loads(metrics.read_text(encoding="utf-8"))["model_version"] == "v"
    assert write_supervised_threshold_metrics_csv(_result(), tmp_path / "threshold.csv").exists()
    assert write_supervised_top_k_metrics_csv(_result(), tmp_path / "topk.csv").exists()


def test_model_card_and_artifact_writers(tmp_path) -> None:
    card = write_supervised_model_card_md(_result(), _scores(), tmp_path / "card.md")
    assert "Supervised AML Baseline" in card.read_text(encoding="utf-8")
    artifact = write_supervised_model_artifact(_result(), tmp_path / "model.joblib")
    assert joblib.load(artifact)["feature_names"] == ("a",)


def test_high_level_generator_writes_expected_paths(tmp_path) -> None:
    paths = generate_supervised_model_artefacts(_result(), _scores(), tmp_path)
    assert "supervised_model_card_md" in paths
    assert all(isinstance(path, Path) and path.exists() for path in paths.values())
