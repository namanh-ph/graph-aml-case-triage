"""Persistence utilities for supervised AML model outputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.models.supervised_config import SupervisedModelConfig
from graph_aml.models.supervised_exceptions import SupervisedPersistenceError
from graph_aml.models.supervised_training import SupervisedTrainingResult


@dataclass(frozen=True)
class SupervisedModelPersistenceConfig:
    model_name: str = "supervised_aml_baseline"
    model_version: str = "supervised_aml_baseline_v1"
    dataset_version: str = "supervised_readiness_v1"
    batch_size: int = 1000
    write_model_run: bool = True
    write_scores: bool = True
    write_audit: bool = True
    artefact_output_dir: str = "reports/model_validation"


@dataclass(frozen=True)
class SupervisedModelPersistenceResult:
    run_id: str | None = None
    scores_persisted: int = 0
    model_run_persisted: bool = False
    model_name: str | None = None
    model_version: str | None = None
    dataset_version: str | None = None
    entity_level: str | None = None
    persisted: bool = False
    artefact_paths: dict[str, str] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


def validate_supervised_model_persistence_config(
    config: SupervisedModelPersistenceConfig,
) -> None:
    """Validate supervised persistence configuration."""

    if not config.model_name.strip() or not config.model_version.strip():
        raise SupervisedPersistenceError("model name and version must be non-empty")
    if not config.dataset_version.strip():
        raise SupervisedPersistenceError("dataset_version must be non-empty")
    if config.batch_size <= 0:
        raise SupervisedPersistenceError("batch_size must be positive")
    for value in (config.write_model_run, config.write_scores, config.write_audit):
        if not isinstance(value, bool):
            raise SupervisedPersistenceError("persistence flags must be boolean")


def build_supervised_run_id(
    training_result: SupervisedTrainingResult,
    config: SupervisedModelConfig | None = None,
) -> str:
    """Build a deterministic model run ID from model metadata."""

    resolved = config or SupervisedModelConfig()
    payload = {
        "model_name": training_result.model_name,
        "model_version": training_result.model_version,
        "model_family": training_result.model_family,
        "dataset_version": resolved.dataset.dataset_version,
        "features": list(training_result.feature_names),
        "validation_metrics": training_result.validation_metrics,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return f"supervised_{digest[:24]}"


def build_supervised_score_upsert_sql() -> str:
    """Return upsert SQL for supervised scores."""

    return """
    INSERT INTO mart.supervised_model_scores (
        entity_id, entity_level, model_name, model_version, model_family, score_date,
        supervised_score, predicted_label, risk_rank, label, label_name, label_timestamp,
        dataset_version, metadata
    ) VALUES (
        :entity_id, :entity_level, :model_name, :model_version, :model_family, :score_date,
        :supervised_score, :predicted_label, :risk_rank, :label, :label_name, :label_timestamp,
        :dataset_version, CAST(:metadata AS jsonb)
    )
    ON CONFLICT (entity_id, entity_level, model_name, model_version, score_date)
    DO UPDATE SET
        supervised_score = EXCLUDED.supervised_score,
        predicted_label = EXCLUDED.predicted_label,
        risk_rank = EXCLUDED.risk_rank,
        label = EXCLUDED.label,
        label_name = EXCLUDED.label_name,
        label_timestamp = EXCLUDED.label_timestamp,
        dataset_version = EXCLUDED.dataset_version,
        metadata = EXCLUDED.metadata,
        updated_at = CURRENT_TIMESTAMP
    """


def build_supervised_model_run_insert_sql() -> str:
    """Return insert SQL for supervised model run metadata."""

    return """
    INSERT INTO governance.supervised_model_runs (
        run_id, model_name, model_version, model_family, dataset_version, entity_level,
        feature_names, train_metrics, validation_metrics, threshold_metrics,
        top_k_metrics, artefact_paths, metadata
    ) VALUES (
        :run_id, :model_name, :model_version, :model_family, :dataset_version, :entity_level,
        CAST(:feature_names AS jsonb), CAST(:train_metrics AS jsonb),
        CAST(:validation_metrics AS jsonb), CAST(:threshold_metrics AS jsonb),
        CAST(:top_k_metrics AS jsonb), CAST(:artefact_paths AS jsonb),
        CAST(:metadata AS jsonb)
    )
    ON CONFLICT (run_id) DO NOTHING
    """


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    prepared = frame.astype(object).where(pd.notna(frame), cast(Any, None)).copy()
    if "metadata" in prepared.columns:
        prepared["metadata"] = [
            json.dumps(value or {}, sort_keys=True, default=str)
            for value in prepared["metadata"].tolist()
        ]
    return cast(list[dict[str, object]], prepared.to_dict(orient="records"))


def upsert_supervised_scores(
    engine: Engine,
    scores: pd.DataFrame,
    batch_size: int = 1000,
) -> int:
    """Upsert supervised score rows."""

    if batch_size <= 0:
        raise SupervisedPersistenceError("batch_size must be positive")
    if scores.empty:
        return 0
    sql = text(build_supervised_score_upsert_sql())
    rows = _records(scores)
    try:
        with engine.begin() as connection:
            for start in range(0, len(rows), batch_size):
                connection.execute(sql, rows[start : start + batch_size])
        return len(rows)
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to upsert supervised scores: {exc}") from exc


def insert_supervised_model_run(
    engine: Engine,
    run_id: str,
    training_result: SupervisedTrainingResult,
    scores: pd.DataFrame,
    artefact_paths: dict[str, str] | None = None,
    config: SupervisedModelConfig | None = None,
) -> int:
    """Insert supervised model run metadata idempotently."""

    resolved = config or SupervisedModelConfig()
    payload = {
        "run_id": run_id,
        "model_name": training_result.model_name,
        "model_version": training_result.model_version,
        "model_family": training_result.model_family,
        "dataset_version": resolved.dataset.dataset_version,
        "entity_level": resolved.dataset.level,
        "feature_names": json.dumps(list(training_result.feature_names), sort_keys=True),
        "train_metrics": json.dumps(training_result.train_metrics, sort_keys=True, default=str),
        "validation_metrics": json.dumps(
            training_result.validation_metrics,
            sort_keys=True,
            default=str,
        ),
        "threshold_metrics": training_result.threshold_metrics.to_json(orient="records"),
        "top_k_metrics": training_result.top_k_metrics.to_json(orient="records"),
        "artefact_paths": json.dumps(artefact_paths or {}, sort_keys=True),
        "metadata": json.dumps(
            {
                **training_result.metadata,
                "score_count": int(len(scores)),
            },
            sort_keys=True,
            default=str,
        ),
    }
    try:
        with engine.begin() as connection:
            connection.execute(text(build_supervised_model_run_insert_sql()), payload)
        return 1
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to insert supervised model run: {exc}") from exc


def write_supervised_model_audit_event(
    engine: Engine,
    result: SupervisedModelPersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    """Write supervised model training audit event."""

    details = {
        "run_id": result.run_id,
        "scores_persisted": result.scores_persisted,
        "model_run_persisted": result.model_run_persisted,
        "model_name": result.model_name,
        "model_version": result.model_version,
        "dataset_version": result.dataset_version,
        "entity_level": result.entity_level,
        "artefact_paths": result.artefact_paths,
        "summary": result.summary,
        "metadata": result.metadata,
    }
    sql = text(
        """
        INSERT INTO governance.audit_events (
            event_timestamp, event_type, component, action, status, run_id, details
        ) VALUES (
            :event_timestamp, :event_type, :component, :action, :status, :run_id,
            CAST(:details AS jsonb)
        )
        """
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                sql,
                {
                    "event_timestamp": datetime.now(UTC),
                    "event_type": "supervised_model_training",
                    "component": "models",
                    "action": "persist_supervised_model_outputs",
                    "status": status,
                    "run_id": run_id or result.run_id,
                    "details": json.dumps(details, sort_keys=True, default=str),
                },
            )
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to write supervised audit event: {exc}") from exc


def persist_supervised_model_outputs(
    engine: Engine,
    training_result: SupervisedTrainingResult,
    scores: pd.DataFrame,
    persistence_config: SupervisedModelPersistenceConfig | None = None,
    model_config: SupervisedModelConfig | None = None,
    artefact_paths: dict[str, str] | None = None,
) -> SupervisedModelPersistenceResult:
    """Persist supervised scores, model run metadata, and audit event."""

    config = persistence_config or SupervisedModelPersistenceConfig()
    validate_supervised_model_persistence_config(config)
    model = model_config or SupervisedModelConfig()
    run_id = build_supervised_run_id(training_result, model)
    score_count = 0
    model_run_count = 0
    if config.write_scores:
        score_count = upsert_supervised_scores(engine, scores, config.batch_size)
    if config.write_model_run:
        model_run_count = insert_supervised_model_run(
            engine,
            run_id,
            training_result,
            scores,
            artefact_paths,
            model,
        )
    result = SupervisedModelPersistenceResult(
        run_id=run_id,
        scores_persisted=score_count,
        model_run_persisted=bool(model_run_count),
        model_name=training_result.model_name,
        model_version=training_result.model_version,
        dataset_version=config.dataset_version,
        entity_level=model.dataset.level,
        persisted=bool(score_count or model_run_count),
        artefact_paths=artefact_paths or {},
        summary={
            "score_count": int(len(scores)),
            "feature_count": len(training_result.feature_names),
        },
        metadata={"model_family": training_result.model_family},
    )
    if config.write_audit:
        write_supervised_model_audit_event(engine, result, "success", run_id)
    return result


def log_supervised_model_to_mlflow(
    training_result: SupervisedTrainingResult,
    scores: pd.DataFrame,
    artefact_paths: dict[str, str] | None = None,
    config: SupervisedModelConfig | None = None,
) -> str | None:
    """Log supervised metadata to local MLflow when available."""

    resolved = config or SupervisedModelConfig()
    if not resolved.persistence.write_mlflow:
        return None
    try:
        import mlflow
    except Exception:
        return None
    try:
        with mlflow.start_run(run_name=training_result.model_version) as run:
            mlflow.log_param("model_name", training_result.model_name)
            mlflow.log_param("model_version", training_result.model_version)
            mlflow.log_param("model_family", training_result.model_family)
            mlflow.log_param("dataset_version", resolved.dataset.dataset_version)
            mlflow.log_metric("feature_count", len(training_result.feature_names))
            mlflow.log_metric("score_count", len(scores))
            for key, value in training_result.validation_metrics.items():
                if isinstance(value, int | float) and value is not None:
                    mlflow.log_metric(f"validation_{key}", float(value))
            for path in (artefact_paths or {}).values():
                if path and not str(path).startswith("mlflow_"):
                    mlflow.log_artifact(str(path))
            return str(run.info.run_id)
    except Exception as exc:
        raise SupervisedPersistenceError(f"failed to log supervised MLflow run: {exc}") from exc
