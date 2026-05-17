"""Persist Neo4j graph analytics features into PostgreSQL mart tables."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, cast

import pandas as pd
from neo4j import Driver
from sqlalchemy import Engine, text

from graph_aml.graph.analytics import (
    GRAPH_ANALYTICS_FEATURE_COLUMNS,
    GraphAnalyticsResult,
    compute_graph_analytics_features_from_neo4j,
)
from graph_aml.graph.analytics_config import GraphAnalyticsConfig
from graph_aml.graph.exceptions import (
    GraphAnalyticsError,
    GraphFeaturePersistenceError,
    GraphFeatureValidationError,
)
from graph_aml.graph.feature_validation import (
    validate_prepared_graph_feature_frame,
)

GRAPH_FEATURE_TABLE_SCHEMA = "mart"
GRAPH_FEATURE_TABLE_NAME = "graph_features"
DEFAULT_GRAPH_FEATURE_VERSION = "graph_features_v1"

GRAPH_FEATURE_METADATA_COLUMNS = (
    "feature_date",
    "feature_version",
    "graph_build_id",
    "graph_database",
    "computed_at",
    "metadata",
)

_INTEGER_FEATURE_COLUMNS = (
    "community_id",
    "community_size",
    "cycle_count",
    "fan_in_count",
    "fan_out_count",
    "alert_count",
    "high_risk_alert_count",
    "shortest_path_to_flagged",
    "neighbour_account_count",
    "counterparty_count",
    "transaction_count",
    "graph_component_size",
)
_NUMERIC_FEATURE_COLUMNS = tuple(
    column
    for column in GRAPH_ANALYTICS_FEATURE_COLUMNS
    if column not in {"account_id", "shortest_path_to_flagged"}
)
_PERSISTED_COLUMNS = (
    "account_id",
    "feature_date",
    "feature_version",
    "graph_build_id",
    "graph_database",
    "computed_at",
    *[column for column in GRAPH_ANALYTICS_FEATURE_COLUMNS if column != "account_id"],
    "metadata",
)
_CONFLICT_COLUMNS = ("account_id", "feature_date", "feature_version", "graph_build_id")
_SAFE_ID_PATTERN = re.compile(r"[^A-Za-z0-9]+")


@dataclass(frozen=True)
class GraphFeaturePersistenceConfig:
    """Configuration for graph feature mart persistence."""

    feature_date: date | None = None
    feature_version: str = DEFAULT_GRAPH_FEATURE_VERSION
    graph_build_id: str | None = None
    graph_database: str | None = None
    batch_size: int = 1000
    write_audit: bool = True

    def __post_init__(self) -> None:
        validate_graph_feature_persistence_config(self)


@dataclass(frozen=True)
class GraphFeaturePersistenceResult:
    """Summary of graph feature persistence."""

    rows_prepared: int = 0
    rows_persisted: int = 0
    unique_account_count: int = 0
    feature_date: str | None = None
    feature_version: str | None = None
    graph_build_id: str | None = None
    graph_database: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def _safe_identifier_part(value: str) -> str:
    safe = _SAFE_ID_PATTERN.sub("_", value.strip()).strip("_").lower()
    return safe or "unknown"


def build_graph_feature_build_id(
    feature_date: date,
    feature_version: str,
    graph_database: str | None = None,
) -> str:
    """Build a deterministic graph feature build identifier."""

    if not isinstance(feature_date, date):
        raise GraphFeaturePersistenceError("feature_date must be a date")
    if not str(feature_version).strip():
        raise GraphFeaturePersistenceError("feature_version must be non-empty")
    parts = [
        _safe_identifier_part(str(feature_version)),
        feature_date.isoformat().replace("-", "_"),
    ]
    if graph_database is not None and str(graph_database).strip():
        parts.append(_safe_identifier_part(str(graph_database)))
    return "_".join(parts)


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


def build_graph_feature_metadata(
    analytics_summary: dict[str, object] | None = None,
    analytics_metadata: dict[str, object] | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build JSON-safe metadata for graph feature rows."""

    return {
        "analytics_summary": _json_safe({} if analytics_summary is None else analytics_summary),
        "analytics_metadata": _json_safe({} if analytics_metadata is None else analytics_metadata),
        "extra_metadata": _json_safe({} if extra_metadata is None else extra_metadata),
    }


def validate_graph_feature_persistence_config(
    config: GraphFeaturePersistenceConfig,
) -> None:
    """Validate graph feature persistence configuration."""

    if not isinstance(config, GraphFeaturePersistenceConfig):
        raise GraphFeaturePersistenceError("config must be GraphFeaturePersistenceConfig")
    if not str(config.feature_version).strip():
        raise GraphFeaturePersistenceError("feature_version must be non-empty")
    if config.graph_build_id is not None and not str(config.graph_build_id).strip():
        raise GraphFeaturePersistenceError("graph_build_id must be non-empty when supplied")
    if config.batch_size <= 0:
        raise GraphFeaturePersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise GraphFeaturePersistenceError("write_audit must be boolean")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalise_computed_at(value: datetime | None) -> datetime:
    timestamp = _utc_now() if value is None else value
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _coerce_numeric(series: pd.Series, column: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if column == "shortest_path_to_flagged":
        return numeric.astype("Int64")
    numeric = numeric.fillna(0)
    if column in _INTEGER_FEATURE_COLUMNS:
        return numeric.astype("int64")
    return numeric.astype("float64")


def prepare_graph_features_for_persistence(
    features: pd.DataFrame,
    config: GraphFeaturePersistenceConfig | None = None,
    analytics_summary: dict[str, object] | None = None,
    analytics_metadata: dict[str, object] | None = None,
    extra_metadata: dict[str, object] | None = None,
    computed_at: datetime | None = None,
) -> pd.DataFrame:
    """Attach persistence metadata and coerce graph feature values."""

    resolved = GraphFeaturePersistenceConfig() if config is None else config
    validate_graph_feature_persistence_config(resolved)
    if not isinstance(features, pd.DataFrame):
        raise GraphFeatureValidationError("features must be a DataFrame")
    missing = set(GRAPH_ANALYTICS_FEATURE_COLUMNS).difference(features.columns)
    if missing:
        raise GraphFeatureValidationError(f"graph features are missing columns: {sorted(missing)}")
    if not features.empty:
        account_ids = features["account_id"].astype("string").str.strip()
        if account_ids.isna().any() or (account_ids == "").any():
            raise GraphFeatureValidationError("account_id must be non-null")
    try:
        output = features.loc[:, GRAPH_ANALYTICS_FEATURE_COLUMNS].copy(deep=True)
        if output.empty:
            for column in _PERSISTED_COLUMNS:
                if column not in output.columns:
                    output[column] = pd.Series(dtype="object")
            return output.loc[:, _PERSISTED_COLUMNS]

        output["_row_order"] = range(len(output))
        output["account_id"] = output["account_id"].astype("string").str.strip()
        output = (
            output.sort_values(["account_id", "_row_order"])
            .drop_duplicates(subset=["account_id"], keep="last")
            .drop(columns=["_row_order"])
        )
        for column in GRAPH_ANALYTICS_FEATURE_COLUMNS:
            if column == "account_id":
                continue
            output[column] = _coerce_numeric(output[column], column)

        feature_date = resolved.feature_date or _utc_now().date()
        graph_build_id = resolved.graph_build_id or build_graph_feature_build_id(
            feature_date,
            resolved.feature_version,
            resolved.graph_database,
        )
        timestamp = _normalise_computed_at(computed_at)
        metadata = build_graph_feature_metadata(
            analytics_summary=analytics_summary,
            analytics_metadata=analytics_metadata,
            extra_metadata=extra_metadata,
        )
        output["feature_date"] = feature_date
        output["feature_version"] = resolved.feature_version
        output["graph_build_id"] = graph_build_id
        output["graph_database"] = resolved.graph_database
        output["computed_at"] = timestamp
        output["metadata"] = [metadata.copy() for _ in range(len(output))]
        output = output.loc[:, _PERSISTED_COLUMNS].sort_values("account_id").reset_index(drop=True)
        validate_prepared_graph_feature_frame(output)
        return output
    except GraphFeatureValidationError:
        raise
    except Exception as exc:
        raise GraphFeatureValidationError(
            f"Failed to prepare graph features for persistence: {exc}"
        ) from exc


def build_graph_feature_upsert_sql() -> str:
    """Build deterministic PostgreSQL upsert SQL for graph features."""

    insert_columns = ", ".join(_PERSISTED_COLUMNS)
    placeholders = ", ".join(
        "CAST(:metadata AS JSONB)" if column == "metadata" else f":{column}"
        for column in _PERSISTED_COLUMNS
    )
    conflict_columns = ", ".join(_CONFLICT_COLUMNS)
    update_columns = [
        column
        for column in _PERSISTED_COLUMNS
        if column not in _CONFLICT_COLUMNS and column != "computed_at"
    ]
    update_clause = ",\n            ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )
    return f"""
        INSERT INTO {GRAPH_FEATURE_TABLE_SCHEMA}.{GRAPH_FEATURE_TABLE_NAME} ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_columns}) DO UPDATE SET
            computed_at = EXCLUDED.computed_at,
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


def upsert_graph_features(
    engine: Engine,
    prepared_features: pd.DataFrame,
    batch_size: int = 1000,
) -> int:
    """Upsert prepared graph features into mart.graph_features."""

    if batch_size <= 0:
        raise GraphFeaturePersistenceError("batch_size must be positive")
    if prepared_features.empty:
        return 0
    try:
        validate_prepared_graph_feature_frame(prepared_features)
        statement = text(build_graph_feature_upsert_sql())
        rows = _records(prepared_features.loc[:, _PERSISTED_COLUMNS])
        with engine.begin() as connection:
            for start in range(0, len(rows), batch_size):
                connection.execute(statement, rows[start : start + batch_size])
        return len(rows)
    except GraphFeaturePersistenceError:
        raise
    except Exception as exc:
        raise GraphFeaturePersistenceError(f"Failed to upsert graph features: {exc}") from exc


def _result_summary(prepared: pd.DataFrame, rows_persisted: int) -> dict[str, object]:
    return {
        "rows_prepared": int(len(prepared)),
        "rows_persisted": int(rows_persisted),
        "unique_account_count": int(prepared["account_id"].nunique()) if not prepared.empty else 0,
        "feature_count": len(
            [column for column in GRAPH_ANALYTICS_FEATURE_COLUMNS if column != "account_id"]
        ),
        "persisted": rows_persisted > 0,
    }


def persist_graph_features(
    engine: Engine,
    features: pd.DataFrame,
    config: GraphFeaturePersistenceConfig | None = None,
    analytics_summary: dict[str, object] | None = None,
    analytics_metadata: dict[str, object] | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> GraphFeaturePersistenceResult:
    """Prepare, upsert, and optionally audit graph analytics features."""

    resolved = GraphFeaturePersistenceConfig() if config is None else config
    try:
        prepared = prepare_graph_features_for_persistence(
            features,
            config=resolved,
            analytics_summary=analytics_summary,
            analytics_metadata=analytics_metadata,
            extra_metadata=extra_metadata,
        )
        rows_persisted = upsert_graph_features(
            engine,
            prepared,
            batch_size=resolved.batch_size,
        )
        metadata = (
            dict(prepared.iloc[0]["metadata"])
            if not prepared.empty and isinstance(prepared.iloc[0]["metadata"], dict)
            else build_graph_feature_metadata(analytics_summary, analytics_metadata, extra_metadata)
        )
        result = GraphFeaturePersistenceResult(
            rows_prepared=len(prepared),
            rows_persisted=rows_persisted,
            unique_account_count=int(prepared["account_id"].nunique()) if not prepared.empty else 0,
            feature_date=str(prepared.iloc[0]["feature_date"]) if not prepared.empty else None,
            feature_version=str(prepared.iloc[0]["feature_version"])
            if not prepared.empty
            else resolved.feature_version,
            graph_build_id=str(prepared.iloc[0]["graph_build_id"]) if not prepared.empty else None,
            graph_database=(
                None
                if prepared.empty or _is_missing(prepared.iloc[0]["graph_database"])
                else str(prepared.iloc[0]["graph_database"])
            ),
            persisted=rows_persisted > 0,
            metadata=metadata,
            summary=_result_summary(prepared, rows_persisted),
        )
        if resolved.write_audit:
            write_graph_feature_persistence_audit_event(engine, result, status="success")
        return result
    except GraphFeatureValidationError:
        raise
    except GraphFeaturePersistenceError:
        raise
    except Exception as exc:
        raise GraphFeaturePersistenceError(f"Failed to persist graph features: {exc}") from exc


def compute_and_persist_graph_features_from_neo4j(
    postgres_engine: Engine,
    neo4j_driver: Driver,
    analytics_config: GraphAnalyticsConfig | None = None,
    persistence_config: GraphFeaturePersistenceConfig | None = None,
    database: str | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> GraphFeaturePersistenceResult:
    """Compute graph analytics from Neo4j and persist the feature frame."""

    try:
        analytics_result: GraphAnalyticsResult = compute_graph_analytics_features_from_neo4j(
            neo4j_driver,
            analytics_config,
            database=database,
        )
        base_config = (
            GraphFeaturePersistenceConfig() if persistence_config is None else persistence_config
        )
        resolved_config = base_config
        if base_config.graph_database is None and database is not None:
            resolved_config = GraphFeaturePersistenceConfig(
                feature_date=base_config.feature_date,
                feature_version=base_config.feature_version,
                graph_build_id=base_config.graph_build_id,
                graph_database=database,
                batch_size=base_config.batch_size,
                write_audit=base_config.write_audit,
            )
        return persist_graph_features(
            postgres_engine,
            analytics_result.features,
            config=resolved_config,
            analytics_summary=analytics_result.summary,
            analytics_metadata=analytics_result.metadata,
            extra_metadata=extra_metadata,
        )
    except GraphAnalyticsError:
        raise
    except GraphFeaturePersistenceError:
        raise
    except Exception as exc:
        raise GraphFeaturePersistenceError(
            f"Failed to compute and persist graph features: {exc}"
        ) from exc


def write_graph_feature_persistence_audit_event(
    engine: Engine,
    result: GraphFeaturePersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    """Write one governance audit event for graph feature persistence."""

    details = {
        "rows_prepared": int(result.rows_prepared),
        "rows_persisted": int(result.rows_persisted),
        "unique_account_count": int(result.unique_account_count),
        "feature_date": result.feature_date,
        "feature_version": result.feature_version,
        "graph_build_id": result.graph_build_id,
        "graph_database": result.graph_database,
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
                    "event_type": "graph_feature_persistence",
                    "component": "graph",
                    "run_id": run_id,
                    "pipeline_stage": "graph_feature_persistence",
                    "entity_type": "feature_table",
                    "entity_id": f"{GRAPH_FEATURE_TABLE_SCHEMA}.{GRAPH_FEATURE_TABLE_NAME}",
                    "action": "persist_graph_features",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise GraphFeaturePersistenceError(
            f"Failed to write graph feature persistence audit event: {exc}"
        ) from exc
