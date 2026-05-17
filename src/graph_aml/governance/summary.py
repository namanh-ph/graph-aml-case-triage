"""Summary helpers for governance inventory outputs."""

from __future__ import annotations

from typing import Any

import pandas as pd

from graph_aml.governance.lineage_models import GovernanceInventoryBuildResult


def _counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {
        str(key): int(value)
        for key, value in frame[column].astype(str).value_counts().sort_index().to_dict().items()
    }


def summarise_lineage_nodes(nodes: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(nodes)),
        "node_type_counts": _counts(nodes, "node_type"),
        "schema_counts": _counts(nodes, "schema_name"),
    }


def summarise_lineage_edges(edges: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(edges)),
        "relationship_type_counts": _counts(edges, "relationship_type"),
        "process_counts": _counts(edges, "process_name"),
    }


def summarise_artefact_registry(artefacts: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(artefacts)),
        "artefact_type_counts": _counts(artefacts, "artefact_type"),
        "extension_counts": _counts(artefacts, "extension"),
        "source_dir_counts": _counts(artefacts, "source_dir"),
    }


def summarise_process_inventory(processes: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(processes)),
        "processes": sorted(processes["process_name"].astype(str).tolist())
        if "process_name" in processes.columns and not processes.empty
        else [],
    }


def summarise_model_inventory(models: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(models)),
        "model_version_counts": _counts(models, "model_version"),
        "model_family_counts": _counts(models, "model_family"),
    }


def summarise_validation_inventory(validations: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(validations)),
        "validation_type_counts": _counts(validations, "validation_type"),
        "validation_version_counts": _counts(validations, "validation_version"),
    }


def governance_inventory_result_to_dict(
    result: GovernanceInventoryBuildResult,
) -> dict[str, object]:
    payload: dict[str, Any] = {
        "inventory_run_id": result.inventory_run_id,
        "summary": result.summary,
        "metadata": result.metadata,
        "lineage_nodes": summarise_lineage_nodes(result.lineage_nodes),
        "lineage_edges": summarise_lineage_edges(result.lineage_edges),
        "artefact_registry": summarise_artefact_registry(result.artefact_registry),
        "process_inventory": summarise_process_inventory(result.process_inventory),
        "model_inventory": summarise_model_inventory(result.model_inventory),
        "validation_inventory": summarise_validation_inventory(result.validation_inventory),
    }
    return dict(payload)
