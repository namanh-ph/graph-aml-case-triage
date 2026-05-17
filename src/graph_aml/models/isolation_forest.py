"""Isolation Forest training and scoring for account-level anomaly detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import Engine

from graph_aml.models.config import IsolationForestModelConfig
from graph_aml.models.exceptions import (
    ModelFeatureInputError,
    ModelPersistenceError,
    ModelTrainingError,
)
from graph_aml.models.feature_inputs import (
    build_model_feature_frame,
    read_model_feature_inputs,
)
from graph_aml.models.preprocessing import (
    ModelPreprocessingResult,
    fit_transform_model_features,
    transform_model_features,
)
from graph_aml.models.summary import summarise_anomaly_scores


@dataclass(frozen=True)
class IsolationForestTrainingResult:
    """Trained Isolation Forest model and reproducible preprocessing state."""

    model: object
    preprocessing: ModelPreprocessingResult
    model_name: str
    model_version: str
    trained_at: datetime
    training_row_count: int
    feature_names: tuple[str, ...]
    parameters: dict[str, object] = field(default_factory=dict)
    metrics: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AnomalyScoreResult:
    """Account-level anomaly scores and model output metadata."""

    scores: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def build_isolation_forest_model(
    config: IsolationForestModelConfig | None = None,
) -> IsolationForest:
    """Build a configured scikit-learn Isolation Forest instance."""

    resolved = IsolationForestModelConfig() if config is None else config
    return IsolationForest(
        n_estimators=resolved.n_estimators,
        contamination=resolved.contamination,
        max_samples=resolved.max_samples,
        max_features=resolved.max_features,
        bootstrap=resolved.bootstrap,
        n_jobs=resolved.n_jobs,
        random_state=resolved.random_state,
    )


def _model_parameters(config: IsolationForestModelConfig) -> dict[str, object]:
    return {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "random_state": config.random_state,
        "n_estimators": config.n_estimators,
        "contamination": config.contamination,
        "max_samples": config.max_samples,
        "max_features": config.max_features,
        "bootstrap": config.bootstrap,
        "n_jobs": config.n_jobs,
        "imputation_strategy": config.imputation_strategy,
        "scaling_strategy": config.scaling_strategy,
    }


def train_isolation_forest_model(
    feature_frame: pd.DataFrame,
    config: IsolationForestModelConfig | None = None,
    trained_at: datetime | None = None,
) -> IsolationForestTrainingResult:
    """Train an Isolation Forest on account-level feature rows."""

    resolved = IsolationForestModelConfig() if config is None else config
    try:
        if len(feature_frame) < resolved.min_training_rows:
            raise ModelTrainingError(
                f"at least {resolved.min_training_rows} rows are required for training"
            )
        preprocessing = fit_transform_model_features(feature_frame, resolved)
        model = build_isolation_forest_model(resolved)
        matrix = cast(np.ndarray, preprocessing.matrix)
        model.fit(matrix)
        timestamp = datetime.now(UTC) if trained_at is None else trained_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        metrics: dict[str, object] = {
            "training_row_count": len(feature_frame),
            "feature_count": len(preprocessing.feature_names),
        }
        return IsolationForestTrainingResult(
            model=model,
            preprocessing=preprocessing,
            model_name=resolved.model_name,
            model_version=resolved.model_version,
            trained_at=timestamp.astimezone(UTC),
            training_row_count=len(feature_frame),
            feature_names=preprocessing.feature_names,
            parameters=_model_parameters(resolved),
            metrics=metrics,
        )
    except ModelTrainingError:
        raise
    except (ModelFeatureInputError, ValueError) as exc:
        raise ModelTrainingError(f"Failed to train Isolation Forest: {exc}") from exc


def _risk_band(score: float, config: IsolationForestModelConfig) -> str:
    if score >= config.score_percentile_high:
        return "high"
    if score >= config.score_percentile_medium:
        return "medium"
    return "low"


def score_isolation_forest_model(
    training_result: IsolationForestTrainingResult,
    feature_frame: pd.DataFrame,
    config: IsolationForestModelConfig | None = None,
) -> AnomalyScoreResult:
    """Score account rows with a trained Isolation Forest."""

    resolved = IsolationForestModelConfig() if config is None else config
    try:
        preprocessing = transform_model_features(
            feature_frame,
            training_result.preprocessing,
            resolved,
        )
        matrix = cast(np.ndarray, preprocessing.matrix)
        model = cast(Any, training_result.model)
        decision = np.asarray(model.decision_function(matrix), dtype=float)
        score_samples = np.asarray(model.score_samples(matrix), dtype=float)
        prediction = np.asarray(model.predict(matrix), dtype=int)
        raw_anomaly = -decision
        percentile = pd.Series(raw_anomaly).rank(method="first", pct=True).to_numpy() * 100.0
        rows = []
        for idx, account_id in enumerate(preprocessing.account_ids):
            score = float(percentile[idx])
            rows.append(
                {
                    "account_id": account_id,
                    "anomaly_score": score,
                    "anomaly_score_raw": float(score_samples[idx]),
                    "is_anomaly": bool(prediction[idx] == -1),
                    "risk_band": _risk_band(score, resolved),
                }
            )
        scores = pd.DataFrame(rows)
        if not scores.empty:
            scores = scores.sort_values(
                ["anomaly_score", "account_id"],
                ascending=[False, True],
            ).reset_index(drop=True)
            scores["anomaly_rank"] = range(1, len(scores) + 1)
            scores = scores.loc[
                :,
                [
                    "account_id",
                    "anomaly_score",
                    "anomaly_score_raw",
                    "is_anomaly",
                    "anomaly_rank",
                    "risk_band",
                ],
            ]
        summary = summarise_anomaly_scores(scores)
        metadata = {
            "model_name": training_result.model_name,
            "model_version": training_result.model_version,
            "feature_names": list(training_result.feature_names),
            "score_percentile_high": resolved.score_percentile_high,
            "score_percentile_medium": resolved.score_percentile_medium,
        }
        return AnomalyScoreResult(scores=scores, summary=summary, metadata=metadata)
    except (ModelFeatureInputError, ValueError) as exc:
        raise ModelTrainingError(f"Failed to score Isolation Forest: {exc}") from exc


def train_and_score_isolation_forest(
    feature_frame: pd.DataFrame,
    config: IsolationForestModelConfig | None = None,
) -> tuple[IsolationForestTrainingResult, AnomalyScoreResult]:
    """Train and immediately score the same account feature frame."""

    training_result = train_isolation_forest_model(feature_frame, config)
    score_result = score_isolation_forest_model(training_result, feature_frame, config)
    return training_result, score_result


def train_score_and_persist_isolation_forest(
    engine: Engine,
    config: IsolationForestModelConfig | None = None,
    persistence_config: object | None = None,
    limit: int | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> tuple[IsolationForestTrainingResult, AnomalyScoreResult, object]:
    """Read model inputs, train, score, and persist anomaly scores."""

    resolved = IsolationForestModelConfig() if config is None else config
    try:
        inputs = read_model_feature_inputs(engine, resolved, limit=limit)
        feature_frame = build_model_feature_frame(
            inputs["account_features"],
            inputs.get("graph_features"),
            resolved,
        )
        training_result, score_result = train_and_score_isolation_forest(
            feature_frame,
            resolved,
        )
        from graph_aml.models.persistence import persist_anomaly_scores

        persistence_result = persist_anomaly_scores(
            engine,
            score_result,
            training_result,
            cast(Any, persistence_config),
            extra_metadata=extra_metadata,
        )
        return training_result, score_result, persistence_result
    except (ModelTrainingError, ModelFeatureInputError, ModelPersistenceError):
        raise
    except Exception as exc:
        raise ModelTrainingError(f"Isolation Forest workflow failed: {exc}") from exc


def log_isolation_forest_mlflow_run(
    training_result: IsolationForestTrainingResult,
    score_result: AnomalyScoreResult,
    config: IsolationForestModelConfig | None = None,
    artefact_paths: dict[str, Path] | None = None,
) -> str | None:
    """Optionally log Isolation Forest metadata and artefacts to MLflow."""

    resolved = IsolationForestModelConfig() if config is None else config
    if not resolved.mlflow_enabled:
        return None
    try:
        import mlflow

        mlflow.set_experiment(resolved.mlflow_experiment_name)
        with mlflow.start_run(run_name=training_result.model_version) as run:
            for key, value in training_result.parameters.items():
                mlflow.log_param(key, value)
            mlflow.log_metric("training_row_count", training_result.training_row_count)
            mlflow.log_metric("feature_count", len(training_result.feature_names))
            for key, value in score_result.summary.items():
                if isinstance(value, int | float) and value is not None:
                    mlflow.log_metric(str(key), float(value))
            for path in (artefact_paths or {}).values():
                mlflow.log_artifact(str(path))
            return str(run.info.run_id)
    except Exception as exc:
        raise ModelTrainingError(f"Failed to log MLflow run: {exc}") from exc
