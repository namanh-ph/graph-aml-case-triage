"""Optional Neo4j graph readers for dashboard graph exploration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.graph_data import GRAPH_VIEW_EDGE_COLUMNS, GRAPH_VIEW_NODE_COLUMNS
from graph_aml.graph.execution import run_cypher_read


def read_neo4j_graph_neighbourhood(
    driver: Any,
    account_id: str,
    max_hops: int = 2,
    include_transactions: bool = True,
    include_alerts: bool = True,
    include_cases: bool = True,
    include_counterparties: bool = True,
    database: str | None = None,
) -> dict[str, list[dict[str, object]]]:
    """Read a bounded Neo4j neighbourhood using an externally supplied driver."""

    if not str(account_id).strip():
        raise DashboardDataError("account_id must be non-empty")
    if max_hops <= 0:
        raise DashboardDataError("max_hops must be positive")
    depth = min(int(max_hops), 5)
    labels = ["Account"]
    if include_transactions:
        labels.append("Transaction")
    if include_alerts:
        labels.append("Alert")
    if include_cases:
        labels.append("Case")
    if include_counterparties:
        labels.append("Counterparty")
    query = f"""
        MATCH path = (seed {{account_id: $account_id}})-[*1..{depth}]-(node)
        WHERE any(label IN labels(node) WHERE label IN $labels)
        WITH collect(DISTINCT node) AS nodes,
             collect(DISTINCT relationships(path)) AS relationship_groups
        UNWIND relationship_groups AS rels
        UNWIND rels AS rel
        RETURN
            [n IN nodes | properties(n) + {{labels: labels(n), element_id: elementId(n)}}] AS nodes,
            collect(DISTINCT properties(rel) + {{
                type: type(rel),
                source_id: elementId(startNode(rel)),
                target_id: elementId(endNode(rel))
            }}) AS relationships
    """
    try:
        rows = run_cypher_read(
            driver,
            query,
            {"account_id": account_id, "labels": labels},
            database=database,
        )
        if not rows:
            return {"nodes": [], "relationships": []}
        nodes = rows[0].get("nodes") or []
        relationships = rows[0].get("relationships") or []
        if not isinstance(nodes, Iterable) or isinstance(nodes, str | bytes):
            nodes = []
        if not isinstance(relationships, Iterable) or isinstance(relationships, str | bytes):
            relationships = []
        return {"nodes": list(nodes), "relationships": list(relationships)}
    except Exception as exc:
        raise DashboardDataError(f"Failed to read Neo4j dashboard graph: {exc}") from exc


def neo4j_graph_records_to_frames(
    payload: dict[str, list[dict[str, object]]],
) -> dict[str, pd.DataFrame]:
    """Convert Neo4j graph records into dashboard-compatible frames."""

    try:
        nodes = []
        for row in payload.get("nodes", []):
            labels = row.get("labels") or []
            node_type = str(labels[0]).lower() if isinstance(labels, list) and labels else "node"
            node_id = row.get("account_id") or row.get("id") or row.get("element_id")
            nodes.append(
                {
                    "node_id": node_id,
                    "node_type": node_type,
                    "label": node_id,
                    "risk_score": row.get("risk_score") or row.get("account_risk_score"),
                    "risk_band": row.get("risk_band"),
                    "community_id": row.get("community_id"),
                    "metadata": row,
                }
            )
        edges = []
        for row in payload.get("relationships", []):
            edges.append(
                {
                    "source_id": row.get("source_id"),
                    "target_id": row.get("target_id"),
                    "edge_type": row.get("type", "relationship"),
                    "weight": row.get("weight", 1.0),
                    "transaction_id": row.get("transaction_id"),
                    "amount": row.get("amount"),
                    "metadata": row,
                }
            )
        return {
            "nodes": pd.DataFrame(nodes, columns=GRAPH_VIEW_NODE_COLUMNS),
            "edges": pd.DataFrame(edges, columns=GRAPH_VIEW_EDGE_COLUMNS),
        }
    except Exception as exc:
        raise DashboardDataError(f"Failed to parse Neo4j dashboard graph records: {exc}") from exc
