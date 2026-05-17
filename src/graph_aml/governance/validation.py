"""Validation helpers for governance inventory outputs."""

from __future__ import annotations

import re

import pandas as pd

from graph_aml.governance.artefact_registry import ARTEFACT_REGISTRY_COLUMNS
from graph_aml.governance.exceptions import GovernanceInventoryValidationError
from graph_aml.governance.lineage_models import (
    LINEAGE_EDGE_COLUMNS,
    LINEAGE_NODE_COLUMNS,
    GovernanceInventoryBuildResult,
)


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise GovernanceInventoryValidationError(f"{name} is missing columns: {missing}")


def validate_lineage_frames(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
) -> None:
    _require_columns(nodes, LINEAGE_NODE_COLUMNS, "lineage nodes")
    _require_columns(edges, LINEAGE_EDGE_COLUMNS, "lineage edges")
    if not nodes.empty and nodes["inventory_run_id"].isna().any():
        raise GovernanceInventoryValidationError("lineage nodes require inventory_run_id")
    if not edges.empty and edges["inventory_run_id"].isna().any():
        raise GovernanceInventoryValidationError("lineage edges require inventory_run_id")


def validate_artefact_registry(
    artefacts: pd.DataFrame,
) -> None:
    _require_columns(artefacts, ARTEFACT_REGISTRY_COLUMNS, "artefact registry")
    if artefacts.empty:
        return
    if artefacts["artefact_id"].astype(str).str.strip().eq("").any():
        raise GovernanceInventoryValidationError("artefact IDs must be non-empty")
    if artefacts["relative_path"].astype(str).str.strip().eq("").any():
        raise GovernanceInventoryValidationError("artefact relative paths must be non-empty")
    hashes = artefacts["hash_value"].dropna().astype(str)
    valid_hashes = hashes.map(
        lambda value: bool(re.fullmatch(r"[0-9a-fA-F]{32,64}", value))
    )
    if not hashes.empty and not valid_hashes.all():
        raise GovernanceInventoryValidationError("artefact hash values are malformed")


def validate_governance_inventory_result(
    result: GovernanceInventoryBuildResult,
) -> None:
    if not result.inventory_run_id.strip():
        raise GovernanceInventoryValidationError("inventory_run_id must be non-empty")
    validate_lineage_frames(result.lineage_nodes, result.lineage_edges)
    validate_artefact_registry(result.artefact_registry)


def build_governance_inventory_quality_summary(
    result: GovernanceInventoryBuildResult,
) -> dict[str, object]:
    known_nodes = set(result.lineage_nodes.get("node_id", pd.Series(dtype=str)).astype(str))
    orphan_edges = 0
    if not result.lineage_edges.empty:
        edge_nodes = set(result.lineage_edges["source_id"].astype(str)) | set(
            result.lineage_edges["target_id"].astype(str)
        )
        orphan_edges = len(edge_nodes - known_nodes)
    missing_hash_count = (
        int(result.artefact_registry["hash_value"].isna().sum())
        if "hash_value" in result.artefact_registry.columns
        else 0
    )
    return {
        "node_count": int(len(result.lineage_nodes)),
        "edge_count": int(len(result.lineage_edges)),
        "orphan_edge_count": orphan_edges,
        "artefact_count": int(len(result.artefact_registry)),
        "missing_hash_count": missing_hash_count,
        "process_count": int(len(result.process_inventory)),
        "model_count": int(len(result.model_inventory)),
        "validation_count": int(len(result.validation_inventory)),
    }


def compare_inventory_row_counts(
    source: pd.DataFrame,
    persisted: pd.DataFrame,
) -> dict[str, object]:
    source_count = int(len(source))
    persisted_count = int(len(persisted))
    return {
        "source_count": source_count,
        "persisted_count": persisted_count,
        "matches": source_count == persisted_count,
        "difference": persisted_count - source_count,
        "warnings": [] if source_count == persisted_count else ["row_count_mismatch"],
    }
