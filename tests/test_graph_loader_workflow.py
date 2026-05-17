"""Tests for high-level graph loading workflows."""

import pandas as pd
import pytest

import graph_aml.graph.loader as loader_module
from graph_aml.graph import (
    GraphLoadError,
    GraphLoadResult,
    load_graph_from_inputs,
    load_graph_from_staged,
)


class FakeDriver:
    pass


class FakeEngine:
    pass


def _inputs() -> dict[str, pd.DataFrame]:
    return {
        "customers": pd.DataFrame([{"customer_id": "C1"}]),
        "accounts": pd.DataFrame([{"customer_id": "C1", "account_id": "A1"}]),
        "transactions": pd.DataFrame(
            [{"transaction_id": "T1", "sender_account_id": "A1", "receiver_account_id": "A1"}]
        ),
        "counterparties": pd.DataFrame(),
        "countries": pd.DataFrame([{"country_code": "AU"}]),
        "alerts": pd.DataFrame([{"alert_id": "AL1", "account_id": "A1", "evidence_ids": ["T1"]}]),
    }


def test_graph_load_result_defaults_are_safe() -> None:
    result = GraphLoadResult()

    assert result.nodes_loaded == {}
    assert result.relationships_loaded == {}


def test_load_graph_from_inputs_loads_nodes_before_relationships(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        loader_module,
        "ensure_graph_constraints",
        lambda *a, **k: {"constraints_attempted": 1},
    )
    monkeypatch.setattr(
        loader_module,
        "load_graph_nodes",
        lambda driver, label, key, rows, batch_size=1000, database=None: (
            calls.append(f"node:{label}") or len(rows)
        ),
    )
    monkeypatch.setattr(
        loader_module,
        "load_graph_relationships",
        lambda driver, rel, *args, **kwargs: calls.append(f"rel:{rel}") or len(args[-1]),
    )

    result = load_graph_from_inputs(FakeDriver(), _inputs())

    assert result.constraints_attempted == 1
    assert calls.index("node:Alert") < calls.index("rel:OWNS")
    assert result.summary["total_nodes_loaded"] >= 1


def test_load_graph_from_inputs_skips_constraints_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(loader_module, "ensure_graph_constraints", lambda *a, **k: pytest.fail())
    monkeypatch.setattr(loader_module, "load_graph_nodes", lambda *a, **k: 0)
    monkeypatch.setattr(loader_module, "load_graph_relationships", lambda *a, **k: 0)

    result = load_graph_from_inputs(FakeDriver(), _inputs(), ensure_constraints_first=False)

    assert result.constraints_attempted == 0


def test_load_graph_from_staged_reads_inputs_and_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loader_module, "read_graph_inputs", lambda engine, **kwargs: _inputs())
    monkeypatch.setattr(
        loader_module,
        "load_graph_from_inputs",
        lambda driver, inputs, **kwargs: GraphLoadResult(nodes_loaded={"Account": 1}),
    )

    result = load_graph_from_staged(FakeEngine(), FakeDriver(), limit=5)

    assert result.nodes_loaded == {"Account": 1}


def test_high_level_loader_failures_raise_graph_load_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(loader_module, "build_all_graph_nodes", fail)

    with pytest.raises(GraphLoadError):
        load_graph_from_inputs(FakeDriver(), _inputs())
