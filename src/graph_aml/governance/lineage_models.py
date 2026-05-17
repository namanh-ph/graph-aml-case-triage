"""Dataclasses and record schemas for governance lineage."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class LineageNode:
    node_id: str
    node_type: str
    name: str
    schema_name: str | None = None
    version: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LineageEdge:
    source_id: str
    target_id: str
    relationship_type: str
    process_name: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceInventoryBuildResult:
    inventory_run_id: str
    lineage_nodes: pd.DataFrame
    lineage_edges: pd.DataFrame
    artefact_registry: pd.DataFrame
    process_inventory: pd.DataFrame
    model_inventory: pd.DataFrame
    validation_inventory: pd.DataFrame
    summary: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)


LINEAGE_NODE_COLUMNS = (
    "inventory_run_id",
    "node_id",
    "node_type",
    "name",
    "schema_name",
    "version",
    "row_count",
    "metadata",
)

LINEAGE_EDGE_COLUMNS = (
    "inventory_run_id",
    "source_id",
    "target_id",
    "relationship_type",
    "process_name",
    "metadata",
)

PROCESS_INVENTORY_COLUMNS = (
    "inventory_run_id",
    "process_name",
    "input_count",
    "output_count",
    "inputs",
    "outputs",
    "latest_audit_timestamp",
    "latest_status",
    "metadata",
)

MODEL_INVENTORY_COLUMNS = (
    "inventory_run_id",
    "model_name",
    "model_version",
    "model_family",
    "dataset_version",
    "entity_level",
    "run_count",
    "latest_run_timestamp",
    "metadata",
)

VALIDATION_INVENTORY_COLUMNS = (
    "inventory_run_id",
    "validation_type",
    "validation_version",
    "run_count",
    "latest_run_id",
    "latest_run_timestamp",
    "summary",
    "metadata",
)


def lineage_node_to_record(
    node: LineageNode,
    inventory_run_id: str,
) -> dict[str, object]:
    """Convert a lineage node to a JSON-serialisable row record."""

    return {
        "inventory_run_id": inventory_run_id,
        "node_id": node.node_id,
        "node_type": node.node_type,
        "name": node.name,
        "schema_name": node.schema_name,
        "version": node.version,
        "row_count": node.metadata.get("row_count"),
        "metadata": dict(node.metadata or {}),
    }


def lineage_edge_to_record(
    edge: LineageEdge,
    inventory_run_id: str,
) -> dict[str, object]:
    """Convert a lineage edge to a JSON-serialisable row record."""

    return {
        "inventory_run_id": inventory_run_id,
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "relationship_type": edge.relationship_type,
        "process_name": edge.process_name,
        "metadata": dict(edge.metadata or {}),
    }
