"""Build table, process, and run-dependency lineage records."""

from __future__ import annotations

import hashlib
import json
from typing import cast

import pandas as pd

from graph_aml.governance.config import GovernanceInventoryConfig
from graph_aml.governance.exceptions import LineageBuildError
from graph_aml.governance.lineage_models import (
    LINEAGE_EDGE_COLUMNS,
    LINEAGE_NODE_COLUMNS,
    PROCESS_INVENTORY_COLUMNS,
)


def _table_node_id(name: str) -> str:
    return f"table:{name}"


def _process_node_id(name: str) -> str:
    return f"process:{name}"


def _run_node_id(name: str) -> str:
    return f"run:{name}"


def _empty(columns: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def build_inventory_run_id(
    config: GovernanceInventoryConfig | None = None,
    generated_at: pd.Timestamp | None = None,
) -> str:
    """Build deterministic inventory run ID for fixed config and timestamp."""

    resolved = config or GovernanceInventoryConfig()
    timestamp = generated_at or pd.Timestamp.utcnow()
    payload = {
        "inventory_name": resolved.inventory_name,
        "inventory_version": resolved.inventory_version,
        "generated_at": pd.Timestamp(timestamp).isoformat(),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"{resolved.inventory_version}_{digest}"


def build_table_lineage_nodes(
    table_counts: pd.DataFrame,
    inventory_run_id: str,
) -> pd.DataFrame:
    """Build table lineage nodes from table count metadata."""

    try:
        if table_counts is None:
            raise LineageBuildError("table_counts is required")
        if table_counts.empty:
            return _empty(LINEAGE_NODE_COLUMNS)
        required = {"schema_name", "table_name"}
        if not required.issubset(table_counts.columns):
            raise LineageBuildError("table_counts must include schema_name and table_name")
        rows: list[dict[str, object]] = []
        sorted_counts = table_counts.copy().sort_values(["schema_name", "table_name"])
        for row in sorted_counts.to_dict("records"):
            schema_name = str(row.get("schema_name", "")).strip()
            table_name = str(row.get("table_name", "")).strip()
            full_name = f"{schema_name}.{table_name}" if schema_name else table_name
            rows.append(
                {
                    "inventory_run_id": inventory_run_id,
                    "node_id": _table_node_id(full_name),
                    "node_type": "table",
                    "name": full_name,
                    "schema_name": schema_name or None,
                    "version": None,
                    "row_count": int(row.get("row_count") or 0),
                    "metadata": {"source": "pg_stat_user_tables"},
                }
            )
        return pd.DataFrame(rows, columns=LINEAGE_NODE_COLUMNS).drop_duplicates("node_id")
    except GovernanceInventoryError:
        raise
    except Exception as exc:
        raise LineageBuildError(f"failed to build table lineage nodes: {exc}") from exc


class GovernanceInventoryError(Exception):
    """Internal sentinel for local exception handling."""


def _latest_audit(audit_events: pd.DataFrame, process_name: str) -> tuple[object, object]:
    if audit_events.empty:
        return None, None
    frame = audit_events.copy()
    mask = pd.Series(False, index=frame.index)
    for column in ("component", "pipeline_stage", "event_type", "action"):
        if column in frame.columns:
            mask = mask | frame[column].astype(str).str.contains(process_name, case=False, na=False)
    matches = frame.loc[mask]
    if matches.empty:
        return None, None
    timestamp_col = "event_timestamp" if "event_timestamp" in matches.columns else "created_at"
    matches = matches.sort_values(timestamp_col, ascending=False)
    latest = matches.iloc[0]
    return latest.get(timestamp_col), latest.get("status")


def build_process_lineage(
    config: GovernanceInventoryConfig | None = None,
    inventory_run_id: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build configured process lineage nodes and table/process edges."""

    resolved = config or GovernanceInventoryConfig()
    run_id = inventory_run_id or build_inventory_run_id(resolved)
    try:
        node_rows: list[dict[str, object]] = []
        edge_rows: list[dict[str, object]] = []
        process_rows: list[dict[str, object]] = []
        for process_name, payload in sorted(resolved.known_processes.items()):
            inputs = tuple(payload.get("inputs", ()))
            outputs = tuple(payload.get("outputs", ()))
            node_rows.append(
                {
                    "inventory_run_id": run_id,
                    "node_id": _process_node_id(process_name),
                    "node_type": "process",
                    "name": process_name,
                    "schema_name": None,
                    "version": resolved.inventory_version,
                    "row_count": None,
                    "metadata": {"max_dependency_depth": resolved.lineage.max_dependency_depth},
                }
            )
            for source in inputs:
                source_id = _table_node_id(source)
                node_rows.append(
                    {
                        "inventory_run_id": run_id,
                        "node_id": source_id,
                        "node_type": "table_pattern" if "*" in source else "table",
                        "name": source,
                        "schema_name": source.split(".", 1)[0] if "." in source else None,
                        "version": None,
                        "row_count": None,
                        "metadata": {"configured_dependency": True},
                    }
                )
                edge_rows.append(
                    {
                        "inventory_run_id": run_id,
                        "source_id": source_id,
                        "target_id": _process_node_id(process_name),
                        "relationship_type": "process_input",
                        "process_name": process_name,
                        "metadata": {},
                    }
                )
            for target in outputs:
                target_id = _table_node_id(target)
                node_rows.append(
                    {
                        "inventory_run_id": run_id,
                        "node_id": target_id,
                        "node_type": "table_pattern" if "*" in target else "table",
                        "name": target,
                        "schema_name": target.split(".", 1)[0] if "." in target else None,
                        "version": None,
                        "row_count": None,
                        "metadata": {"configured_dependency": True},
                    }
                )
                edge_rows.append(
                    {
                        "inventory_run_id": run_id,
                        "source_id": _process_node_id(process_name),
                        "target_id": target_id,
                        "relationship_type": "process_output",
                        "process_name": process_name,
                        "metadata": {},
                    }
                )
            process_rows.append(
                {
                    "inventory_run_id": run_id,
                    "process_name": process_name,
                    "input_count": len(inputs),
                    "output_count": len(outputs),
                    "inputs": list(inputs),
                    "outputs": list(outputs),
                    "latest_audit_timestamp": None,
                    "latest_status": None,
                    "metadata": {"configured": True},
                }
            )
        nodes = pd.DataFrame(node_rows, columns=LINEAGE_NODE_COLUMNS)
        edges = pd.DataFrame(edge_rows, columns=LINEAGE_EDGE_COLUMNS)
        processes = pd.DataFrame(process_rows, columns=PROCESS_INVENTORY_COLUMNS)
        if not nodes.empty:
            nodes = nodes.drop_duplicates("node_id").sort_values(["node_type", "name"])
        if not edges.empty:
            edges = edges.drop_duplicates(
                ["source_id", "target_id", "relationship_type", "process_name"]
            ).sort_values(["process_name", "relationship_type", "source_id", "target_id"])
        return nodes.reset_index(drop=True), edges.reset_index(drop=True), processes.reset_index(
            drop=True
        )
    except Exception as exc:
        raise LineageBuildError(f"failed to build process lineage: {exc}") from exc


def build_run_dependency_edges(
    inputs: dict[str, object],
    process_inventory: pd.DataFrame,
    inventory_run_id: str,
) -> pd.DataFrame:
    """Build run-dependency edges from audit events and persisted run tables."""

    try:
        rows: list[dict[str, object]] = []
        audit_events = inputs.get("audit_events")
        if isinstance(audit_events, pd.DataFrame) and not audit_events.empty:
            for row in audit_events.to_dict("records"):
                run_id = row.get("run_id")
                component = (
                    row.get("component")
                    or row.get("pipeline_stage")
                    or row.get("event_type")
                )
                if not run_id or not component:
                    continue
                rows.append(
                    {
                        "inventory_run_id": inventory_run_id,
                        "source_id": _process_node_id(str(component)),
                        "target_id": _run_node_id(str(run_id)),
                        "relationship_type": "emitted_run",
                        "process_name": str(component),
                        "metadata": {
                            "event_type": row.get("event_type"),
                            "status": row.get("status"),
                        },
                    }
                )
        for source_key, id_column, process_name in (
            ("model_runs", "model_run_id", "anomaly_model"),
            ("supervised_model_runs", "run_id", "supervised_model"),
        ):
            model_runs = inputs.get("model_runs")
            frame = (
                cast("dict[str, pd.DataFrame]", model_runs).get(source_key, pd.DataFrame())
                if isinstance(model_runs, dict)
                else pd.DataFrame()
            )
            if id_column in frame.columns:
                for run_id in frame[id_column].dropna().astype(str).tolist():
                    rows.append(
                        {
                            "inventory_run_id": inventory_run_id,
                            "source_id": _process_node_id(process_name),
                            "target_id": _run_node_id(run_id),
                            "relationship_type": "produced_run",
                            "process_name": process_name,
                            "metadata": {"source_table": f"governance.{source_key}"},
                        }
                    )
        if not rows:
            return _empty(LINEAGE_EDGE_COLUMNS)
        return (
            pd.DataFrame(rows, columns=LINEAGE_EDGE_COLUMNS)
            .drop_duplicates(["source_id", "target_id", "relationship_type"])
            .sort_values(["process_name", "source_id", "target_id"])
            .reset_index(drop=True)
        )
    except Exception as exc:
        raise LineageBuildError(f"failed to build run dependency edges: {exc}") from exc


def build_governance_lineage(
    inputs: dict[str, object],
    config: GovernanceInventoryConfig | None = None,
    inventory_run_id: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build full governance lineage nodes, edges, and process inventory."""

    resolved = config or GovernanceInventoryConfig()
    run_id = inventory_run_id or build_inventory_run_id(resolved)
    try:
        node_frames: list[pd.DataFrame] = []
        edge_frames: list[pd.DataFrame] = []
        process_inventory = _empty(PROCESS_INVENTORY_COLUMNS)
        if resolved.lineage.include_table_lineage:
            table_counts = inputs.get("table_counts", pd.DataFrame())
            if isinstance(table_counts, pd.DataFrame):
                node_frames.append(build_table_lineage_nodes(table_counts, run_id))
        if resolved.lineage.include_process_lineage:
            process_nodes, process_edges, process_inventory = build_process_lineage(
                resolved,
                run_id,
            )
            audit_events = inputs.get("audit_events")
            if isinstance(audit_events, pd.DataFrame) and not process_inventory.empty:
                records = process_inventory.to_dict("records")
                for row in records:
                    timestamp, status = _latest_audit(audit_events, str(row["process_name"]))
                    row["latest_audit_timestamp"] = timestamp
                    row["latest_status"] = status
                process_inventory = pd.DataFrame(records, columns=PROCESS_INVENTORY_COLUMNS)
            node_frames.append(process_nodes)
            edge_frames.append(process_edges)
        if resolved.lineage.include_run_dependencies:
            run_edges = build_run_dependency_edges(inputs, process_inventory, run_id)
            edge_frames.append(run_edges)
            if not run_edges.empty:
                node_frames.append(
                    pd.DataFrame(
                        [
                            {
                                "inventory_run_id": run_id,
                                "node_id": target_id,
                                "node_type": "run",
                                "name": str(target_id).replace("run:", "", 1),
                                "schema_name": "governance",
                                "version": None,
                                "row_count": None,
                                "metadata": {"derived_from": "run_dependencies"},
                            }
                            for target_id in sorted(run_edges["target_id"].dropna().unique())
                        ],
                        columns=LINEAGE_NODE_COLUMNS,
                    )
                )
        nodes = (
            pd.concat([frame for frame in node_frames if not frame.empty], ignore_index=True)
            if any(not frame.empty for frame in node_frames)
            else _empty(LINEAGE_NODE_COLUMNS)
        )
        edges = (
            pd.concat([frame for frame in edge_frames if not frame.empty], ignore_index=True)
            if any(not frame.empty for frame in edge_frames)
            else _empty(LINEAGE_EDGE_COLUMNS)
        )
        if not nodes.empty:
            nodes = nodes.drop_duplicates("node_id").sort_values(["node_type", "name"])
        if not edges.empty:
            edges = edges.drop_duplicates(
                ["source_id", "target_id", "relationship_type"]
            ).sort_values(["relationship_type", "process_name", "source_id", "target_id"])
        return nodes.reset_index(drop=True), edges.reset_index(drop=True), process_inventory
    except LineageBuildError:
        raise
    except Exception as exc:
        raise LineageBuildError(f"failed to build governance lineage: {exc}") from exc
