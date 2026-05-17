"""Governance audit events for AML alert persistence."""

from __future__ import annotations

import json

from sqlalchemy import Engine, text

from graph_aml.alerts.exceptions import AlertAuditError


def write_alert_persistence_audit_event(
    engine: Engine,
    alert_count: int,
    rule_name_counts: dict[str, int],
    severity_counts: dict[str, int],
    status: str,
    run_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    """Write one governance audit event for alert persistence."""

    details = {
        "alert_count": int(alert_count),
        "rule_name_counts": rule_name_counts,
        "severity_counts": severity_counts,
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
                    "event_type": "alert_persistence",
                    "component": "alerts",
                    "run_id": run_id,
                    "pipeline_stage": "alert_persistence",
                    "entity_type": "alert_table",
                    "entity_id": "aml.alerts",
                    "action": "persist_alerts",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise AlertAuditError(f"Failed to write alert persistence audit event: {exc}") from exc
