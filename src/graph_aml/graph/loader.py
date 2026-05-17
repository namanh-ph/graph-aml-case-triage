"""Neo4j graph loading utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, cast

import pandas as pd
from neo4j import Driver
from sqlalchemy import Engine

from graph_aml.graph.constraints import ensure_graph_constraints
from graph_aml.graph.exceptions import GraphLoadError, GraphMappingError, GraphSchemaError
from graph_aml.graph.execution import run_cypher_batch
from graph_aml.graph.mapping import build_all_graph_nodes, build_all_graph_relationships
from graph_aml.graph.schema import GRAPH_NODE_KEY_PROPERTIES, validate_graph_schema
from graph_aml.graph.staging import read_graph_inputs

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class GraphLoadResult:
    """Summary of an attempted Neo4j graph load."""

    nodes_loaded: dict[str, int] = field(default_factory=dict)
    relationships_loaded: dict[str, int] = field(default_factory=dict)
    constraints_attempted: int = 0
    database: str | None = None
    summary: dict[str, object] = field(default_factory=dict)


def _validate_identifier(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_PATTERN.fullmatch(value):
        raise GraphLoadError(f"{field_name} must be a safe Cypher identifier")


def _validate_batch_size(batch_size: int) -> int:
    if not isinstance(batch_size, int) or batch_size <= 0:
        raise GraphLoadError("batch_size must be a positive integer")
    return int(batch_size)


def build_node_merge_cypher(label: str, key_property: str) -> str:
    """Build deterministic node MERGE Cypher."""

    _validate_identifier(label, field_name="label")
    _validate_identifier(key_property, field_name="key_property")
    return (
        f"UNWIND $rows AS row\n"
        f"MERGE (n:{label} {{{key_property}: row.{key_property}}})\n"
        "SET n += row"
    )


def load_graph_nodes(
    driver: Driver,
    label: str,
    key_property: str,
    rows: list[dict[str, object]],
    batch_size: int = 1000,
    database: str | None = None,
) -> int:
    """Load node rows with Neo4j MERGE."""

    _validate_batch_size(batch_size)
    if not rows:
        return 0
    try:
        query = build_node_merge_cypher(label, key_property)
        return run_cypher_batch(driver, query, rows, batch_size=batch_size, database=database)
    except GraphLoadError:
        raise
    except Exception as exc:
        raise GraphLoadError(f"Failed to load {label} nodes: {exc}") from exc


def build_relationship_merge_cypher(
    source_label: str,
    source_key: str,
    relationship_type: str,
    target_label: str,
    target_key: str,
    source_row_key: str,
    target_row_key: str,
) -> str:
    """Build deterministic relationship MERGE Cypher."""

    for value, field_name in (
        (source_label, "source_label"),
        (source_key, "source_key"),
        (relationship_type, "relationship_type"),
        (target_label, "target_label"),
        (target_key, "target_key"),
        (source_row_key, "source_row_key"),
        (target_row_key, "target_row_key"),
    ):
        _validate_identifier(value, field_name=field_name)
    return (
        f"UNWIND $rows AS row\n"
        f"MATCH (source:{source_label} {{{source_key}: row.{source_row_key}}})\n"
        f"MATCH (target:{target_label} {{{target_key}: row.{target_row_key}}})\n"
        f"MERGE (source)-[r:{relationship_type}]->(target)\n"
        "SET r += row"
    )


def load_graph_relationships(
    driver: Driver,
    relationship_type: str,
    source_label: str,
    source_key: str,
    target_label: str,
    target_key: str,
    source_row_key: str,
    target_row_key: str,
    rows: list[dict[str, object]],
    batch_size: int = 1000,
    database: str | None = None,
) -> int:
    """Load relationship rows with Neo4j MERGE."""

    _validate_batch_size(batch_size)
    if not rows:
        return 0
    try:
        query = build_relationship_merge_cypher(
            source_label,
            source_key,
            relationship_type,
            target_label,
            target_key,
            source_row_key,
            target_row_key,
        )
        return run_cypher_batch(driver, query, rows, batch_size=batch_size, database=database)
    except GraphLoadError:
        raise
    except Exception as exc:
        raise GraphLoadError(f"Failed to load {relationship_type} relationships: {exc}") from exc


def _relationship_load_specs() -> dict[str, tuple[str, str, str, str, str, str]]:
    return {
        "OWNS": ("Customer", "customer_id", "Account", "account_id", "customer_id", "account_id"),
        "SENT": (
            "Account",
            "account_id",
            "Transaction",
            "transaction_id",
            "account_id",
            "transaction_id",
        ),
        "RECEIVED": (
            "Transaction",
            "transaction_id",
            "Account",
            "account_id",
            "transaction_id",
            "account_id",
        ),
        "PAID_TO": (
            "Transaction",
            "transaction_id",
            "Counterparty",
            "counterparty_id",
            "transaction_id",
            "counterparty_id",
        ),
        "TRIGGERS": (
            "Transaction",
            "transaction_id",
            "Alert",
            "alert_id",
            "transaction_id",
            "alert_id",
        ),
        "FLAGS_ACCOUNT": ("Alert", "alert_id", "Account", "account_id", "alert_id", "account_id"),
        "INVOLVES_TRANSACTION": (
            "Alert",
            "alert_id",
            "Transaction",
            "transaction_id",
            "alert_id",
            "transaction_id",
        ),
    }


def _load_located_in_relationships(
    driver: Driver,
    rows: list[dict[str, object]],
    *,
    batch_size: int,
    database: str | None,
) -> int:
    total = 0
    for source_label, source_key in sorted(GRAPH_NODE_KEY_PROPERTIES.items()):
        if source_label == "Country":
            continue
        label_rows = [row for row in rows if row.get("source_label") == source_label]
        total += load_graph_relationships(
            driver,
            "LOCATED_IN",
            source_label,
            source_key,
            "Country",
            "country_code",
            "source_id",
            "country_code",
            label_rows,
            batch_size=batch_size,
            database=database,
        )
    return total


def _build_summary(
    nodes_loaded: dict[str, int],
    relationships_loaded: dict[str, int],
    constraints_attempted: int,
    database: str | None,
) -> dict[str, object]:
    return {
        "nodes_loaded": dict(nodes_loaded),
        "relationships_loaded": dict(relationships_loaded),
        "total_nodes_loaded": int(sum(nodes_loaded.values())),
        "total_relationships_loaded": int(sum(relationships_loaded.values())),
        "constraints_attempted": int(constraints_attempted),
        "database": database,
    }


def load_graph_from_inputs(
    driver: Driver,
    inputs: dict[str, pd.DataFrame],
    database: str | None = None,
    batch_size: int = 1000,
    ensure_constraints_first: bool = True,
) -> GraphLoadResult:
    """Load prepared graph inputs into Neo4j."""

    try:
        _validate_batch_size(batch_size)
        validate_graph_schema()
        constraints_attempted = 0
        if ensure_constraints_first:
            constraint_summary = ensure_graph_constraints(driver, database=database)
            constraints_attempted = int(cast(Any, constraint_summary["constraints_attempted"]))

        node_rows = build_all_graph_nodes(inputs)
        relationship_rows = build_all_graph_relationships(inputs)
        nodes_loaded: dict[str, int] = {}
        for label in ("Customer", "Country", "Account", "Counterparty", "Transaction", "Alert"):
            nodes_loaded[label] = load_graph_nodes(
                driver,
                label,
                GRAPH_NODE_KEY_PROPERTIES[label],
                node_rows.get(label, []),
                batch_size=batch_size,
                database=database,
            )

        relationships_loaded: dict[str, int] = {}
        specs = _relationship_load_specs()
        for relationship_type in (
            "OWNS",
            "SENT",
            "RECEIVED",
            "PAID_TO",
            "LOCATED_IN",
            "TRIGGERS",
            "FLAGS_ACCOUNT",
            "INVOLVES_TRANSACTION",
        ):
            rows = relationship_rows.get(relationship_type, [])
            if relationship_type == "LOCATED_IN":
                relationships_loaded[relationship_type] = _load_located_in_relationships(
                    driver,
                    rows,
                    batch_size=batch_size,
                    database=database,
                )
                continue
            spec = specs[relationship_type]
            relationships_loaded[relationship_type] = load_graph_relationships(
                driver,
                relationship_type,
                *spec,
                rows,
                batch_size=batch_size,
                database=database,
            )

        summary = _build_summary(
            nodes_loaded, relationships_loaded, constraints_attempted, database
        )
        return GraphLoadResult(
            nodes_loaded=nodes_loaded,
            relationships_loaded=relationships_loaded,
            constraints_attempted=constraints_attempted,
            database=database,
            summary=summary,
        )
    except (GraphLoadError, GraphMappingError, GraphSchemaError):
        raise
    except Exception as exc:
        raise GraphLoadError(f"Failed to load graph from inputs: {exc}") from exc


def load_graph_from_staged(
    postgres_engine: Engine,
    neo4j_driver: Driver,
    limit: int | None = None,
    include_alerts: bool = True,
    database: str | None = None,
    batch_size: int = 1000,
    ensure_constraints_first: bool = True,
) -> GraphLoadResult:
    """Read staged PostgreSQL inputs and load them into Neo4j."""

    try:
        inputs = read_graph_inputs(
            postgres_engine,
            limit=limit,
            include_alerts=include_alerts,
        )
        return load_graph_from_inputs(
            neo4j_driver,
            inputs,
            database=database,
            batch_size=batch_size,
            ensure_constraints_first=ensure_constraints_first,
        )
    except GraphLoadError:
        raise
    except Exception as exc:
        raise GraphLoadError(f"Failed to load graph from staged inputs: {exc}") from exc
