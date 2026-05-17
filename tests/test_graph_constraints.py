"""Tests for Neo4j graph constraint helpers."""

import pytest

import graph_aml.graph.constraints as constraints_module
from graph_aml.graph import (
    GRAPH_NODE_CONSTRAINTS,
    GraphConstraintError,
    build_unique_constraint_cypher,
    ensure_graph_constraints,
    list_graph_constraints,
)


class FakeDriver:
    pass


def test_graph_node_constraints_include_required_labels() -> None:
    labels = {label for label, _ in GRAPH_NODE_CONSTRAINTS}

    assert {
        "Customer",
        "Account",
        "Transaction",
        "Counterparty",
        "Device",
        "Country",
        "Alert",
        "Case",
    } <= labels


def test_constraint_cypher_uses_neo4j_five_unique_constraint_syntax() -> None:
    cypher = build_unique_constraint_cypher("Account", "account_id")

    assert "CREATE CONSTRAINT" in cypher
    assert "IF NOT EXISTS" in cypher
    assert "CREATE CONSTRAINT constraint_account_account_id_unique IF NOT EXISTS" in cypher
    assert "FOR (n:Account) REQUIRE n.account_id IS UNIQUE" in cypher


def test_invalid_labels_raise_graph_constraint_error() -> None:
    with pytest.raises(GraphConstraintError):
        build_unique_constraint_cypher("Account`) MATCH (n)", "account_id")


def test_invalid_property_names_raise_graph_constraint_error() -> None:
    with pytest.raises(GraphConstraintError):
        build_unique_constraint_cypher("Account", "account-id")


def test_ensure_graph_constraints_attempts_every_configured_constraint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries: list[str] = []
    monkeypatch.setattr(
        constraints_module,
        "run_cypher_write",
        lambda driver, query, parameters=None, database=None: queries.append(query) or [],
    )

    summary = ensure_graph_constraints(
        FakeDriver(),  # type: ignore[arg-type]
        constraints=(("Account", "account_id"), ("Customer", "customer_id")),
    )

    assert summary["constraints_attempted"] == 2
    assert summary["constraint_names"] == [
        "constraint_account_account_id_unique",
        "constraint_customer_customer_id_unique",
    ]
    assert len(queries) == 2


def test_list_graph_constraints_runs_show_constraints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        constraints_module,
        "run_cypher_read",
        lambda driver, query, parameters=None, database=None: (
            calls.append(query) or [{"name": "constraint_account_account_id_unique"}]
        ),
    )

    rows = list_graph_constraints(FakeDriver())  # type: ignore[arg-type]

    assert calls == ["SHOW CONSTRAINTS"]
    assert rows == [{"name": "constraint_account_account_id_unique"}]


def test_constraint_execution_failures_raise_graph_constraint_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(constraints_module, "run_cypher_write", fail)

    with pytest.raises(GraphConstraintError):
        ensure_graph_constraints(FakeDriver())  # type: ignore[arg-type]
