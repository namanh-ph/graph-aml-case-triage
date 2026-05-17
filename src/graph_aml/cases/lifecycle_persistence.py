"""Persistence utilities for AML case lifecycle actions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import Engine, text

from graph_aml.cases.exceptions import (
    CaseLifecyclePersistenceError,
    CaseLifecycleTransitionError,
    CaseLifecycleValidationError,
)
from graph_aml.cases.lifecycle import validate_case_status_transition
from graph_aml.cases.lifecycle_config import CaseLifecycleConfig
from graph_aml.cases.lifecycle_models import (
    CaseLifecycleAction,
    build_case_action_id,
    lifecycle_action_to_record,
    validate_case_lifecycle_action,
)


@dataclass(frozen=True)
class CaseLifecyclePersistenceConfig:
    lifecycle_version: str = "case_lifecycle_v1"
    write_audit: bool = True

    def __post_init__(self) -> None:
        validate_case_lifecycle_persistence_config(self)


@dataclass(frozen=True)
class CaseLifecyclePersistenceResult:
    action_id: str | None = None
    case_id: str | None = None
    action_type: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    current_status: str | None = None
    analyst_id: str | None = None
    persisted: bool = False
    case_updated: bool = False
    assignment_updated: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


def validate_case_lifecycle_persistence_config(
    config: CaseLifecyclePersistenceConfig,
) -> None:
    if not isinstance(config, CaseLifecyclePersistenceConfig):
        raise CaseLifecyclePersistenceError("config must be CaseLifecyclePersistenceConfig")
    if not config.lifecycle_version.strip():
        raise CaseLifecyclePersistenceError("lifecycle_version must be non-empty")
    if not isinstance(config.write_audit, bool):
        raise CaseLifecyclePersistenceError("write_audit must be boolean")


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]
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


def _to_db_record(record: dict[str, object]) -> dict[str, object]:
    prepared = dict(record)
    prepared["metadata"] = json.dumps(_json_safe(record.get("metadata", {})), sort_keys=True)
    return prepared


def build_case_lifecycle_event_insert_sql() -> str:
    return """
        INSERT INTO aml.case_lifecycle_events (
            action_id,
            case_id,
            action_type,
            analyst_id,
            from_status,
            to_status,
            assigned_to,
            queue,
            decision_reason,
            comment,
            metadata,
            action_timestamp
        )
        VALUES (
            :action_id,
            :case_id,
            :action_type,
            :analyst_id,
            :from_status,
            :to_status,
            :assigned_to,
            :queue,
            :decision_reason,
            :comment,
            CAST(:metadata AS JSONB),
            :action_timestamp
        )
    """


def build_case_status_update_sql() -> str:
    return """
        UPDATE aml.cases
        SET
            status = COALESCE(:to_status, status),
            updated_at = CURRENT_TIMESTAMP,
            last_decision_reason = COALESCE(:decision_reason, last_decision_reason),
            last_decision_at = :action_timestamp,
            closed_at = CASE
                WHEN :to_status IN ('Closed false positive', 'Closed suspicious', 'Archived')
                THEN COALESCE(closed_at, :action_timestamp)
                ELSE closed_at
            END
        WHERE case_id = :case_id
    """


def build_case_assignment_upsert_sql() -> str:
    return """
        INSERT INTO aml.case_assignments (
            case_id,
            assigned_to,
            queue,
            assigned_by,
            assigned_at,
            updated_at
        )
        VALUES (
            :case_id,
            :assigned_to,
            :queue,
            :analyst_id,
            :action_timestamp,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (case_id) DO UPDATE SET
            assigned_to = EXCLUDED.assigned_to,
            queue = EXCLUDED.queue,
            assigned_by = EXCLUDED.assigned_by,
            assigned_at = EXCLUDED.assigned_at,
            updated_at = CURRENT_TIMESTAMP
    """


def _case_assignment_snapshot_update_sql() -> str:
    return """
        UPDATE aml.cases
        SET
            assigned_to = :assigned_to,
            queue = :queue,
            updated_at = CURRENT_TIMESTAMP
        WHERE case_id = :case_id
    """


def insert_case_lifecycle_event(
    engine: Engine,
    action_record: dict[str, object],
) -> int:
    try:
        with engine.begin() as connection:
            connection.execute(
                text(build_case_lifecycle_event_insert_sql()), _to_db_record(action_record)
            )
        return 1
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to insert lifecycle event: {exc}") from exc


def update_case_status_snapshot(
    engine: Engine,
    action_record: dict[str, object],
) -> int:
    if action_record.get("to_status") is None:
        return 0
    try:
        with engine.begin() as connection:
            connection.execute(text(build_case_status_update_sql()), action_record)
        return 1
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to update case status: {exc}") from exc


def upsert_case_assignment(
    engine: Engine,
    action_record: dict[str, object],
) -> int:
    if action_record.get("action_type") != "assign":
        return 0
    try:
        with engine.begin() as connection:
            connection.execute(text(build_case_assignment_upsert_sql()), action_record)
            connection.execute(text(_case_assignment_snapshot_update_sql()), action_record)
        return 1
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to upsert case assignment: {exc}") from exc


def apply_case_lifecycle_action(
    engine: Engine,
    action: CaseLifecycleAction,
    config: CaseLifecycleConfig | None = None,
    persistence_config: CaseLifecyclePersistenceConfig | None = None,
) -> CaseLifecyclePersistenceResult:
    resolved = CaseLifecycleConfig() if config is None else config
    persistence = (
        CaseLifecyclePersistenceConfig() if persistence_config is None else persistence_config
    )
    try:
        validate_case_lifecycle_action(action, resolved)
        if action.from_status and action.to_status:
            validate_case_status_transition(action.from_status, action.to_status, resolved)
        record = lifecycle_action_to_record(action)
        record["metadata"] = {
            **cast(dict[str, object], record.get("metadata") or {}),
            "lifecycle_version": persistence.lifecycle_version,
        }
        record["action_id"] = build_case_action_id(
            CaseLifecycleAction(
                **{**action.__dict__, "action_timestamp": record["action_timestamp"]}
            )
        )
        event_count = insert_case_lifecycle_event(engine, record)
        status_count = update_case_status_snapshot(engine, record)
        assignment_count = upsert_case_assignment(engine, record)
        result = CaseLifecyclePersistenceResult(
            action_id=str(record["action_id"]),
            case_id=str(record["case_id"]),
            action_type=str(record["action_type"]),
            from_status=cast(str | None, record.get("from_status")),
            to_status=cast(str | None, record.get("to_status")),
            current_status=cast(str | None, record.get("to_status") or record.get("from_status")),
            analyst_id=str(record["analyst_id"]),
            persisted=event_count > 0,
            case_updated=status_count > 0,
            assignment_updated=assignment_count > 0,
            metadata=cast(dict[str, object], record["metadata"]),
        )
        if persistence.write_audit:
            write_case_lifecycle_audit_event(engine, result, status="success")
        return result
    except (CaseLifecyclePersistenceError, CaseLifecycleTransitionError):
        raise
    except CaseLifecycleValidationError as exc:
        raise CaseLifecyclePersistenceError(str(exc)) from exc
    except Exception as exc:
        raise CaseLifecyclePersistenceError(f"Failed to apply lifecycle action: {exc}") from exc


def write_case_lifecycle_audit_event(
    engine: Engine,
    result: CaseLifecyclePersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    details = {
        "action_id": result.action_id,
        "case_id": result.case_id,
        "action_type": result.action_type,
        "from_status": result.from_status,
        "to_status": result.to_status,
        "current_status": result.current_status,
        "analyst_id": result.analyst_id,
        "case_updated": bool(result.case_updated),
        "assignment_updated": bool(result.assignment_updated),
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
                    "event_type": "case_lifecycle_action",
                    "component": "cases",
                    "run_id": run_id,
                    "pipeline_stage": "case_lifecycle",
                    "entity_type": "case",
                    "entity_id": result.case_id,
                    "action": result.action_type or "case_lifecycle_action",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": result.analyst_id or "system",
                },
            )
    except Exception as exc:
        raise CaseLifecyclePersistenceError(
            f"Failed to write lifecycle audit event: {exc}"
        ) from exc
