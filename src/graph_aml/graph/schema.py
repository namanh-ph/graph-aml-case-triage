"""Neo4j graph schema metadata for AML entity loading."""

from __future__ import annotations

import re
from dataclasses import dataclass

from graph_aml.graph.exceptions import GraphSchemaError

GRAPH_NODE_LABELS = (
    "Customer",
    "Account",
    "Transaction",
    "Counterparty",
    "Country",
    "Alert",
)

GRAPH_RELATIONSHIP_TYPES = (
    "OWNS",
    "SENT",
    "RECEIVED",
    "PAID_TO",
    "LOCATED_IN",
    "TRIGGERS",
    "FLAGS_ACCOUNT",
    "INVOLVES_TRANSACTION",
)

GRAPH_NODE_KEY_PROPERTIES = {
    "Customer": "customer_id",
    "Account": "account_id",
    "Transaction": "transaction_id",
    "Counterparty": "counterparty_id",
    "Country": "country_code",
    "Alert": "alert_id",
}

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class GraphNodeSpec:
    """Definition for a graph node label and its key properties."""

    label: str
    key_property: str
    required_properties: tuple[str, ...]
    optional_properties: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphRelationshipSpec:
    """Definition for a directed graph relationship type."""

    relationship_type: str
    source_label: str
    source_key: str
    target_label: str
    target_key: str
    required_properties: tuple[str, ...] = ()
    optional_properties: tuple[str, ...] = ()


def _validate_identifier(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_PATTERN.fullmatch(value):
        raise GraphSchemaError(f"{field_name} must be a safe Cypher identifier")


def get_graph_node_specs() -> dict[str, GraphNodeSpec]:
    """Return graph node specs keyed by label."""

    return {
        "Customer": GraphNodeSpec(
            label="Customer",
            key_property="customer_id",
            required_properties=("customer_id",),
            optional_properties=(
                "customer_type",
                "segment",
                "jurisdiction",
                "occupation",
                "risk_rating",
            ),
        ),
        "Account": GraphNodeSpec(
            label="Account",
            key_property="account_id",
            required_properties=("account_id", "customer_id"),
            optional_properties=("account_type", "opened_at", "status", "currency", "country_code"),
        ),
        "Transaction": GraphNodeSpec(
            label="Transaction",
            key_property="transaction_id",
            required_properties=("transaction_id",),
            optional_properties=(
                "transaction_timestamp",
                "amount",
                "currency",
                "transaction_type",
                "channel",
                "country_code",
            ),
        ),
        "Counterparty": GraphNodeSpec(
            label="Counterparty",
            key_property="counterparty_id",
            required_properties=("counterparty_id",),
            optional_properties=("counterparty_type", "name", "country_code", "risk_rating"),
        ),
        "Country": GraphNodeSpec(
            label="Country",
            key_property="country_code",
            required_properties=("country_code",),
            optional_properties=("country_name", "high_risk_flag", "region"),
        ),
        "Alert": GraphNodeSpec(
            label="Alert",
            key_property="alert_id",
            required_properties=("alert_id",),
            optional_properties=(
                "rule_name",
                "typology",
                "severity",
                "risk_score_rule",
                "reason_code",
                "evidence_ids",
                "created_at",
            ),
        ),
    }


def get_graph_relationship_specs() -> dict[str, GraphRelationshipSpec]:
    """Return graph relationship specs keyed by relationship type."""

    return {
        "OWNS": GraphRelationshipSpec("OWNS", "Customer", "customer_id", "Account", "account_id"),
        "SENT": GraphRelationshipSpec(
            "SENT", "Account", "account_id", "Transaction", "transaction_id"
        ),
        "RECEIVED": GraphRelationshipSpec(
            "RECEIVED", "Transaction", "transaction_id", "Account", "account_id"
        ),
        "PAID_TO": GraphRelationshipSpec(
            "PAID_TO", "Transaction", "transaction_id", "Counterparty", "counterparty_id"
        ),
        "LOCATED_IN": GraphRelationshipSpec(
            "LOCATED_IN", "Customer", "customer_id", "Country", "country_code"
        ),
        "TRIGGERS": GraphRelationshipSpec(
            "TRIGGERS", "Transaction", "transaction_id", "Alert", "alert_id"
        ),
        "FLAGS_ACCOUNT": GraphRelationshipSpec(
            "FLAGS_ACCOUNT", "Alert", "alert_id", "Account", "account_id"
        ),
        "INVOLVES_TRANSACTION": GraphRelationshipSpec(
            "INVOLVES_TRANSACTION", "Alert", "alert_id", "Transaction", "transaction_id"
        ),
    }


def validate_graph_node_spec(spec: GraphNodeSpec) -> None:
    """Validate node schema metadata."""

    _validate_identifier(spec.label, field_name="label")
    _validate_identifier(spec.key_property, field_name="key_property")
    if spec.label not in GRAPH_NODE_LABELS:
        raise GraphSchemaError(f"Unknown graph node label: {spec.label}")
    if GRAPH_NODE_KEY_PROPERTIES.get(spec.label) != spec.key_property:
        raise GraphSchemaError(f"Unexpected key property for label {spec.label}")
    if spec.key_property not in spec.required_properties:
        raise GraphSchemaError("key_property must be listed as a required property")
    for prop in (*spec.required_properties, *spec.optional_properties):
        _validate_identifier(prop, field_name="property")


def validate_graph_relationship_spec(spec: GraphRelationshipSpec) -> None:
    """Validate relationship schema metadata."""

    _validate_identifier(spec.relationship_type, field_name="relationship_type")
    if spec.relationship_type not in GRAPH_RELATIONSHIP_TYPES:
        raise GraphSchemaError(f"Unknown graph relationship type: {spec.relationship_type}")
    for label in (spec.source_label, spec.target_label):
        _validate_identifier(label, field_name="label")
        if label not in GRAPH_NODE_LABELS:
            raise GraphSchemaError(f"Unknown graph node label: {label}")
    for prop in (
        spec.source_key,
        spec.target_key,
        *spec.required_properties,
        *spec.optional_properties,
    ):
        _validate_identifier(prop, field_name="property")


def validate_graph_schema() -> None:
    """Validate all graph schema metadata."""

    for node_spec in get_graph_node_specs().values():
        validate_graph_node_spec(node_spec)
    for relationship_spec in get_graph_relationship_specs().values():
        validate_graph_relationship_spec(relationship_spec)


def get_graph_schema_summary() -> dict[str, object]:
    """Return a JSON-serialisable graph schema summary."""

    validate_graph_schema()
    return {
        "node_labels": list(GRAPH_NODE_LABELS),
        "relationship_types": list(GRAPH_RELATIONSHIP_TYPES),
        "node_key_properties": dict(GRAPH_NODE_KEY_PROPERTIES),
        "node_count": len(GRAPH_NODE_LABELS),
        "relationship_type_count": len(GRAPH_RELATIONSHIP_TYPES),
    }
