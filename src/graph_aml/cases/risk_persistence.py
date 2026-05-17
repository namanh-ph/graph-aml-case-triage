"""PostgreSQL persistence for case-level risk scores."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.exceptions import CaseRiskPersistenceError, CaseRiskValidationError
from graph_aml.cases.risk_scoring import CaseRiskScoreResult
from graph_aml.cases.risk_validation import (
    CASE_RISK_PERSISTENCE_COLUMNS,
    validate_prepared_case_risk_score_frame,
)

CASE_RISK_TABLE_SCHEMA = "aml"
CASE_RISK_TABLE_NAME = "case_risk_scores"
DEFAULT_CASE_RISK_SCORE_NAME = "composite_case_risk"
DEFAULT_CASE_RISK_SCORE_VERSION = "composite_case_risk_v1"
_CONFLICT_COLUMNS = ("case_id", "score_date", "score_name", "score_version")
_JSON_COLUMNS = ("weights", "metadata")


@dataclass(frozen=True)
class CaseRiskScorePersistenceConfig:
    score_date: date | None = None
    score_name: str = DEFAULT_CASE_RISK_SCORE_NAME
    score_version: str = DEFAULT_CASE_RISK_SCORE_VERSION
    batch_size: int = 1000
    write_audit: bool = True
    update_case_snapshot: bool = True

    def __post_init__(self) -> None:
        validate_case_risk_score_persistence_config(self)


@dataclass(frozen=True)
class CaseRiskScorePersistenceResult:
    rows_prepared: int = 0
    rows_persisted: int = 0
    case_snapshots_updated: int = 0
    unique_case_count: int = 0
    score_date: str | None = None
    score_name: str | None = None
    score_version: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def validate_case_risk_score_persistence_config(config: CaseRiskScorePersistenceConfig) -> None:
    if not isinstance(config, CaseRiskScorePersistenceConfig):
        raise CaseRiskPersistenceError("config must be CaseRiskScorePersistenceConfig")
    if not config.score_name.strip():
        raise CaseRiskPersistenceError("score_name must be non-empty")
    if not config.score_version.strip():
        raise CaseRiskPersistenceError("score_version must be non-empty")
    if config.batch_size <= 0:
        raise CaseRiskPersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise CaseRiskPersistenceError("write_audit must be boolean")
    if not isinstance(config.update_case_snapshot, bool):
        raise CaseRiskPersistenceError("update_case_snapshot must be boolean")


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


def prepare_case_risk_scores_for_persistence(
    result: CaseRiskScoreResult,
    config: CaseRiskScorePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
    scored_at: datetime | None = None,
) -> pd.DataFrame:
    resolved = CaseRiskScorePersistenceConfig() if config is None else config
    try:
        scores = result.scores.copy(deep=True)
        if scores.empty:
            output = pd.DataFrame(columns=CASE_RISK_PERSISTENCE_COLUMNS)
        else:
            score_date = resolved.score_date or _utc_now().date()
            output = scores.sort_values(["case_id", "risk_rank"]).drop_duplicates(
                "case_id",
                keep="last",
            )
            output["score_date"] = score_date
            output["score_name"] = resolved.score_name
            output["score_version"] = resolved.score_version
            output["weights"] = [_json_safe(result.metadata.get("weights", {}))] * len(output)
            output["metadata"] = [
                _json_safe(
                    {
                        "score_summary": result.summary,
                        "score_metadata": result.metadata,
                        "extra_metadata": extra_metadata or {},
                    }
                )
            ] * len(output)
            output["scored_at"] = _normalise_timestamp(scored_at)
            output = output.loc[:, CASE_RISK_PERSISTENCE_COLUMNS].reset_index(drop=True)
        validate_prepared_case_risk_score_frame(output)
        return output
    except CaseRiskValidationError as exc:
        raise CaseRiskPersistenceError(str(exc)) from exc
    except Exception as exc:
        raise CaseRiskPersistenceError(
            f"Failed to prepare case risk scores for persistence: {exc}"
        ) from exc


def build_case_risk_score_upsert_sql() -> str:
    insert_columns = ", ".join(CASE_RISK_PERSISTENCE_COLUMNS)
    placeholders = ", ".join(
        f"CAST(:{column} AS JSONB)" if column in _JSON_COLUMNS else f":{column}"
        for column in CASE_RISK_PERSISTENCE_COLUMNS
    )
    update_columns = [
        column for column in CASE_RISK_PERSISTENCE_COLUMNS if column not in _CONFLICT_COLUMNS
    ]
    update_clause = ",\n            ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )
    return f"""
        INSERT INTO {CASE_RISK_TABLE_SCHEMA}.{CASE_RISK_TABLE_NAME} ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT ({", ".join(_CONFLICT_COLUMNS)}) DO UPDATE SET
            {update_clause},
            updated_at = CURRENT_TIMESTAMP
    """


def build_case_snapshot_update_sql() -> str:
    return """
        UPDATE aml.cases
        SET
            case_risk_score = :case_risk_score,
            case_risk_band = :risk_band,
            case_risk_rank = :risk_rank,
            updated_at = CURRENT_TIMESTAMP
        WHERE case_id = :case_id
    """


def _upsert_frame(
    engine: Engine,
    frame: pd.DataFrame,
    sql: str,
    columns: tuple[str, ...],
    batch_size: int,
) -> int:
    if batch_size <= 0:
        raise CaseRiskPersistenceError("batch_size must be positive")
    if frame.empty:
        return 0
    rows = _records(frame.loc[:, columns])
    statement = text(sql)
    with engine.begin() as connection:
        for start in range(0, len(rows), batch_size):
            connection.execute(statement, rows[start : start + batch_size])
    return len(rows)


def upsert_case_risk_scores(
    engine: Engine,
    prepared_scores: pd.DataFrame,
    batch_size: int = 1000,
) -> int:
    try:
        if prepared_scores.empty:
            return 0
        validate_prepared_case_risk_score_frame(prepared_scores)
        return _upsert_frame(
            engine,
            prepared_scores,
            build_case_risk_score_upsert_sql(),
            CASE_RISK_PERSISTENCE_COLUMNS,
            batch_size,
        )
    except Exception as exc:
        if isinstance(exc, CaseRiskPersistenceError):
            raise
        raise CaseRiskPersistenceError(f"Failed to upsert case risk scores: {exc}") from exc


def update_case_risk_snapshot(
    engine: Engine,
    prepared_scores: pd.DataFrame,
    batch_size: int = 1000,
) -> int:
    try:
        columns = ("case_id", "case_risk_score", "risk_band", "risk_rank")
        return _upsert_frame(
            engine, prepared_scores, build_case_snapshot_update_sql(), columns, batch_size
        )
    except Exception as exc:
        if isinstance(exc, CaseRiskPersistenceError):
            raise
        raise CaseRiskPersistenceError(f"Failed to update case risk snapshot: {exc}") from exc


def persist_case_risk_scores(
    engine: Engine,
    result: CaseRiskScoreResult,
    config: CaseRiskScorePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> CaseRiskScorePersistenceResult:
    resolved = CaseRiskScorePersistenceConfig() if config is None else config
    try:
        prepared = prepare_case_risk_scores_for_persistence(result, resolved, extra_metadata)
        rows_persisted = upsert_case_risk_scores(engine, prepared, resolved.batch_size)
        snapshots = (
            update_case_risk_snapshot(engine, prepared, resolved.batch_size)
            if resolved.update_case_snapshot
            else 0
        )
        persistence_result = CaseRiskScorePersistenceResult(
            rows_prepared=len(prepared),
            rows_persisted=rows_persisted,
            case_snapshots_updated=snapshots,
            unique_case_count=int(prepared["case_id"].nunique()) if not prepared.empty else 0,
            score_date=str(prepared.iloc[0]["score_date"]) if not prepared.empty else None,
            score_name=str(prepared.iloc[0]["score_name"])
            if not prepared.empty
            else resolved.score_name,
            score_version=str(prepared.iloc[0]["score_version"])
            if not prepared.empty
            else resolved.score_version,
            persisted=rows_persisted > 0,
            metadata=dict(prepared.iloc[0]["metadata"]) if not prepared.empty else {},
            summary={
                "rows_prepared": int(len(prepared)),
                "rows_persisted": int(rows_persisted),
                "case_snapshots_updated": int(snapshots),
            },
        )
        if resolved.write_audit:
            write_case_risk_score_audit_event(engine, persistence_result, status="success")
        return persistence_result
    except CaseRiskPersistenceError:
        raise
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to persist case risk scores: {exc}") from exc


def write_case_risk_score_audit_event(
    engine: Engine,
    result: CaseRiskScorePersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    details = {
        "rows_prepared": int(result.rows_prepared),
        "rows_persisted": int(result.rows_persisted),
        "case_snapshots_updated": int(result.case_snapshots_updated),
        "unique_case_count": int(result.unique_case_count),
        "score_date": result.score_date,
        "score_name": result.score_name,
        "score_version": result.score_version,
        "summary": result.summary,
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
                    "event_type": "case_risk_scoring",
                    "component": "cases",
                    "run_id": run_id,
                    "pipeline_stage": "case_risk_scoring",
                    "entity_type": "score_table",
                    "entity_id": "aml.case_risk_scores",
                    "action": "persist_case_risk_scores",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise CaseRiskPersistenceError(f"Failed to write case risk audit event: {exc}") from exc
