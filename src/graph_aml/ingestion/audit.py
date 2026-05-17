"""Audit event writing for raw ingestion workflows."""

from __future__ import annotations

import json

from sqlalchemy import Engine, text

from graph_aml.ingestion.exceptions import IngestionAuditError


def write_ingestion_audit_event(
    engine: Engine,
    dataset_id: str,
    dataset_version: str,
    source_system: str,
    source_file: str,
    row_counts: dict[str, int],
    status: str,
    run_id: str | None = None,
) -> None:
    """Write one raw ingestion audit event."""

    details = {
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "source_file": source_file,
        "row_counts": row_counts,
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
                    "event_type": "raw_ingestion",
                    "component": "ingestion",
                    "run_id": run_id,
                    "pipeline_stage": "raw_load",
                    "entity_type": "dataset",
                    "entity_id": dataset_id,
                    "action": "load_persisted_dataset_to_raw",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": source_system,
                },
            )
    except Exception as exc:
        raise IngestionAuditError(f"Failed to write ingestion audit event: {exc}") from exc
