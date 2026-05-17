"""Readback utilities for persisted governance inventory outputs."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from sqlalchemy import Engine, text

from graph_aml.governance.exceptions import GovernanceInventoryPersistenceError


def _validate_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    if isinstance(limit, bool) or int(limit) < 0:
        raise GovernanceInventoryPersistenceError("limit must be non-negative")
    return int(limit)


def _read(engine: Engine, sql: str, params: dict[str, object]) -> pd.DataFrame:
    return pd.read_sql_query(
        text(sql),
        engine,
        params=cast("dict[str, Any] | None", params or None),
    )


def _select(
    table: str,
    clauses: list[str],
    params: dict[str, object],
    order_by: str,
    limit: int | None,
) -> str:
    sql = f"SELECT * FROM {table}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += f" ORDER BY {order_by}"
    safe_limit = _validate_limit(limit)
    if safe_limit is not None:
        sql += " LIMIT :limit"
        params["limit"] = safe_limit
    return sql


def read_inventory_runs(
    engine: Engine,
    inventory_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    clauses: list[str] = []
    if inventory_version:
        clauses.append("inventory_version = :inventory_version")
        params["inventory_version"] = inventory_version
    sql = _select(
        "governance.inventory_runs",
        clauses,
        params,
        "created_at DESC NULLS LAST, inventory_run_id",
        limit,
    )
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(f"failed to read inventory runs: {exc}") from exc


def read_lineage_nodes(
    engine: Engine,
    inventory_run_id: str | None = None,
    node_type: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    clauses: list[str] = []
    if inventory_run_id:
        clauses.append("inventory_run_id = :inventory_run_id")
        params["inventory_run_id"] = inventory_run_id
    if node_type:
        clauses.append("node_type = :node_type")
        params["node_type"] = node_type
    sql = _select("governance.lineage_nodes", clauses, params, "node_type, name", limit)
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(f"failed to read lineage nodes: {exc}") from exc


def read_lineage_edges(
    engine: Engine,
    inventory_run_id: str | None = None,
    process_name: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    clauses: list[str] = []
    if inventory_run_id:
        clauses.append("inventory_run_id = :inventory_run_id")
        params["inventory_run_id"] = inventory_run_id
    if process_name:
        clauses.append("process_name = :process_name")
        params["process_name"] = process_name
    sql = _select(
        "governance.lineage_edges",
        clauses,
        params,
        "process_name NULLS LAST, relationship_type, source_id, target_id",
        limit,
    )
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(f"failed to read lineage edges: {exc}") from exc


def read_artefact_registry(
    engine: Engine,
    inventory_run_id: str | None = None,
    artefact_type: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    clauses: list[str] = []
    if inventory_run_id:
        clauses.append("inventory_run_id = :inventory_run_id")
        params["inventory_run_id"] = inventory_run_id
    if artefact_type:
        clauses.append("artefact_type = :artefact_type")
        params["artefact_type"] = artefact_type
    sql = _select(
        "governance.artefact_registry",
        clauses,
        params,
        "artefact_type, source_dir, relative_path",
        limit,
    )
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(
            f"failed to read artefact registry: {exc}"
        ) from exc


def read_process_inventory(
    engine: Engine,
    inventory_run_id: str | None = None,
    process_name: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    clauses: list[str] = []
    if inventory_run_id:
        clauses.append("inventory_run_id = :inventory_run_id")
        params["inventory_run_id"] = inventory_run_id
    if process_name:
        clauses.append("process_name = :process_name")
        params["process_name"] = process_name
    sql = _select("governance.process_inventory", clauses, params, "process_name", limit)
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(
            f"failed to read process inventory: {exc}"
        ) from exc


def read_model_inventory(
    engine: Engine,
    inventory_run_id: str | None = None,
    model_version: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    clauses: list[str] = []
    if inventory_run_id:
        clauses.append("inventory_run_id = :inventory_run_id")
        params["inventory_run_id"] = inventory_run_id
    if model_version:
        clauses.append("model_version = :model_version")
        params["model_version"] = model_version
    sql = _select(
        "governance.model_inventory",
        clauses,
        params,
        "model_name, model_version NULLS LAST",
        limit,
    )
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(f"failed to read model inventory: {exc}") from exc


def read_validation_inventory(
    engine: Engine,
    inventory_run_id: str | None = None,
    validation_type: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    params: dict[str, object] = {}
    clauses: list[str] = []
    if inventory_run_id:
        clauses.append("inventory_run_id = :inventory_run_id")
        params["inventory_run_id"] = inventory_run_id
    if validation_type:
        clauses.append("validation_type = :validation_type")
        params["validation_type"] = validation_type
    sql = _select(
        "governance.validation_inventory",
        clauses,
        params,
        "validation_type, validation_version NULLS LAST",
        limit,
    )
    try:
        return _read(engine, sql, params)
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(
            f"failed to read validation inventory: {exc}"
        ) from exc


def read_governance_inventory_summary(engine: Engine) -> dict[str, object]:
    """Read compact governance inventory summary."""

    try:
        runs = _read(
            engine,
            """
            SELECT COUNT(*) AS inventory_run_count, MAX(created_at) AS latest_created_at
            FROM governance.inventory_runs
            """,
            {},
        )
        latest = _read(
            engine,
            """
            SELECT inventory_version, inventory_run_id
            FROM governance.inventory_runs
            ORDER BY created_at DESC NULLS LAST, inventory_run_id
            LIMIT 1
            """,
            {},
        )
        counts: dict[str, int] = {}
        for key, table in {
            "lineage_node_count": "governance.lineage_nodes",
            "lineage_edge_count": "governance.lineage_edges",
            "artefact_count": "governance.artefact_registry",
            "process_count": "governance.process_inventory",
            "model_inventory_count": "governance.model_inventory",
            "validation_inventory_count": "governance.validation_inventory",
        }.items():
            frame = _read(engine, f"SELECT COUNT(*) AS row_count FROM {table}", {})
            counts[key] = int(frame.iloc[0]["row_count"]) if not frame.empty else 0
        inventory_run_count = (
            int(runs.iloc[0]["inventory_run_count"]) if not runs.empty else 0
        )
        latest_inventory_version = (
            latest.iloc[0]["inventory_version"] if not latest.empty else None
        )
        latest_inventory_run_id = (
            latest.iloc[0]["inventory_run_id"] if not latest.empty else None
        )
        return {
            "inventory_run_count": inventory_run_count,
            "latest_inventory_version": latest_inventory_version,
            "latest_inventory_run_id": latest_inventory_run_id,
            **counts,
        }
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(
            f"failed to read governance inventory summary: {exc}"
        ) from exc
