"""Persistence utilities for governance inventory outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.governance.config import GovernanceInventoryConfig
from graph_aml.governance.exceptions import GovernanceInventoryPersistenceError
from graph_aml.governance.lineage_models import GovernanceInventoryBuildResult


@dataclass(frozen=True)
class GovernanceInventoryPersistenceConfig:
    inventory_name: str = "aml_governance_inventory"
    inventory_version: str = "governance_inventory_v1"
    batch_size: int = 1000
    write_audit: bool = True


@dataclass(frozen=True)
class GovernanceInventoryPersistenceResult:
    inventory_run_id: str | None = None
    inventory_run_persisted: bool = False
    lineage_nodes_persisted: int = 0
    lineage_edges_persisted: int = 0
    artefacts_persisted: int = 0
    processes_persisted: int = 0
    models_persisted: int = 0
    validations_persisted: int = 0
    inventory_name: str | None = None
    inventory_version: str | None = None
    persisted: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)


def validate_governance_inventory_persistence_config(
    config: GovernanceInventoryPersistenceConfig,
) -> None:
    if not config.inventory_name.strip() or not config.inventory_version.strip():
        raise GovernanceInventoryPersistenceError("inventory name and version must be non-empty")
    if config.batch_size <= 0:
        raise GovernanceInventoryPersistenceError("batch_size must be positive")
    if not isinstance(config.write_audit, bool):
        raise GovernanceInventoryPersistenceError("write_audit must be boolean")


def build_inventory_run_insert_sql() -> str:
    return """
    INSERT INTO governance.inventory_runs (
        inventory_run_id, inventory_name, inventory_version, lineage_node_count,
        lineage_edge_count, artefact_count, process_count, model_inventory_count,
        validation_inventory_count, summary, metadata
    ) VALUES (
        :inventory_run_id, :inventory_name, :inventory_version, :lineage_node_count,
        :lineage_edge_count, :artefact_count, :process_count, :model_inventory_count,
        :validation_inventory_count, CAST(:summary AS jsonb), CAST(:metadata AS jsonb)
    )
    ON CONFLICT (inventory_run_id) DO NOTHING
    """


def build_lineage_node_upsert_sql() -> str:
    return """
    INSERT INTO governance.lineage_nodes (
        inventory_run_id, node_id, node_type, name, schema_name, version, row_count, metadata
    ) VALUES (
        :inventory_run_id, :node_id, :node_type, :name, :schema_name, :version,
        :row_count, CAST(:metadata AS jsonb)
    )
    ON CONFLICT (inventory_run_id, node_id) DO UPDATE SET
        node_type = EXCLUDED.node_type,
        name = EXCLUDED.name,
        schema_name = EXCLUDED.schema_name,
        version = EXCLUDED.version,
        row_count = EXCLUDED.row_count,
        metadata = EXCLUDED.metadata
    """


def build_lineage_edge_upsert_sql() -> str:
    return """
    INSERT INTO governance.lineage_edges (
        inventory_run_id, source_id, target_id, relationship_type, process_name, metadata
    ) VALUES (
        :inventory_run_id, :source_id, :target_id, :relationship_type,
        :process_name, CAST(:metadata AS jsonb)
    )
    ON CONFLICT (inventory_run_id, source_id, target_id, relationship_type) DO UPDATE SET
        process_name = EXCLUDED.process_name,
        metadata = EXCLUDED.metadata
    """


def build_artefact_registry_upsert_sql() -> str:
    return """
    INSERT INTO governance.artefact_registry (
        inventory_run_id, artefact_id, artefact_type, file_name, relative_path,
        extension, size_bytes, hash_value, modified_at, source_dir, metadata
    ) VALUES (
        :inventory_run_id, :artefact_id, :artefact_type, :file_name, :relative_path,
        :extension, :size_bytes, :hash_value, :modified_at, :source_dir,
        CAST(:metadata AS jsonb)
    )
    ON CONFLICT (inventory_run_id, artefact_id) DO UPDATE SET
        artefact_type = EXCLUDED.artefact_type,
        file_name = EXCLUDED.file_name,
        relative_path = EXCLUDED.relative_path,
        extension = EXCLUDED.extension,
        size_bytes = EXCLUDED.size_bytes,
        hash_value = EXCLUDED.hash_value,
        modified_at = EXCLUDED.modified_at,
        source_dir = EXCLUDED.source_dir,
        metadata = EXCLUDED.metadata
    """


def build_process_inventory_upsert_sql() -> str:
    return """
    INSERT INTO governance.process_inventory (
        inventory_run_id, process_name, input_count, output_count, inputs, outputs,
        latest_audit_timestamp, latest_status, metadata
    ) VALUES (
        :inventory_run_id, :process_name, :input_count, :output_count,
        CAST(:inputs AS jsonb), CAST(:outputs AS jsonb), :latest_audit_timestamp,
        :latest_status, CAST(:metadata AS jsonb)
    )
    ON CONFLICT (inventory_run_id, process_name) DO UPDATE SET
        input_count = EXCLUDED.input_count,
        output_count = EXCLUDED.output_count,
        inputs = EXCLUDED.inputs,
        outputs = EXCLUDED.outputs,
        latest_audit_timestamp = EXCLUDED.latest_audit_timestamp,
        latest_status = EXCLUDED.latest_status,
        metadata = EXCLUDED.metadata
    """


def build_model_inventory_insert_sql() -> str:
    return """
    INSERT INTO governance.model_inventory (
        inventory_run_id, model_name, model_version, model_family, dataset_version,
        entity_level, run_count, latest_run_timestamp, metadata
    ) VALUES (
        :inventory_run_id, :model_name, :model_version, :model_family, :dataset_version,
        :entity_level, :run_count, :latest_run_timestamp, CAST(:metadata AS jsonb)
    )
    """


def build_validation_inventory_insert_sql() -> str:
    return """
    INSERT INTO governance.validation_inventory (
        inventory_run_id, validation_type, validation_version, run_count, latest_run_id,
        latest_run_timestamp, summary, metadata
    ) VALUES (
        :inventory_run_id, :validation_type, :validation_version, :run_count,
        :latest_run_id, :latest_run_timestamp, CAST(:summary AS jsonb), CAST(:metadata AS jsonb)
    )
    """


def _json_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    prepared = frame.astype(object).where(pd.notna(frame), cast(Any, None)).copy()
    for column in columns:
        if column in prepared.columns:
            prepared[column] = [
                json.dumps(value if value is not None else {}, sort_keys=True, default=str)
                for value in prepared[column].tolist()
            ]
    return prepared


def _records(
    frame: pd.DataFrame,
    json_columns: tuple[str, ...] = ("metadata",),
) -> list[dict[str, object]]:
    if frame.empty:
        return []
    return cast(
        list[dict[str, object]],
        _json_columns(frame, json_columns).to_dict(orient="records"),
    )


def persist_governance_inventory(
    engine: Engine,
    result: GovernanceInventoryBuildResult,
    config: GovernanceInventoryConfig | None = None,
    persistence_config: GovernanceInventoryPersistenceConfig | None = None,
) -> GovernanceInventoryPersistenceResult:
    """Persist governance inventory frames."""

    resolved = config or GovernanceInventoryConfig()
    persistence = persistence_config or GovernanceInventoryPersistenceConfig(
        inventory_name=resolved.inventory_name,
        inventory_version=resolved.inventory_version,
        write_audit=resolved.persistence.write_audit,
    )
    validate_governance_inventory_persistence_config(persistence)
    run_row = {
        "inventory_run_id": result.inventory_run_id,
        "inventory_name": resolved.inventory_name,
        "inventory_version": resolved.inventory_version,
        "lineage_node_count": len(result.lineage_nodes),
        "lineage_edge_count": len(result.lineage_edges),
        "artefact_count": len(result.artefact_registry),
        "process_count": len(result.process_inventory),
        "model_inventory_count": len(result.model_inventory),
        "validation_inventory_count": len(result.validation_inventory),
        "summary": json.dumps(result.summary, sort_keys=True, default=str),
        "metadata": json.dumps(result.metadata, sort_keys=True, default=str),
    }
    try:
        with engine.begin() as connection:
            connection.execute(text(build_inventory_run_insert_sql()), run_row)
            for frame, sql, json_columns in (
                (result.lineage_nodes, build_lineage_node_upsert_sql(), ("metadata",)),
                (result.lineage_edges, build_lineage_edge_upsert_sql(), ("metadata",)),
                (result.artefact_registry, build_artefact_registry_upsert_sql(), ("metadata",)),
                (
                    result.process_inventory,
                    build_process_inventory_upsert_sql(),
                    ("inputs", "outputs", "metadata"),
                ),
                (result.model_inventory, build_model_inventory_insert_sql(), ("metadata",)),
                (
                    result.validation_inventory,
                    build_validation_inventory_insert_sql(),
                    ("summary", "metadata"),
                ),
            ):
                rows = _records(frame, json_columns)
                if rows:
                    connection.execute(text(sql), rows)
        persisted = GovernanceInventoryPersistenceResult(
            inventory_run_id=result.inventory_run_id,
            inventory_run_persisted=True,
            lineage_nodes_persisted=len(result.lineage_nodes),
            lineage_edges_persisted=len(result.lineage_edges),
            artefacts_persisted=len(result.artefact_registry),
            processes_persisted=len(result.process_inventory),
            models_persisted=len(result.model_inventory),
            validations_persisted=len(result.validation_inventory),
            inventory_name=resolved.inventory_name,
            inventory_version=resolved.inventory_version,
            persisted=True,
            metadata=result.metadata,
            summary=result.summary,
        )
        if persistence.write_audit:
            write_governance_inventory_audit_event(
                engine,
                persisted,
                run_id=result.inventory_run_id,
            )
        return persisted
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(
            f"failed to persist governance inventory: {exc}"
        ) from exc


def write_governance_inventory_audit_event(
    engine: Engine,
    result: GovernanceInventoryPersistenceResult,
    status: str = "success",
    run_id: str | None = None,
) -> None:
    """Write governance inventory audit event."""

    details = {
        "inventory_run_id": result.inventory_run_id,
        "lineage_nodes_persisted": result.lineage_nodes_persisted,
        "lineage_edges_persisted": result.lineage_edges_persisted,
        "artefacts_persisted": result.artefacts_persisted,
        "processes_persisted": result.processes_persisted,
        "models_persisted": result.models_persisted,
        "validations_persisted": result.validations_persisted,
        "inventory_name": result.inventory_name,
        "inventory_version": result.inventory_version,
        "summary": result.summary,
        "metadata": result.metadata,
    }
    sql = """
    INSERT INTO governance.audit_events (
        event_type, component, run_id, pipeline_stage, action, status, details
    ) VALUES (
        :event_type, :component, :run_id, :pipeline_stage, :action, :status,
        CAST(:details AS jsonb)
    )
    """
    params = {
        "event_type": "governance_inventory",
        "component": "governance",
        "run_id": run_id or result.inventory_run_id,
        "pipeline_stage": "governance_inventory",
        "action": "persist_governance_inventory",
        "status": status,
        "details": json.dumps(details, sort_keys=True, default=str),
    }
    try:
        with engine.begin() as connection:
            connection.execute(text(sql), params)
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(
            f"failed to write governance inventory audit event: {exc}"
        ) from exc
