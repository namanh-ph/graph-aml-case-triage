"""PostgreSQL persistence for account anomaly scores."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.models.exceptions import ModelPersistenceError, ModelValidationError
from graph_aml.models.isolation_forest import (
    AnomalyScoreResult,
    IsolationForestTrainingResult,
)
from graph_aml.models.validation import validate_prepared_anomaly_score_frame

ANOMALY_SCORE_TABLE_SCHEMA = "mart"
ANOMALY_SCORE_TABLE_NAME = "account_anomaly_scores"
DEFAULT_ANOMALY_MODEL_NAME = "account_isolation_forest"
DEFAULT_ANOMALY_MODEL_VERSION = "isolation_forest_v1"

ANOMALY_SCORE_PERSISTED_COLUMNS = (
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

_CONFLICT_COLUMNS = ("account_id", "score_date", "model_name", "model_version", "model_run_id")
_JSON_COLUMNS = (
    "feature_names",
    "model_parameters",
    "preprocessing_metadata",
    "metrics",
    "metadata",
)
_SAFE_ID_PATTERN = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True)
class AnomalyScorePersistenceConfig:
    """Configuration for anomaly score persistence."""

    score_date: date | None = None
    model_name: str = DEFAULT_ANOMALY_MODEL_NAME
    model_version: str = DEFAULT_ANOMALY_MODEL_VERSION
    model_run_id: str | None = None
    feature_date: date | None = None
    account_feature_version: str | None = None
    graph_feature_version: str | None = None
    graph_build_id: str | None = None
    batch_size: int = 1000
    write_audit: bool = True

    def __post_init__(self) -> None:
        validate_anomaly_score_persistence_config(self)


@dataclass(frozen=True)
class AnomalyScorePersistenceResult:
    """Summary of anomaly score persistence."""

    rows_prepared: int = 0
    rows_persisted: int = 0
    unique_account_count: int = 0
    score_date: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    model_run_id: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def _safe_identifier_part(value: str) -> str:
    safe = _SAFE_ID_PATTERN.sub("_", value.strip()).strip("_").lower()
    return safe or "unknown"


def build_model_run_id(
    score_date: date,
    model_name: str,
    model_version: str,
) -> str:
    """Build a deterministic model run ID."""

    if not isinstance(score_date, date):
        raise ModelPersistenceError("score_date must be a date")
    if not model_name.strip() or not model_version.strip():
        raise ModelPersistenceError("model_name and model_version must be non-empty")
    return "_".join(
        [
            _safe_identifier_part(model_name),
            _safe_identifier_part(model_version),
            score_date.isoformat().replace("-", "_"),
        ]
    )


def validate_anomaly_score_persistence_config(
    config: AnomalyScorePersistenceConfig,
) -> None:
    """Validate anomaly score persistence configuration."""

    if not isinstance(config, AnomalyScorePersistenceConfig):
        raise ModelPersistenceError("config must be AnomalyScorePersistenceConfig")
    if not config.model_name.strip():
        raise ModelPersistenceError("model_name must be non-empty")
    if not config.model_version.strip():
        raise ModelPersistenceError("model_version must be non-empty")
    if config.model_run_id is not None and not config.model_run_id.strip():
        raise ModelPersistenceError("model_run_id must be non-empty when supplied")
    if config.batch_size <= 0:
        raise ModelPersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise ModelPersistenceError("write_audit must be boolean")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalise_timestamp(value: datetime | None) -> datetime:
    timestamp = _utc_now() if value is None else value
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime | date):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return cast(Any, value).item()
        except (AttributeError, ValueError):
            return str(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _preprocessing_metadata(training_result: IsolationForestTrainingResult) -> dict[str, object]:
    return {
        "imputation_values": dict(training_result.preprocessing.imputation_values),
        "scaling_values": {
            key: dict(value) for key, value in training_result.preprocessing.scaling_values.items()
        },
    }


def prepare_anomaly_scores_for_persistence(
    score_result: AnomalyScoreResult,
    training_result: IsolationForestTrainingResult,
    config: AnomalyScorePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
    scored_at: datetime | None = None,
) -> pd.DataFrame:
    """Attach model lineage metadata and coerce anomaly scores for persistence."""

    resolved = AnomalyScorePersistenceConfig() if config is None else config
    validate_anomaly_score_persistence_config(resolved)
    try:
        scores = score_result.scores.copy()
        missing = {
            "account_id",
            "anomaly_score",
            "anomaly_score_raw",
            "is_anomaly",
            "anomaly_rank",
            "risk_band",
        }.difference(scores.columns)
        if missing:
            raise ModelValidationError(f"scores missing required columns: {sorted(missing)}")
        score_date = resolved.score_date or _utc_now().date()
        model_run_id = resolved.model_run_id or build_model_run_id(
            score_date,
            resolved.model_name,
            resolved.model_version,
        )
        output = scores.copy()
        output["account_id"] = output["account_id"].astype("string").str.strip()
        output = output.sort_values(["account_id", "anomaly_rank"]).drop_duplicates(
            subset=["account_id"],
            keep="last",
        )
        output["score_date"] = score_date
        output["model_name"] = resolved.model_name
        output["model_version"] = resolved.model_version
        output["model_run_id"] = model_run_id
        output["feature_date"] = resolved.feature_date
        output["account_feature_version"] = resolved.account_feature_version
        output["graph_feature_version"] = resolved.graph_feature_version
        output["graph_build_id"] = resolved.graph_build_id
        output["anomaly_score"] = pd.to_numeric(output["anomaly_score"], errors="coerce").astype(
            "float64"
        )
        output["anomaly_score_raw"] = pd.to_numeric(
            output["anomaly_score_raw"],
            errors="coerce",
        ).astype("float64")
        output["anomaly_rank"] = pd.to_numeric(output["anomaly_rank"], errors="coerce").astype(
            "int64"
        )
        output["is_anomaly"] = output["is_anomaly"].astype(bool)
        output["risk_band"] = output["risk_band"].astype(str)
        output["feature_names"] = [list(training_result.feature_names)] * len(output)
        output["model_parameters"] = [_json_safe(training_result.parameters)] * len(output)
        output["preprocessing_metadata"] = [_preprocessing_metadata(training_result)] * len(output)
        output["metrics"] = [_json_safe(training_result.metrics)] * len(output)
        output["metadata"] = [
            _json_safe(
                {
                    "score_summary": score_result.summary,
                    "score_metadata": score_result.metadata,
                    "extra_metadata": extra_metadata or {},
                }
            )
        ] * len(output)
        output["scored_at"] = _normalise_timestamp(scored_at)
        output = output.loc[:, ANOMALY_SCORE_PERSISTED_COLUMNS].reset_index(drop=True)
        validate_prepared_anomaly_score_frame(output)
        return output
    except ModelValidationError:
        raise
    except Exception as exc:
        raise ModelPersistenceError(
            f"Failed to prepare anomaly scores for persistence: {exc}"
        ) from exc


def build_anomaly_score_upsert_sql() -> str:
    """Build deterministic PostgreSQL upsert SQL for anomaly scores."""

    insert_columns = ", ".join(ANOMALY_SCORE_PERSISTED_COLUMNS)
    placeholders = ", ".join(
        f"CAST(:{column} AS JSONB)" if column in _JSON_COLUMNS else f":{column}"
        for column in ANOMALY_SCORE_PERSISTED_COLUMNS
    )
    conflict_columns = ", ".join(_CONFLICT_COLUMNS)
    update_columns = [
        column for column in ANOMALY_SCORE_PERSISTED_COLUMNS if column not in _CONFLICT_COLUMNS
    ]
    update_clause = ",\n            ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )
    return f"""
        INSERT INTO {ANOMALY_SCORE_TABLE_SCHEMA}.{ANOMALY_SCORE_TABLE_NAME} ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_columns}) DO UPDATE SET
            {update_clause},
            updated_at = CURRENT_TIMESTAMP
    """


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(cast(Any, value))
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, bool) else False


def _to_db_value(value: object) -> object:
    if _is_missing(value):
        return None
    if isinstance(value, dict | list | tuple):
        return json.dumps(_json_safe(value), sort_keys=True, default=str)
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime | date):
        return value
    if hasattr(value, "item"):
        try:
            return cast(Any, value).item()
        except (AttributeError, ValueError):
            return str(value)
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        {str(column): _to_db_value(value) for column, value in row.items()}
        for row in frame.astype(object).to_dict(orient="records")
    ]


def upsert_anomaly_scores(
    engine: Engine,
    prepared_scores: pd.DataFrame,
    batch_size: int = 1000,
) -> int:
    """Upsert prepared anomaly scores into mart.account_anomaly_scores."""

    if batch_size <= 0:
        raise ModelPersistenceError("batch_size must be positive")
    if prepared_scores.empty:
        return 0
    try:
        validate_prepared_anomaly_score_frame(prepared_scores)
        rows = _records(prepared_scores.loc[:, ANOMALY_SCORE_PERSISTED_COLUMNS])
        statement = text(build_anomaly_score_upsert_sql())
        with engine.begin() as connection:
            for start in range(0, len(rows), batch_size):
                connection.execute(statement, rows[start : start + batch_size])
        return len(rows)
    except ModelValidationError as exc:
        raise ModelPersistenceError(str(exc)) from exc
    except ModelPersistenceError:
        raise
    except Exception as exc:
        raise ModelPersistenceError(f"Failed to upsert anomaly scores: {exc}") from exc


def _result_summary(prepared: pd.DataFrame, rows_persisted: int) -> dict[str, object]:
    return {
        "rows_prepared": int(len(prepared)),
        "rows_persisted": int(rows_persisted),
        "unique_account_count": int(prepared["account_id"].nunique()) if not prepared.empty else 0,
        "persisted": rows_persisted > 0,
    }


def persist_anomaly_scores(
    engine: Engine,
    score_result: AnomalyScoreResult,
    training_result: IsolationForestTrainingResult,
    config: AnomalyScorePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> AnomalyScorePersistenceResult:
    """Prepare, upsert, and optionally audit anomaly scores."""

    resolved = AnomalyScorePersistenceConfig() if config is None else config
    try:
        prepared = prepare_anomaly_scores_for_persistence(
            score_result,
            training_result,
            config=resolved,
            extra_metadata=extra_metadata,
        )
        rows_persisted = upsert_anomaly_scores(engine, prepared, resolved.batch_size)
        result = AnomalyScorePersistenceResult(
            rows_prepared=len(prepared),
            rows_persisted=rows_persisted,
            unique_account_count=int(prepared["account_id"].nunique()) if not prepared.empty else 0,
            score_date=str(prepared.iloc[0]["score_date"]) if not prepared.empty else None,
            model_name=(
                str(prepared.iloc[0]["model_name"]) if not prepared.empty else resolved.model_name
            ),
            model_version=str(prepared.iloc[0]["model_version"])
            if not prepared.empty
            else resolved.model_version,
            model_run_id=str(prepared.iloc[0]["model_run_id"]) if not prepared.empty else None,
            persisted=rows_persisted > 0,
            metadata=dict(prepared.iloc[0]["metadata"]) if not prepared.empty else {},
            summary=_result_summary(prepared, rows_persisted),
        )
        if resolved.write_audit:
            write_anomaly_score_persistence_audit_event(engine, result, status="success")
        return result
    except ModelPersistenceError:
        raise
    except Exception as exc:
        raise ModelPersistenceError(f"Failed to persist anomaly scores: {exc}") from exc


def write_anomaly_score_persistence_audit_event(
    engine: Engine,
    result: AnomalyScorePersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    """Write one governance audit event for anomaly score persistence."""

    details = {
        "rows_prepared": int(result.rows_prepared),
        "rows_persisted": int(result.rows_persisted),
        "unique_account_count": int(result.unique_account_count),
        "score_date": result.score_date,
        "model_name": result.model_name,
        "model_version": result.model_version,
        "model_run_id": result.model_run_id,
        "metadata": result.metadata,
    }
    statement = text(
        """
        INSERT INTO governance.audit_events (
            event_type,
            component,
            run_id,
            pipeline_stage,
            entity_type,
            entity_id,
            action,
            status,
            details,
            created_by
        )
        VALUES (
            :event_type,
            :component,
            :run_id,
            :pipeline_stage,
            :entity_type,
            :entity_id,
            :action,
            :status,
            CAST(:details AS JSONB),
            :created_by
        )
        """
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                statement,
                {
                    "event_type": "model_scoring",
                    "component": "models",
                    "run_id": run_id,
                    "pipeline_stage": "anomaly_scoring",
                    "entity_type": "score_table",
                    "entity_id": f"{ANOMALY_SCORE_TABLE_SCHEMA}.{ANOMALY_SCORE_TABLE_NAME}",
                    "action": "persist_account_anomaly_scores",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise ModelPersistenceError(
            f"Failed to write anomaly score persistence audit event: {exc}"
        ) from exc
