"""PostgreSQL persistence for composite account risk scores."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.scoring.composite import AccountRiskScoreResult
from graph_aml.scoring.exceptions import ScoringPersistenceError, ScoringValidationError
from graph_aml.scoring.validation import validate_prepared_account_risk_score_frame

ACCOUNT_RISK_SCORE_TABLE_SCHEMA = "mart"
ACCOUNT_RISK_SCORE_TABLE_NAME = "account_risk_scores"
DEFAULT_ACCOUNT_RISK_SCORE_NAME = "composite_account_risk"
DEFAULT_ACCOUNT_RISK_SCORE_VERSION = "composite_account_risk_v1"

ACCOUNT_RISK_SCORE_PERSISTED_COLUMNS = (
    "account_id",
    "score_date",
    "score_name",
    "score_version",
    "account_risk_score",
    "risk_band",
    "risk_rank",
    "rule_risk_score",
    "graph_risk_score",
    "anomaly_risk_score",
    "customer_risk_score",
    "jurisdiction_risk_score",
    "component_coverage",
    "alert_count",
    "high_severity_alert_count",
    "critical_severity_alert_count",
    "max_rule_alert_score",
    "mean_rule_alert_score",
    "max_anomaly_score",
    "graph_percentile_score",
    "weights",
    "metadata",
    "scored_at",
)

_CONFLICT_COLUMNS = ("account_id", "score_date", "score_name", "score_version")
_JSON_COLUMNS = ("weights", "metadata")


@dataclass(frozen=True)
class AccountRiskScorePersistenceConfig:
    """Configuration for account risk score persistence."""

    score_date: date | None = None
    score_name: str = DEFAULT_ACCOUNT_RISK_SCORE_NAME
    score_version: str = DEFAULT_ACCOUNT_RISK_SCORE_VERSION
    batch_size: int = 1000
    write_audit: bool = True

    def __post_init__(self) -> None:
        validate_account_risk_score_persistence_config(self)


@dataclass(frozen=True)
class AccountRiskScorePersistenceResult:
    """Summary of account risk score persistence."""

    rows_prepared: int = 0
    rows_persisted: int = 0
    unique_account_count: int = 0
    score_date: str | None = None
    score_name: str | None = None
    score_version: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def validate_account_risk_score_persistence_config(
    config: AccountRiskScorePersistenceConfig,
) -> None:
    """Validate account risk score persistence configuration."""

    if not isinstance(config, AccountRiskScorePersistenceConfig):
        raise ScoringPersistenceError("config must be AccountRiskScorePersistenceConfig")
    if not config.score_name.strip():
        raise ScoringPersistenceError("score_name must be non-empty")
    if not config.score_version.strip():
        raise ScoringPersistenceError("score_version must be non-empty")
    if config.batch_size <= 0:
        raise ScoringPersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise ScoringPersistenceError("write_audit must be boolean")


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


def prepare_account_risk_scores_for_persistence(
    result: AccountRiskScoreResult,
    config: AccountRiskScorePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
    scored_at: datetime | None = None,
) -> pd.DataFrame:
    """Attach persistence metadata and coerce account risk scores."""

    resolved = AccountRiskScorePersistenceConfig() if config is None else config
    validate_account_risk_score_persistence_config(resolved)
    try:
        scores = result.scores.copy()
        score_date = resolved.score_date or _utc_now().date()
        output = scores.copy()
        output["account_id"] = output["account_id"].astype("string").str.strip()
        output = output.sort_values(["account_id", "risk_rank"]).drop_duplicates(
            "account_id",
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
        output = output.loc[:, ACCOUNT_RISK_SCORE_PERSISTED_COLUMNS].reset_index(drop=True)
        validate_prepared_account_risk_score_frame(output)
        return output
    except ScoringValidationError:
        raise
    except Exception as exc:
        raise ScoringPersistenceError(
            f"Failed to prepare account risk scores for persistence: {exc}"
        ) from exc


def build_account_risk_score_upsert_sql() -> str:
    """Build deterministic PostgreSQL upsert SQL for account risk scores."""

    insert_columns = ", ".join(ACCOUNT_RISK_SCORE_PERSISTED_COLUMNS)
    placeholders = ", ".join(
        f"CAST(:{column} AS JSONB)" if column in _JSON_COLUMNS else f":{column}"
        for column in ACCOUNT_RISK_SCORE_PERSISTED_COLUMNS
    )
    conflict_columns = ", ".join(_CONFLICT_COLUMNS)
    update_columns = [
        column for column in ACCOUNT_RISK_SCORE_PERSISTED_COLUMNS if column not in _CONFLICT_COLUMNS
    ]
    update_clause = ",\n            ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )
    table_name = f"{ACCOUNT_RISK_SCORE_TABLE_SCHEMA}.{ACCOUNT_RISK_SCORE_TABLE_NAME}"
    return f"""
        INSERT INTO {table_name} ({insert_columns})
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


def upsert_account_risk_scores(
    engine: Engine,
    prepared_scores: pd.DataFrame,
    batch_size: int = 1000,
) -> int:
    """Upsert prepared account risk scores into mart.account_risk_scores."""

    if batch_size <= 0:
        raise ScoringPersistenceError("batch_size must be positive")
    if prepared_scores.empty:
        return 0
    try:
        validate_prepared_account_risk_score_frame(prepared_scores)
        rows = _records(prepared_scores.loc[:, ACCOUNT_RISK_SCORE_PERSISTED_COLUMNS])
        statement = text(build_account_risk_score_upsert_sql())
        with engine.begin() as connection:
            for start in range(0, len(rows), batch_size):
                connection.execute(statement, rows[start : start + batch_size])
        return len(rows)
    except ScoringValidationError as exc:
        raise ScoringPersistenceError(str(exc)) from exc
    except ScoringPersistenceError:
        raise
    except Exception as exc:
        raise ScoringPersistenceError(f"Failed to upsert account risk scores: {exc}") from exc


def _result_summary(prepared: pd.DataFrame, rows_persisted: int) -> dict[str, object]:
    return {
        "rows_prepared": int(len(prepared)),
        "rows_persisted": int(rows_persisted),
        "unique_account_count": int(prepared["account_id"].nunique()) if not prepared.empty else 0,
        "persisted": rows_persisted > 0,
    }


def persist_account_risk_scores(
    engine: Engine,
    result: AccountRiskScoreResult,
    config: AccountRiskScorePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> AccountRiskScorePersistenceResult:
    """Prepare, upsert, and optionally audit account risk scores."""

    resolved = AccountRiskScorePersistenceConfig() if config is None else config
    try:
        prepared = prepare_account_risk_scores_for_persistence(
            result,
            config=resolved,
            extra_metadata=extra_metadata,
        )
        rows_persisted = upsert_account_risk_scores(engine, prepared, resolved.batch_size)
        persistence_result = AccountRiskScorePersistenceResult(
            rows_prepared=len(prepared),
            rows_persisted=rows_persisted,
            unique_account_count=int(prepared["account_id"].nunique()) if not prepared.empty else 0,
            score_date=str(prepared.iloc[0]["score_date"]) if not prepared.empty else None,
            score_name=str(prepared.iloc[0]["score_name"])
            if not prepared.empty
            else resolved.score_name,
            score_version=str(prepared.iloc[0]["score_version"])
            if not prepared.empty
            else resolved.score_version,
            persisted=rows_persisted > 0,
            metadata=dict(prepared.iloc[0]["metadata"]) if not prepared.empty else {},
            summary=_result_summary(prepared, rows_persisted),
        )
        if resolved.write_audit:
            write_account_risk_score_audit_event(engine, persistence_result, status="success")
        return persistence_result
    except ScoringPersistenceError:
        raise
    except Exception as exc:
        raise ScoringPersistenceError(f"Failed to persist account risk scores: {exc}") from exc


def write_account_risk_score_audit_event(
    engine: Engine,
    result: AccountRiskScorePersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    """Write one governance audit event for risk score persistence."""

    details = {
        "rows_prepared": int(result.rows_prepared),
        "rows_persisted": int(result.rows_persisted),
        "unique_account_count": int(result.unique_account_count),
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
                    "event_type": "risk_scoring",
                    "component": "scoring",
                    "run_id": run_id,
                    "pipeline_stage": "account_risk_scoring",
                    "entity_type": "score_table",
                    "entity_id": (
                        f"{ACCOUNT_RISK_SCORE_TABLE_SCHEMA}.{ACCOUNT_RISK_SCORE_TABLE_NAME}"
                    ),
                    "action": "persist_account_risk_scores",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise ScoringPersistenceError(
            f"Failed to write account risk score audit event: {exc}"
        ) from exc
