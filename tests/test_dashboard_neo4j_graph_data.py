"""Tests for optional Neo4j dashboard graph readers."""

import pandas as pd
import pytest

from graph_aml.dashboard.exceptions import DashboardDataError
from graph_aml.dashboard.neo4j_graph_data import (
    neo4j_graph_records_to_frames,
    read_neo4j_graph_neighbourhood,
)


def test_neo4j_reader_uses_existing_cypher_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_read(driver: object, query: str, parameters: dict[str, object], database=None):
        calls.append(driver)
        assert parameters["account_id"] == "A1"
        assert "MATCH path" in query
        return [{"nodes": [{"account_id": "A1", "labels": ["Account"]}], "relationships": []}]

    monkeypatch.setattr("graph_aml.dashboard.neo4j_graph_data.run_cypher_read", fake_read)
    driver = object()

    payload = read_neo4j_graph_neighbourhood(driver, "A1")

    assert calls == [driver]
    assert payload["nodes"][0]["account_id"] == "A1"


def test_neo4j_reader_does_not_create_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "graph_aml.graph.connection.create_neo4j_driver",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("driver")),
    )
    monkeypatch.setattr(
        "graph_aml.dashboard.neo4j_graph_data.run_cypher_read",
        lambda *_args, **_kwargs: [],
    )

    assert read_neo4j_graph_neighbourhood(object(), "A1") == {"nodes": [], "relationships": []}


def test_neo4j_records_convert_to_frames() -> None:
    frames = neo4j_graph_records_to_frames(
        {
            "nodes": [{"account_id": "A1", "labels": ["Account"], "risk_band": "high"}],
            "relationships": [{"source_id": "A1", "target_id": "A2", "type": "PAYS"}],
        }
    )

    assert isinstance(frames["nodes"], pd.DataFrame)
    assert isinstance(frames["edges"], pd.DataFrame)


def test_neo4j_read_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> list[dict[str, object]]:
        raise RuntimeError("boom")

    monkeypatch.setattr("graph_aml.dashboard.neo4j_graph_data.run_cypher_read", fail)

    with pytest.raises(DashboardDataError):
        read_neo4j_graph_neighbourhood(object(), "A1")
