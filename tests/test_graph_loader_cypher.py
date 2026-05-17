"""Tests for graph loader Cypher templates."""

import pytest

from graph_aml.graph import (
    GraphLoadError,
    build_node_merge_cypher,
    build_relationship_merge_cypher,
)


def test_node_merge_cypher_uses_unwind_merge_and_set() -> None:
    cypher = build_node_merge_cypher("Account", "account_id")

    assert "UNWIND $rows AS row" in cypher
    assert "MERGE (n:Account {account_id: row.account_id})" in cypher
    assert "SET n += row" in cypher


def test_relationship_merge_cypher_uses_match_merge_and_set() -> None:
    cypher = build_relationship_merge_cypher(
        "Account",
        "account_id",
        "SENT",
        "Transaction",
        "transaction_id",
        "account_id",
        "transaction_id",
    )

    assert "MATCH (source:Account {account_id: row.account_id})" in cypher
    assert "MATCH (target:Transaction {transaction_id: row.transaction_id})" in cypher
    assert "MERGE (source)-[r:SENT]->(target)" in cypher
    assert "SET r += row" in cypher


@pytest.mark.parametrize(
    "args",
    (
        ("Bad Label", "account_id"),
        ("Account", "account-id"),
    ),
)
def test_invalid_node_identifiers_raise_graph_load_error(args: tuple[str, str]) -> None:
    with pytest.raises(GraphLoadError):
        build_node_merge_cypher(*args)


def test_invalid_relationship_identifiers_raise_graph_load_error() -> None:
    with pytest.raises(GraphLoadError):
        build_relationship_merge_cypher(
            "Account",
            "account_id",
            "BAD-TYPE",
            "Transaction",
            "transaction_id",
            "account_id",
            "transaction_id",
        )


def test_cypher_template_generation_is_deterministic() -> None:
    assert build_node_merge_cypher("Alert", "alert_id") == build_node_merge_cypher(
        "Alert", "alert_id"
    )
