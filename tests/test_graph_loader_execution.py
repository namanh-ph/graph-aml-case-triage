"""Tests for graph node and relationship loading execution."""

import pytest

import graph_aml.graph.loader as loader_module
from graph_aml.graph import GraphLoadError, load_graph_nodes, load_graph_relationships


class FakeDriver:
    pass


def test_load_graph_nodes_returns_zero_for_empty_rows() -> None:
    assert load_graph_nodes(FakeDriver(), "Account", "account_id", []) == 0


def test_load_graph_nodes_calls_batch_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[dict[str, object]], int]] = []
    monkeypatch.setattr(
        loader_module,
        "run_cypher_batch",
        lambda driver, query, rows, batch_size=1000, database=None: (
            calls.append((query, rows, batch_size)) or len(rows)
        ),
    )

    count = load_graph_nodes(
        FakeDriver(), "Account", "account_id", [{"account_id": "A1"}], batch_size=10
    )

    assert count == 1
    assert calls[0][2] == 10


def test_load_graph_relationships_returns_zero_for_empty_rows() -> None:
    assert (
        load_graph_relationships(
            FakeDriver(),
            "OWNS",
            "Customer",
            "customer_id",
            "Account",
            "account_id",
            "customer_id",
            "account_id",
            [],
        )
        == 0
    )


def test_load_graph_relationships_calls_batch_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        loader_module,
        "run_cypher_batch",
        lambda driver, query, rows, batch_size=1000, database=None: (
            calls.append(batch_size) or len(rows)
        ),
    )

    count = load_graph_relationships(
        FakeDriver(),
        "OWNS",
        "Customer",
        "customer_id",
        "Account",
        "account_id",
        "customer_id",
        "account_id",
        [{"customer_id": "C1", "account_id": "A1"}],
        batch_size=25,
    )

    assert count == 1
    assert calls == [25]


def test_execution_failures_raise_graph_load_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(loader_module, "run_cypher_batch", fail)

    with pytest.raises(GraphLoadError):
        load_graph_nodes(FakeDriver(), "Account", "account_id", [{"account_id": "A1"}])


def test_invalid_batch_size_raises_graph_load_error() -> None:
    with pytest.raises(GraphLoadError):
        load_graph_nodes(FakeDriver(), "Account", "account_id", [{"account_id": "A1"}], 0)
