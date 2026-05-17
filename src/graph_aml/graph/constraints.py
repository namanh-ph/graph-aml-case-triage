"""Neo4j node uniqueness constraint helpers."""

from __future__ import annotations

import re

from neo4j import Driver

from graph_aml.graph.exceptions import GraphConstraintError
from graph_aml.graph.execution import run_cypher_read, run_cypher_write

GRAPH_NODE_CONSTRAINTS = (
    ("Customer", "customer_id"),
    ("Account", "account_id"),
    ("Transaction", "transaction_id"),
    ("Counterparty", "counterparty_id"),
    ("Device", "device_id"),
    ("Country", "country_code"),
    ("Alert", "alert_id"),
    ("Case", "case_id"),
)

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def build_unique_constraint_cypher(label: str, property_name: str) -> str:
    """Build a Neo4j 5 unique node-property constraint statement."""

    _validate_identifier(label, "label")
    _validate_identifier(property_name, "property")
    constraint_name = _constraint_name(label, property_name)
    return (
        f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
        f"FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE"
    )


def ensure_graph_constraints(
    driver: Driver,
    constraints: tuple[tuple[str, str], ...] = GRAPH_NODE_CONSTRAINTS,
    database: str | None = None,
) -> dict[str, object]:
    """Ensure configured graph node uniqueness constraints exist."""

    try:
        names: list[str] = []
        for label, property_name in constraints:
            query = build_unique_constraint_cypher(label, property_name)
            run_cypher_write(driver, query, database=database)
            names.append(_constraint_name(label, property_name))
        return {
            "constraints_attempted": len(constraints),
            "constraint_names": names,
        }
    except GraphConstraintError:
        raise
    except Exception as exc:
        raise GraphConstraintError(f"Could not ensure graph constraints: {exc}") from exc


def list_graph_constraints(
    driver: Driver,
    database: str | None = None,
) -> list[dict[str, object]]:
    """List Neo4j schema constraints."""

    try:
        return run_cypher_read(driver, "SHOW CONSTRAINTS", database=database)
    except Exception as exc:
        raise GraphConstraintError(f"Could not list graph constraints: {exc}") from exc


def _constraint_name(label: str, property_name: str) -> str:
    return f"constraint_{label.lower()}_{property_name.lower()}_unique"


def _validate_identifier(value: str, kind: str) -> None:
    if not _IDENTIFIER_PATTERN.match(value):
        raise GraphConstraintError(f"Invalid Neo4j {kind} identifier: {value}")
