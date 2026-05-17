"""Governance audit events for account feature persistence."""

from __future__ import annotations

import json

from sqlalchemy import Engine, text

from graph_aml.features.exceptions import FeatureAuditError


def write_feature_persistence_audit_event(
    engine: Engine,
    row_count: int,
    account_count: int,
    feature_date_count: int,
    feature_version: str,
    status: str,
    run_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    """Write one governance audit event for account feature persistence."""

    details = {
        "row_count": int(row_count),
        "account_count": int(account_count),
        "feature_date_count": int(feature_date_count),
        "feature_version": feature_version,
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
                    "event_type": "feature_persistence",
                    "component": "features",
                    "run_id": run_id,
                    "pipeline_stage": "feature_persistence",
                    "entity_type": "feature_table",
                    "entity_id": "mart.features_account_daily",
                    "action": "persist_account_features",
                    "status": status,
                    "details": json.dumps(details, sort_keys=True, default=str),
                    "created_by": "system",
                },
            )
    except Exception as exc:
        raise FeatureAuditError(f"Failed to write feature persistence audit event: {exc}") from exc
