"""PostgreSQL persistence for generated AML cases."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.cases.exceptions import CasePersistenceError, CaseValidationError
from graph_aml.cases.generation import CaseGenerationResult
from graph_aml.cases.grouping import (
    CASE_ALERT_LINK_COLUMNS,
    CASE_ENTITY_LINK_COLUMNS,
)
from graph_aml.cases.validation import validate_prepared_case_frames

CASE_TABLE_SCHEMA = "aml"
CASE_TABLE_NAME = "cases"
CASE_ALERT_TABLE_NAME = "case_alerts"
CASE_ENTITY_TABLE_NAME = "case_entities"
DEFAULT_CASE_VERSION = "case_generation_v1"

CASE_PERSISTED_COLUMNS = (
    "case_id",
    "case_version",
    "primary_account_id",
    "primary_customer_id",
    "related_accounts",
    "related_customers",
    "alert_ids",
    "typologies",
    "rule_names",
    "total_transaction_value",
    "alert_count",
    "unique_typology_count",
    "evidence_transaction_count",
    "max_rule_risk_score",
    "mean_rule_risk_score",
    "max_account_risk_score",
    "priority_score",
    "severity",
    "status",
    "grouping_strategy",
    "case_group_key",
    "summary",
    "metadata",
    "created_at",
    "updated_at",
)
_CASE_JSON_COLUMNS = (
    "related_accounts",
    "related_customers",
    "alert_ids",
    "typologies",
    "rule_names",
    "metadata",
)


@dataclass(frozen=True)
class CasePersistenceConfig:
    case_version: str = DEFAULT_CASE_VERSION
    batch_size: int = 1000
    write_audit: bool = True

    def __post_init__(self) -> None:
        validate_case_persistence_config(self)


@dataclass(frozen=True)
class CasePersistenceResult:
    cases_prepared: int = 0
    cases_persisted: int = 0
    case_alert_links_persisted: int = 0
    case_entity_links_persisted: int = 0
    unique_primary_account_count: int = 0
    case_version: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def validate_case_persistence_config(config: CasePersistenceConfig) -> None:
    if not isinstance(config, CasePersistenceConfig):
        raise CasePersistenceError("config must be CasePersistenceConfig")
    if not config.case_version.strip():
        raise CasePersistenceError("case_version must be non-empty")
    if config.batch_size <= 0:
        raise CasePersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise CasePersistenceError("write_audit must be boolean")


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


def prepare_cases_for_persistence(
    result: CaseGenerationResult,
    config: CasePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> dict[str, pd.DataFrame]:
    resolved = CasePersistenceConfig() if config is None else config
    try:
        cases = result.cases.copy(deep=True)
        if cases.empty:
            cases = pd.DataFrame(columns=CASE_PERSISTED_COLUMNS)
        else:
            cases["case_version"] = resolved.case_version
            cases["metadata"] = [
                _json_safe(
                    {
                        "generation_summary": result.summary,
                        "generation_metadata": result.metadata,
                        "extra_metadata": extra_metadata or {},
                    }
                )
            ] * len(cases)
            for column in _CASE_JSON_COLUMNS:
                if column not in cases.columns:
                    cases[column] = [[] for _ in range(len(cases))]
            cases = cases.loc[:, CASE_PERSISTED_COLUMNS]
        case_alerts = result.case_alerts.copy(deep=True)
        case_entities = result.case_entities.copy(deep=True)
        prepared = {
            "cases": cases.reset_index(drop=True),
            "case_alerts": case_alerts.loc[:, CASE_ALERT_LINK_COLUMNS]
            .drop_duplicates()
            .reset_index(drop=True)
            if not case_alerts.empty
            else pd.DataFrame(columns=CASE_ALERT_LINK_COLUMNS),
            "case_entities": case_entities.loc[:, CASE_ENTITY_LINK_COLUMNS]
            .drop_duplicates()
            .reset_index(drop=True)
            if not case_entities.empty
            else pd.DataFrame(columns=CASE_ENTITY_LINK_COLUMNS),
        }
        validate_prepared_case_frames(prepared)
        return prepared
    except CaseValidationError as exc:
        raise CasePersistenceError(str(exc)) from exc
    except CasePersistenceError:
        raise
    except Exception as exc:
        raise CasePersistenceError(f"Failed to prepare cases for persistence: {exc}") from exc


def build_case_upsert_sql() -> str:
    insert_columns = ", ".join(CASE_PERSISTED_COLUMNS)
    placeholders = ", ".join(
        f"CAST(:{column} AS JSONB)" if column in _CASE_JSON_COLUMNS else f":{column}"
        for column in CASE_PERSISTED_COLUMNS
    )
    update_columns = [
        column for column in CASE_PERSISTED_COLUMNS if column not in ("case_id", "created_at")
    ]
    update_clause = ",\n            ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )
    return f"""
        INSERT INTO {CASE_TABLE_SCHEMA}.{CASE_TABLE_NAME} ({insert_columns})
        VALUES ({placeholders})
        ON CONFLICT (case_id) DO UPDATE SET
            {update_clause}
    """


def build_case_alert_upsert_sql() -> str:
    return """
        INSERT INTO aml.case_alerts (case_id, alert_id)
        VALUES (:case_id, :alert_id)
        ON CONFLICT (case_id, alert_id) DO NOTHING
    """


def build_case_entity_upsert_sql() -> str:
    return """
        INSERT INTO aml.case_entities (case_id, entity_type, entity_id, relationship)
        VALUES (:case_id, :entity_type, :entity_id, :relationship)
        ON CONFLICT (case_id, entity_type, entity_id, relationship) DO NOTHING
    """


def _upsert_frame(
    engine: Engine, frame: pd.DataFrame, sql: str, columns: tuple[str, ...], batch_size: int
) -> int:
    if batch_size <= 0:
        raise CasePersistenceError("batch_size must be positive")
    if frame.empty:
        return 0
    rows = _records(frame.loc[:, columns])
    statement = text(sql)
    with engine.begin() as connection:
        for start in range(0, len(rows), batch_size):
            connection.execute(statement, rows[start : start + batch_size])
    return len(rows)


def upsert_cases(engine: Engine, cases: pd.DataFrame, batch_size: int = 1000) -> int:
    try:
        return _upsert_frame(
            engine, cases, build_case_upsert_sql(), CASE_PERSISTED_COLUMNS, batch_size
        )
    except Exception as exc:
        if isinstance(exc, CasePersistenceError):
            raise
        raise CasePersistenceError(f"Failed to upsert cases: {exc}") from exc


def upsert_case_alerts(engine: Engine, case_alerts: pd.DataFrame, batch_size: int = 1000) -> int:
    try:
        return _upsert_frame(
            engine, case_alerts, build_case_alert_upsert_sql(), CASE_ALERT_LINK_COLUMNS, batch_size
        )
    except Exception as exc:
        if isinstance(exc, CasePersistenceError):
            raise
        raise CasePersistenceError(f"Failed to upsert case-alert links: {exc}") from exc


def upsert_case_entities(
    engine: Engine, case_entities: pd.DataFrame, batch_size: int = 1000
) -> int:
    try:
        return _upsert_frame(
            engine,
            case_entities,
            build_case_entity_upsert_sql(),
            CASE_ENTITY_LINK_COLUMNS,
            batch_size,
        )
    except Exception as exc:
        if isinstance(exc, CasePersistenceError):
            raise
        raise CasePersistenceError(f"Failed to upsert case-entity links: {exc}") from exc


def persist_cases(
    engine: Engine,
    result: CaseGenerationResult,
    config: CasePersistenceConfig | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> CasePersistenceResult:
    resolved = CasePersistenceConfig() if config is None else config
    try:
        prepared = prepare_cases_for_persistence(result, resolved, extra_metadata)
        cases_persisted = upsert_cases(engine, prepared["cases"], resolved.batch_size)
        alerts_persisted = upsert_case_alerts(engine, prepared["case_alerts"], resolved.batch_size)
        entities_persisted = upsert_case_entities(
            engine, prepared["case_entities"], resolved.batch_size
        )
        persistence_result = CasePersistenceResult(
            cases_prepared=len(prepared["cases"]),
            cases_persisted=cases_persisted,
            case_alert_links_persisted=alerts_persisted,
            case_entity_links_persisted=entities_persisted,
            unique_primary_account_count=int(
                prepared["cases"]["primary_account_id"].nunique(dropna=True)
            )
            if not prepared["cases"].empty
            else 0,
            case_version=resolved.case_version,
            persisted=cases_persisted > 0,
            metadata=dict(prepared["cases"].iloc[0]["metadata"])
            if not prepared["cases"].empty
            else {},
            summary={
                "cases_prepared": int(len(prepared["cases"])),
                "cases_persisted": int(cases_persisted),
                "case_alert_links_persisted": int(alerts_persisted),
                "case_entity_links_persisted": int(entities_persisted),
            },
        )
        if resolved.write_audit:
            write_case_generation_audit_event(engine, persistence_result, status="success")
        return persistence_result
    except CasePersistenceError:
        raise
    except Exception as exc:
        raise CasePersistenceError(f"Failed to persist generated cases: {exc}") from exc


def write_case_generation_audit_event(
    engine: Engine,
    result: CasePersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    details = {
        "cases_prepared": int(result.cases_prepared),
        "cases_persisted": int(result.cases_persisted),
        "case_alert_links_persisted": int(result.case_alert_links_persisted),
        "case_entity_links_persisted": int(result.case_entity_links_persisted),
        "unique_primary_account_count": int(result.unique_primary_account_count),
        "case_version": result.case_version,
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
                    "event_type": "case_generation",
                    "component": "cases",
                    "run_id": run_id,
                    "pipeline_stage": "case_generation",
                    "entity_type": "case_table",
                    "entity_id": "aml.cases",
                    "action": "persist_generated_cases",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise CasePersistenceError(f"Failed to write case generation audit event: {exc}") from exc
