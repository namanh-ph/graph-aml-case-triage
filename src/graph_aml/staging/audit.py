"""Governance audit event writing for staging transformations."""

from __future__ import annotations

import json

from sqlalchemy import Engine, text

from graph_aml.staging.exceptions import StagingAuditError


def write_staging_audit_event(
    engine: Engine,
    row_counts: dict[str, int],
    status: str,
    run_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    """Write one staging transformation audit event."""

    details = {
        "row_counts": row_counts,
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
                    "event_type": "staging_transformation",
                    "component": "staging",
                    "run_id": run_id,
                    "pipeline_stage": "staging_load",
                    "entity_type": "dataset",
                    "entity_id": None,
                    "action": "transform_raw_to_staging",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise StagingAuditError(f"Failed to write staging audit event: {exc}") from exc
