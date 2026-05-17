"""High-level governance inventory builders and workflow."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

import pandas as pd
from sqlalchemy import Engine

from graph_aml.governance.artefact_registry import build_artefact_registry
from graph_aml.governance.config import GovernanceInventoryConfig
from graph_aml.governance.exceptions import GovernanceInventoryError
from graph_aml.governance.inventory_inputs import read_governance_inventory_inputs
from graph_aml.governance.lineage_builder import (
    build_governance_lineage,
    build_inventory_run_id,
)
from graph_aml.governance.lineage_models import (
    MODEL_INVENTORY_COLUMNS,
    VALIDATION_INVENTORY_COLUMNS,
    GovernanceInventoryBuildResult,
)
from graph_aml.governance.validation import validate_governance_inventory_result


def _empty(columns: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _first_existing(row: pd.Series, columns: tuple[str, ...]) -> object:
    for column in columns:
        if column in row.index and pd.notna(row[column]):
            return row[column]
    return None


def _timestamp_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for column in candidates:
        if column in frame.columns:
            return column
    return None


def build_model_inventory(
    inputs: dict[str, object],
    inventory_run_id: str,
) -> pd.DataFrame:
    """Summarise model run tables into a compact model inventory."""

    model_runs = inputs.get("model_runs", {})
    if not isinstance(model_runs, dict):
        return _empty(MODEL_INVENTORY_COLUMNS)
    rows: list[dict[str, object]] = []
    for source_name, frame in cast("dict[str, pd.DataFrame]", model_runs).items():
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        model_col = "model_name" if "model_name" in frame.columns else None
        version_col = "model_version" if "model_version" in frame.columns else None
        family_col = "model_family" if "model_family" in frame.columns else "model_type"
        dataset_col = "dataset_version" if "dataset_version" in frame.columns else "feature_version"
        entity_col = "entity_level" if "entity_level" in frame.columns else None
        timestamp_col = _timestamp_column(frame, ("trained_at", "created_at", "training_end"))
        group_cols = [
            column
            for column in (model_col, version_col, family_col, dataset_col, entity_col)
            if column
        ]
        grouped = frame.groupby(group_cols, dropna=False) if group_cols else [((), frame)]
        for key, group in grouped:
            first = group.iloc[0]
            latest = group[timestamp_col].max() if timestamp_col else None
            rows.append(
                {
                    "inventory_run_id": inventory_run_id,
                    "model_name": str(
                        _first_existing(first, ("model_name", "experiment_name"))
                        or source_name
                    ),
                    "model_version": _first_existing(first, ("model_version",)),
                    "model_family": _first_existing(first, ("model_family", "model_type")),
                    "dataset_version": _first_existing(
                        first,
                        ("dataset_version", "feature_version"),
                    ),
                    "entity_level": _first_existing(first, ("entity_level",)),
                    "run_count": int(len(group)),
                    "latest_run_timestamp": latest,
                    "metadata": {"source": source_name, "group_key": str(key)},
                }
            )
    if not rows:
        return _empty(MODEL_INVENTORY_COLUMNS)
    return pd.DataFrame(rows, columns=MODEL_INVENTORY_COLUMNS).sort_values(
        ["model_name", "model_version"], na_position="last"
    )


def build_validation_inventory(
    inputs: dict[str, object],
    inventory_run_id: str,
) -> pd.DataFrame:
    """Summarise validation run tables into inventory rows."""

    validation_runs = inputs.get("validation_runs", {})
    if not isinstance(validation_runs, dict):
        return _empty(VALIDATION_INVENTORY_COLUMNS)
    specs = {
        "model_comparison_runs": (
            "model_comparison",
            "comparison_version",
            "comparison_run_id",
        ),
        "monitoring_runs": ("monitoring", "monitoring_version", "monitoring_run_id"),
        "explainability_runs": (
            "explainability",
            "explanation_version",
            "explanation_run_id",
        ),
    }
    rows: list[dict[str, object]] = []
    for source_name, frame in cast("dict[str, pd.DataFrame]", validation_runs).items():
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        validation_type, version_col, id_col = specs.get(
            source_name,
            (source_name.replace("_runs", ""), "version", "run_id"),
        )
        timestamp_col = _timestamp_column(frame, ("created_at", "trained_at"))
        if version_col in frame.columns:
            versions = cast(
                "Iterable[tuple[object, pd.DataFrame]]",
                frame.groupby(version_col, dropna=False),
            )
        else:
            versions = [(None, frame)]
        for version, group in versions:
            latest_group = (
                group.sort_values(timestamp_col, ascending=False).iloc[0]
                if timestamp_col
                else group.iloc[0]
            )
            rows.append(
                {
                    "inventory_run_id": inventory_run_id,
                    "validation_type": validation_type,
                    "validation_version": version,
                    "run_count": int(len(group)),
                    "latest_run_id": latest_group.get(id_col),
                    "latest_run_timestamp": (
                        latest_group.get(timestamp_col) if timestamp_col else None
                    ),
                    "summary": (
                        latest_group.get("summary", {})
                        if "summary" in latest_group.index
                        else {}
                    ),
                    "metadata": {"source": source_name},
                }
            )
    if not rows:
        return _empty(VALIDATION_INVENTORY_COLUMNS)
    return pd.DataFrame(rows, columns=VALIDATION_INVENTORY_COLUMNS).sort_values(
        ["validation_type", "validation_version"], na_position="last"
    )


def build_governance_inventory_from_inputs(
    inputs: dict[str, object],
    config: GovernanceInventoryConfig | None = None,
) -> GovernanceInventoryBuildResult:
    """Build all governance inventory frames without persistence."""

    resolved = config or GovernanceInventoryConfig()
    generated_at = pd.Timestamp.utcnow()
    inventory_run_id = build_inventory_run_id(resolved, generated_at)
    try:
        nodes, edges, process_inventory = build_governance_lineage(
            inputs,
            resolved,
            inventory_run_id,
        )
        artefact_registry = (
            build_artefact_registry(resolved, inventory_run_id)
            if resolved.include.validation_artefacts or resolved.include.documentation_files
            else pd.DataFrame()
        )
        model_inventory = build_model_inventory(inputs, inventory_run_id)
        validation_inventory = build_validation_inventory(inputs, inventory_run_id)
        summary = {
            "inventory_run_id": inventory_run_id,
            "inventory_version": resolved.inventory_version,
            "lineage_node_count": int(len(nodes)),
            "lineage_edge_count": int(len(edges)),
            "artefact_count": int(len(artefact_registry)),
            "process_count": int(len(process_inventory)),
            "model_inventory_count": int(len(model_inventory)),
            "validation_inventory_count": int(len(validation_inventory)),
            "generated_at": generated_at.isoformat(),
        }
        input_availability: dict[str, object] = {}
        for key, value in inputs.items():
            if isinstance(value, pd.DataFrame):
                input_availability[key] = len(value)
            elif isinstance(value, dict):
                input_availability[key] = sorted(str(item) for item in value.keys())
            else:
                input_availability[key] = str(type(value).__name__)
        metadata: dict[str, object] = {
            "inventory_name": resolved.inventory_name,
            "inventory_version": resolved.inventory_version,
            "input_availability": input_availability,
            "include": vars(resolved.include),
            "lineage": vars(resolved.lineage),
        }
        result = GovernanceInventoryBuildResult(
            inventory_run_id=inventory_run_id,
            lineage_nodes=nodes,
            lineage_edges=edges,
            artefact_registry=artefact_registry,
            process_inventory=process_inventory,
            model_inventory=model_inventory,
            validation_inventory=validation_inventory,
            summary=summary,
            metadata=metadata,
        )
        validate_governance_inventory_result(result)
        return result
    except GovernanceInventoryError:
        raise
    except Exception as exc:
        raise GovernanceInventoryError(f"failed to build governance inventory: {exc}") from exc


def build_and_persist_governance_inventory(
    engine: Engine,
    inventory_config: GovernanceInventoryConfig | None = None,
    persistence_config: object | None = None,
    limit: int | None = None,
    write_artefacts: bool = True,
) -> tuple[GovernanceInventoryBuildResult, object]:
    """Read inputs, build inventory, write artefacts, and persist when configured."""

    from graph_aml.governance.artefacts import generate_governance_inventory_artefacts
    from graph_aml.governance.persistence import (
        GovernanceInventoryPersistenceConfig,
        GovernanceInventoryPersistenceResult,
        persist_governance_inventory,
    )

    resolved = inventory_config or GovernanceInventoryConfig()
    print("governance inventory inputs read")
    inputs = read_governance_inventory_inputs(engine, resolved, limit=limit)
    print("lineage built")
    result = build_governance_inventory_from_inputs(inputs, resolved)
    print("artefact registry built")
    print("process inventory built")
    print("model inventory built")
    print("validation inventory built")
    if write_artefacts and resolved.persistence.write_artefacts:
        generate_governance_inventory_artefacts(result, resolved.persistence.artefact_output_dir)
        print("governance inventory artefacts written")
    if resolved.persistence.write_database:
        persistence = persistence_config or GovernanceInventoryPersistenceConfig(
            inventory_name=resolved.inventory_name,
            inventory_version=resolved.inventory_version,
            write_audit=resolved.persistence.write_audit,
        )
        persisted = persist_governance_inventory(
            engine,
            result,
            resolved,
            persistence,  # type: ignore[arg-type]
        )
        print("governance inventory persisted")
    else:
        persisted = GovernanceInventoryPersistenceResult(
            inventory_run_id=result.inventory_run_id,
            inventory_name=resolved.inventory_name,
            inventory_version=resolved.inventory_version,
            metadata=result.metadata,
            summary=result.summary,
        )
    return result, persisted
