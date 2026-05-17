"""Tests for reading projected Neo4j graph data."""

import pytest

import graph_aml.graph.projection as projection_module
from graph_aml.graph import GraphProjectionError, ProjectedGraphData, read_projected_graph_data


class FakeDriver:
    pass


def _node(node_id: str, label: str, **properties: object) -> dict[str, object]:
    return {"node": {"id": node_id, "labels": [label], "properties": properties}}


def _relationship(source: str, target: str, rel_type: str) -> dict[str, object]:
    return {
        "relationship": {
            "source_id": source,
            "target_id": target,
            "type": rel_type,
            "properties": {},
        }
    }


def test_read_projected_graph_data_calls_cypher_read(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_read(driver: object, query: str, **kwargs: object) -> list[dict[str, object]]:
        calls.append(query)
        if "RETURN {id:" in query:
            return [_node("A2", "Account"), _node("AL1", "Alert"), _node("T1", "Transaction")]
        return [_relationship("A2", "T1", "SENT")]

    monkeypatch.setattr(projection_module, "run_cypher_read", fake_read)

    projected = read_projected_graph_data(FakeDriver())

    assert isinstance(projected, ProjectedGraphData)
    assert len(calls) == 2
    assert projected.account_ids == ("A2",)
    assert projected.alert_ids == ("AL1",)
    assert projected.transaction_ids == ("T1",)
    assert projected.relationships[0]["type"] == "SENT"


def test_read_projected_graph_data_sorts_nodes_and_relationships(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_read(driver: object, query: str, **kwargs: object) -> list[dict[str, object]]:
        if "RETURN {id:" in query:
            return [_node("B", "Account"), _node("A", "Account")]
        return [_relationship("B", "A", "SENT"), _relationship("A", "B", "RECEIVED")]

    monkeypatch.setattr(projection_module, "run_cypher_read", fake_read)

    projected = read_projected_graph_data(FakeDriver())

    assert [node["id"] for node in projected.nodes] == ["A", "B"]
    assert [row["source_id"] for row in projected.relationships] == ["A", "B"]


def test_read_projected_graph_data_query_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(projection_module, "run_cypher_read", fail)

    with pytest.raises(GraphProjectionError):
        read_projected_graph_data(FakeDriver())
