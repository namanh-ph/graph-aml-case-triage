"""Neo4j graph load reconciliation helpers."""

from __future__ import annotations

import re
from typing import Any, cast

from neo4j import Driver

from graph_aml.graph.exceptions import GraphReconciliationError
from graph_aml.graph.execution import run_cypher_scalar
from graph_aml.graph.loader import GraphLoadResult
from graph_aml.graph.schema import GRAPH_NODE_LABELS, GRAPH_RELATIONSHIP_TYPES

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _validate_identifier(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_PATTERN.fullmatch(value):
        raise GraphReconciliationError(f"{field_name} must be a safe Cypher identifier")


def count_graph_nodes(driver: Driver, label: str, database: str | None = None) -> int:
    """Count Neo4j nodes for a validated label."""

    _validate_identifier(label, field_name="label")
    if label not in GRAPH_NODE_LABELS:
        raise GraphReconciliationError(f"Unknown graph node label: {label}")
    try:
        value = run_cypher_scalar(driver, f"MATCH (n:{label}) RETURN count(n)", database=database)
        return int(cast(Any, value or 0))
    except GraphReconciliationError:
        raise
    except Exception as exc:
        raise GraphReconciliationError(f"Failed to count {label} nodes: {exc}") from exc


def count_graph_relationships(
    driver: Driver,
    relationship_type: str,
    database: str | None = None,
) -> int:
    """Count Neo4j relationships for a validated type."""

    _validate_identifier(relationship_type, field_name="relationship_type")
    if relationship_type not in GRAPH_RELATIONSHIP_TYPES:
        raise GraphReconciliationError(f"Unknown graph relationship type: {relationship_type}")
    try:
        value = run_cypher_scalar(
            driver,
            f"MATCH ()-[r:{relationship_type}]->() RETURN count(r)",
            database=database,
        )
        return int(cast(Any, value or 0))
    except GraphReconciliationError:
        raise
    except Exception as exc:
        raise GraphReconciliationError(
            f"Failed to count {relationship_type} relationships: {exc}"
        ) from exc


def collect_graph_counts(driver: Driver, database: str | None = None) -> dict[str, object]:
    """Collect graph node and relationship counts."""

    try:
        return {
            "nodes": {
                label: count_graph_nodes(driver, label, database=database)
                for label in GRAPH_NODE_LABELS
            },
            "relationships": {
                relationship_type: count_graph_relationships(
                    driver, relationship_type, database=database
                )
                for relationship_type in GRAPH_RELATIONSHIP_TYPES
            },
            "database": database,
        }
    except GraphReconciliationError:
        raise
    except Exception as exc:
        raise GraphReconciliationError(f"Failed to collect graph counts: {exc}") from exc


def reconcile_graph_load(
    load_result: GraphLoadResult,
    graph_counts: dict[str, object],
) -> dict[str, object]:
    """Compare load attempts with current graph counts."""

    if not isinstance(load_result, GraphLoadResult):
        raise GraphReconciliationError("load_result must be a GraphLoadResult")
    if not isinstance(graph_counts, dict):
        raise GraphReconciliationError("graph_counts must be a dictionary")
    node_counts = graph_counts.get("nodes", {})
    relationship_counts = graph_counts.get("relationships", {})
    if not isinstance(node_counts, dict) or not isinstance(relationship_counts, dict):
        raise GraphReconciliationError("graph_counts must include node and relationship maps")

    warnings: list[str] = []
    for label, attempted in load_result.nodes_loaded.items():
        if int(node_counts.get(label, 0)) < int(attempted):
            actual = node_counts.get(label, 0)
            warnings.append(f"{label} graph count {actual} is below attempted load {attempted}")
    for relationship_type, attempted in load_result.relationships_loaded.items():
        if int(relationship_counts.get(relationship_type, 0)) < int(attempted):
            warnings.append(
                f"{relationship_type} graph count {relationship_counts.get(relationship_type, 0)} "
                f"is below attempted load {attempted}"
            )
    return {
        "status": "warning" if warnings else "ok",
        "nodes_loaded": dict(load_result.nodes_loaded),
        "relationships_loaded": dict(load_result.relationships_loaded),
        "graph_node_counts": dict(node_counts),
        "graph_relationship_counts": dict(relationship_counts),
        "warnings": warnings,
    }
