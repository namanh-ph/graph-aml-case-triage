"""Local artefact writers for Isolation Forest anomaly scoring."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.models.exceptions import ModelPersistenceError, ModelValidationError
from graph_aml.models.isolation_forest import (
    AnomalyScoreResult,
    IsolationForestTrainingResult,
)
from graph_aml.models.persistence import AnomalyScorePersistenceResult
from graph_aml.models.summary import (
    anomaly_score_result_to_dict,
    summarise_training_result,
)


def _write_json(payload: object, output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        raise ModelPersistenceError(f"Failed to write model JSON artefact: {exc}") from exc
    return path


def write_anomaly_scores_csv(
    scores: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/account_anomaly_scores.csv",
) -> Path:
    """Write anomaly scores as CSV."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        scores.to_csv(path, index=False)
    except Exception as exc:
        raise ModelPersistenceError(f"Failed to write anomaly score CSV: {exc}") from exc
    return path


def write_anomaly_scores_json(
    scores: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/account_anomaly_scores.json",
) -> Path:
    """Write anomaly scores as JSON records."""

    records = scores.astype(object).where(pd.notna(scores), None).to_dict(orient="records")
    return _write_json(records, output_path)


def write_isolation_forest_training_summary_json(
    training_result: IsolationForestTrainingResult,
    output_path: Path | str = "reports/model_validation/isolation_forest_training_summary.json",
) -> Path:
    """Write Isolation Forest training summary JSON."""

    if not isinstance(training_result, IsolationForestTrainingResult):
        raise ModelValidationError("training_result must be IsolationForestTrainingResult")
    return _write_json(summarise_training_result(training_result), output_path)


def write_anomaly_score_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/account_anomaly_score_summary.json",
) -> Path:
    """Write anomaly score summary JSON."""

    if not isinstance(summary, dict):
        raise ModelValidationError("summary must be a dictionary")
    return _write_json(summary, output_path)


def _persistence_result_to_dict(result: AnomalyScorePersistenceResult) -> dict[str, object]:
    return {
        "rows_prepared": result.rows_prepared,
        "rows_persisted": result.rows_persisted,
        "unique_account_count": result.unique_account_count,
        "score_date": result.score_date,
        "model_name": result.model_name,
        "model_version": result.model_version,
        "model_run_id": result.model_run_id,
        "persisted": result.persisted,
        "metadata": result.metadata,
        "summary": result.summary,
    }


def write_anomaly_score_persistence_summary_json(
    result: AnomalyScorePersistenceResult,
    output_path: Path | str = "reports/model_validation/anomaly_score_persistence_summary.json",
) -> Path:
    """Write anomaly score persistence summary JSON."""

    if not isinstance(result, AnomalyScorePersistenceResult):
        raise ModelValidationError("result must be AnomalyScorePersistenceResult")
    return _write_json(_persistence_result_to_dict(result), output_path)


def generate_isolation_forest_artefacts(
    training_result: IsolationForestTrainingResult,
    score_result: AnomalyScoreResult,
    persistence_result: AnomalyScorePersistenceResult | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write Isolation Forest training, scoring, and optional persistence artefacts."""

    if not isinstance(score_result, AnomalyScoreResult):
        raise ModelValidationError("score_result must be AnomalyScoreResult")
    directory = Path(output_dir)
    paths = {
        "scores_csv": write_anomaly_scores_csv(
            score_result.scores,
            directory / "account_anomaly_scores.csv",
        ),
        "scores_json": write_anomaly_scores_json(
            score_result.scores,
            directory / "account_anomaly_scores.json",
        ),
        "training_summary_json": write_isolation_forest_training_summary_json(
            training_result,
            directory / "isolation_forest_training_summary.json",
        ),
        "score_summary_json": write_anomaly_score_summary_json(
            anomaly_score_result_to_dict(score_result),
            directory / "account_anomaly_score_summary.json",
        ),
    }
    if persistence_result is not None:
        paths["persistence_summary_json"] = write_anomaly_score_persistence_summary_json(
            persistence_result,
            directory / "anomaly_score_persistence_summary.json",
        )
    return paths
