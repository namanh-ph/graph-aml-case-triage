"""Tests for graph reconciliation helpers."""

import json

import pytest

import graph_aml.graph.reconciliation as reconciliation_module
from graph_aml.graph import (
    GRAPH_NODE_LABELS,
    GRAPH_RELATIONSHIP_TYPES,
    GraphLoadResult,
    GraphReconciliationError,
    collect_graph_counts,
    count_graph_nodes,
    count_graph_relationships,
    reconcile_graph_load,
)


class FakeDriver:
    pass


def test_node_count_query_validates_labels() -> None:
    with pytest.raises(GraphReconciliationError):
        count_graph_nodes(FakeDriver(), "Bad Label")


def test_relationship_count_query_validates_relationship_types() -> None:
    with pytest.raises(GraphReconciliationError):
        count_graph_relationships(FakeDriver(), "BAD-TYPE")


def test_graph_counts_include_all_labels_and_relationships(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reconciliation_module, "run_cypher_scalar", lambda *a, **k: 1)

    counts = collect_graph_counts(FakeDriver())

    assert set(counts["nodes"]) == set(GRAPH_NODE_LABELS)
    assert set(counts["relationships"]) == set(GRAPH_RELATIONSHIP_TYPES)


def test_reconciliation_returns_ok_when_counts_meet_loaded_counts() -> None:
    result = GraphLoadResult(nodes_loaded={"Account": 1}, relationships_loaded={"OWNS": 1})
    counts = {"nodes": {"Account": 2}, "relationships": {"OWNS": 1}}

    reconciliation = reconcile_graph_load(result, counts)

    assert reconciliation["status"] == "ok"
    assert reconciliation["warnings"] == []


def test_reconciliation_returns_warning_when_counts_are_low() -> None:
    result = GraphLoadResult(nodes_loaded={"Account": 2}, relationships_loaded={"OWNS": 2})
    counts = {"nodes": {"Account": 1}, "relationships": {"OWNS": 1}}

    reconciliation = reconcile_graph_load(result, counts)

    assert reconciliation["status"] == "warning"
    assert reconciliation["warnings"]


def test_query_failures_raise_graph_reconciliation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(reconciliation_module, "run_cypher_scalar", fail)

    with pytest.raises(GraphReconciliationError):
        count_graph_nodes(FakeDriver(), "Account")


def test_reconciliation_output_is_json_serialisable() -> None:
    result = GraphLoadResult(nodes_loaded={"Account": 1})
    payload = reconcile_graph_load(result, {"nodes": {"Account": 1}, "relationships": {}})

    json.dumps(payload)
