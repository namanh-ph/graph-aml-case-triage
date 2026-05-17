"""Project Neo4j graph data into NetworkX graphs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
from neo4j import Driver

from graph_aml.graph.analytics_config import GraphAnalyticsConfig
from graph_aml.graph.exceptions import GraphProjectionError
from graph_aml.graph.execution import run_cypher_read

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_NODE_KEY_PROPERTIES = (
    "customer_id",
    "account_id",
    "transaction_id",
    "counterparty_id",
    "country_code",
    "alert_id",
)


@dataclass(frozen=True)
class ProjectedGraphData:
    """Plain Neo4j projection data for NetworkX analytics."""

    nodes: list[dict[str, object]] = field(default_factory=list)
    relationships: list[dict[str, object]] = field(default_factory=list)
    account_ids: tuple[str, ...] = ()
    alert_ids: tuple[str, ...] = ()
    transaction_ids: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


def _validate_identifier(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_PATTERN.fullmatch(value):
        raise GraphProjectionError(f"{field_name} must be a safe Cypher identifier")


def _labels_for_projection(
    include_counterparties: bool,
    include_alert_nodes: bool,
    include_transaction_nodes: bool,
) -> tuple[str, ...]:
    labels = ["Customer", "Account", "Country"]
    if include_transaction_nodes:
        labels.append("Transaction")
    if include_counterparties:
        labels.append("Counterparty")
    if include_alert_nodes:
        labels.append("Alert")
    return tuple(labels)


def _cypher_list(values: tuple[str, ...]) -> str:
    for value in values:
        _validate_identifier(value, field_name="identifier")
    return "[" + ", ".join(f"'{value}'" for value in values) + "]"


def build_graph_projection_node_query(
    include_counterparties: bool = True,
    include_alert_nodes: bool = True,
    include_transaction_nodes: bool = True,
) -> str:
    """Build a deterministic node projection query."""

    labels = _labels_for_projection(
        include_counterparties,
        include_alert_nodes,
        include_transaction_nodes,
    )
    label_list = _cypher_list(labels)
    return (
        "MATCH (n)\n"
        f"WHERE any(label IN labels(n) WHERE label IN {label_list})\n"
        "WITH n, coalesce(n.customer_id, n.account_id, n.transaction_id, "
        "n.counterparty_id, n.country_code, n.alert_id) AS node_id\n"
        "WHERE node_id IS NOT NULL\n"
        "RETURN {id: node_id, labels: labels(n), properties: properties(n)} AS node\n"
        "ORDER BY node_id"
    )


def build_graph_projection_relationship_query(
    relationship_types: tuple[str, ...],
) -> str:
    """Build a deterministic relationship projection query."""

    if not relationship_types:
        raise GraphProjectionError("relationship_types must be non-empty")
    type_list = _cypher_list(tuple(relationship_types))
    return (
        "MATCH (source)-[r]->(target)\n"
        f"WHERE type(r) IN {type_list}\n"
        "WITH source, target, r,\n"
        "  coalesce(source.customer_id, source.account_id, source.transaction_id, "
        "source.counterparty_id, source.country_code, source.alert_id) AS source_id,\n"
        "  coalesce(target.customer_id, target.account_id, target.transaction_id, "
        "target.counterparty_id, target.country_code, target.alert_id) AS target_id\n"
        "WHERE source_id IS NOT NULL AND target_id IS NOT NULL\n"
        "RETURN {source_id: source_id, target_id: target_id, type: type(r), "
        "properties: properties(r)} AS relationship\n"
        "ORDER BY source_id, target_id, type(r)"
    )


def _extract_payload(row: dict[str, object], key: str) -> dict[str, object]:
    payload = row.get(key, row)
    if not isinstance(payload, dict):
        raise GraphProjectionError(f"Projected {key} row must be a dictionary")
    return dict(payload)


def _normalise_node(row: dict[str, object]) -> dict[str, object]:
    node = _extract_payload(row, "node")
    node_id = str(node.get("id", "")).strip()
    if not node_id:
        raise GraphProjectionError("Projected node is missing id")
    labels = node.get("labels", [])
    properties = node.get("properties", {})
    if not isinstance(labels, list | tuple) or not isinstance(properties, dict):
        raise GraphProjectionError("Projected node labels/properties are malformed")
    return {
        "id": node_id,
        "labels": sorted(str(label) for label in labels),
        "properties": dict(properties),
    }


def _normalise_relationship(row: dict[str, object]) -> dict[str, object]:
    relationship = _extract_payload(row, "relationship")
    source_id = str(relationship.get("source_id", "")).strip()
    target_id = str(relationship.get("target_id", "")).strip()
    relationship_type = str(relationship.get("type", "")).strip()
    properties = relationship.get("properties", {})
    if not source_id or not target_id or not relationship_type:
        raise GraphProjectionError("Projected relationship is missing identity fields")
    if not isinstance(properties, dict):
        raise GraphProjectionError("Projected relationship properties are malformed")
    _validate_identifier(relationship_type, field_name="relationship_type")
    return {
        "source_id": source_id,
        "target_id": target_id,
        "type": relationship_type,
        "properties": dict(properties),
    }


def _node_type(labels: object) -> str:
    if isinstance(labels, list | tuple) and labels:
        preferred = ("Account", "Alert", "Transaction", "Counterparty", "Customer", "Country")
        label_set = {str(label) for label in labels}
        for label in preferred:
            if label in label_set:
                return label
        return str(sorted(label_set)[0])
    return "Unknown"


def read_projected_graph_data(
    driver: Driver,
    config: GraphAnalyticsConfig | None = None,
    database: str | None = None,
) -> ProjectedGraphData:
    """Read Neo4j graph data into a plain projection."""

    resolved_config = GraphAnalyticsConfig() if config is None else config
    try:
        node_rows = run_cypher_read(
            driver,
            build_graph_projection_node_query(
                include_counterparties=resolved_config.include_counterparties,
                include_alert_nodes=resolved_config.include_alert_nodes,
                include_transaction_nodes=resolved_config.include_transaction_nodes,
            ),
            database=database,
        )
        relationship_rows = run_cypher_read(
            driver,
            build_graph_projection_relationship_query(
                resolved_config.projection_relationship_types
            ),
            database=database,
        )
        nodes = sorted(
            (_normalise_node(row) for row in node_rows),
            key=lambda item: str(item["id"]),
        )
        relationships = sorted(
            (_normalise_relationship(row) for row in relationship_rows),
            key=lambda item: (str(item["source_id"]), str(item["target_id"]), str(item["type"])),
        )
        account_ids = tuple(
            str(node["id"]) for node in nodes if _node_type(node["labels"]) == "Account"
        )
        alert_ids = tuple(
            str(node["id"]) for node in nodes if _node_type(node["labels"]) == "Alert"
        )
        transaction_ids = tuple(
            str(node["id"]) for node in nodes if _node_type(node["labels"]) == "Transaction"
        )
        return ProjectedGraphData(
            nodes=nodes,
            relationships=relationships,
            account_ids=account_ids,
            alert_ids=alert_ids,
            transaction_ids=transaction_ids,
            metadata={
                "node_count": len(nodes),
                "relationship_count": len(relationships),
                "database": database,
            },
        )
    except GraphProjectionError:
        raise
    except Exception as exc:
        raise GraphProjectionError(f"Failed to read projected graph data: {exc}") from exc


def build_networkx_graph(
    projected: ProjectedGraphData,
    directed: bool = True,
) -> nx.DiGraph | nx.Graph:
    """Build a NetworkX graph from projected Neo4j rows."""

    if not isinstance(projected, ProjectedGraphData):
        raise GraphProjectionError("projected must be ProjectedGraphData")
    graph: nx.DiGraph | nx.Graph = nx.DiGraph() if directed else nx.Graph()
    try:
        for node in projected.nodes:
            node_id = str(node["id"])
            labels_value = node.get("labels", [])
            properties_value = node.get("properties", {})
            if not isinstance(labels_value, list | tuple) or not isinstance(properties_value, dict):
                raise GraphProjectionError("Projected node labels/properties are malformed")
            labels = list(labels_value)
            properties = dict(properties_value)
            graph.add_node(
                node_id,
                labels=labels,
                node_type=_node_type(labels),
                **properties,
            )
        for relationship in projected.relationships:
            properties_value = relationship.get("properties", {})
            if not isinstance(properties_value, dict):
                raise GraphProjectionError("Projected relationship properties are malformed")
            properties = dict(properties_value)
            graph.add_edge(
                str(relationship["source_id"]),
                str(relationship["target_id"]),
                relationship_type=str(relationship["type"]),
                **properties,
            )
    except Exception as exc:
        raise GraphProjectionError(f"Failed to build NetworkX graph: {exc}") from exc
    return graph


def _append_edge_transaction(
    graph: nx.DiGraph,
    source: str,
    target: str,
    *,
    transaction_id: str,
    amount: float,
    target_node_type: str,
) -> None:
    if graph.has_edge(source, target):
        edge = graph[source][target]
        transaction_ids = list(edge.get("transaction_ids", []))
        if transaction_id not in transaction_ids:
            transaction_ids.append(transaction_id)
        edge["transaction_ids"] = sorted(transaction_ids)
        edge["amount"] = float(edge.get("amount", 0.0)) + amount
        edge["target_node_type"] = target_node_type
        return
    graph.add_edge(
        source,
        target,
        transaction_id=transaction_id,
        transaction_ids=[transaction_id],
        amount=amount,
        target_node_type=target_node_type,
    )


def build_account_flow_graph(
    projected: ProjectedGraphData,
) -> nx.DiGraph:
    """Build an account-to-account/counterparty flow graph."""

    full_graph = build_networkx_graph(projected, directed=True)
    flow_graph = nx.DiGraph()
    for node_id, attrs in full_graph.nodes(data=True):
        if attrs.get("node_type") in {"Account", "Counterparty"}:
            flow_graph.add_node(node_id, **attrs)
    try:
        sent_by_transaction: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        received_by_transaction: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        paid_to_by_transaction: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for source, target, attrs in full_graph.edges(data=True):
            rel_type = attrs.get("relationship_type")
            if rel_type == "SENT":
                sent_by_transaction.setdefault(str(target), []).append((str(source), dict(attrs)))
            elif rel_type == "RECEIVED":
                received_by_transaction.setdefault(str(source), []).append(
                    (str(target), dict(attrs))
                )
            elif rel_type == "PAID_TO":
                paid_to_by_transaction.setdefault(str(source), []).append(
                    (str(target), dict(attrs))
                )

        for transaction_id, sources in sent_by_transaction.items():
            transaction_amount = full_graph.nodes.get(transaction_id, {}).get("amount", 0.0)
            for source, sent_attrs in sources:
                amount = float(sent_attrs.get("amount") or transaction_amount or 0.0)
                for target, _attrs in received_by_transaction.get(transaction_id, []):
                    _append_edge_transaction(
                        flow_graph,
                        source,
                        target,
                        transaction_id=transaction_id,
                        amount=amount,
                        target_node_type="Account",
                    )
                for target, _attrs in paid_to_by_transaction.get(transaction_id, []):
                    _append_edge_transaction(
                        flow_graph,
                        source,
                        target,
                        transaction_id=transaction_id,
                        amount=amount,
                        target_node_type="Counterparty",
                    )
    except Exception as exc:
        raise GraphProjectionError(f"Failed to build account flow graph: {exc}") from exc
    return flow_graph
