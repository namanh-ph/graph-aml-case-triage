"""Governance audit events for AML rule execution."""

from __future__ import annotations

import json

from sqlalchemy import Engine, text

from graph_aml.rules.exceptions import RuleAuditError


def write_rule_execution_audit_event(
    engine: Engine,
    rule_name: str,
    alerts_generated: int,
    alerts_persisted: int,
    status: str,
    run_id: str | None = None,
    metadata: dict[str, object] | None = None,
    action: str = "run_structuring_rule",
) -> None:
    """Write one rule execution audit event."""

    details = {
        "rule_name": rule_name,
        "alerts_generated": int(alerts_generated),
        "alerts_persisted": int(alerts_persisted),
        "metadata": {} if metadata is None else metadata,
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
                    "event_type": "rule_execution",
                    "component": "rules",
                    "run_id": run_id,
                    "pipeline_stage": "rule_execution",
                    "entity_type": "rule",
                    "entity_id": rule_name,
                    "action": action,
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise RuleAuditError(f"Failed to write rule execution audit event: {exc}") from exc


def write_rule_engine_audit_event(
    engine: Engine,
    rules_run: tuple[str, ...] | list[str],
    alerts_generated: int,
    alerts_persisted: int,
    status: str,
    run_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    """Write one unified rule-engine execution audit event."""

    details = {
        "rules_run": list(rules_run),
        "alerts_generated": int(alerts_generated),
        "alerts_persisted": int(alerts_persisted),
        "metadata": {} if metadata is None else metadata,
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
                    "event_type": "rule_engine_execution",
                    "component": "rules",
                    "run_id": run_id,
                    "pipeline_stage": "rule_execution",
                    "entity_type": "rule_engine",
                    "entity_id": "aml_rule_engine",
                    "action": "run_aml_rule_engine",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise RuleAuditError(f"Failed to write rule engine audit event: {exc}") from exc
