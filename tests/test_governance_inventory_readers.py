"""Tests for governance inventory readback utilities."""

import pandas as pd
import pytest

from graph_aml.governance import (
    GovernanceInventoryPersistenceError,
    read_artefact_registry,
    read_governance_inventory_summary,
    read_inventory_runs,
    read_lineage_edges,
    read_lineage_nodes,
    read_model_inventory,
    read_process_inventory,
    read_validation_inventory,
)


class FakeEngine:
    pass


def test_governance_inventory_readers_query_expected_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_read(sql: object, *_: object, **__: object) -> pd.DataFrame:
        calls.append(str(sql))
        return pd.DataFrame({"row_count": [0]})

    monkeypatch.setattr(pd, "read_sql_query", fake_read)
    engine = FakeEngine()
    read_inventory_runs(engine, inventory_version="v1", limit=1)  # type: ignore[arg-type]
    read_lineage_nodes(engine, inventory_run_id="r1", node_type="table", limit=1)  # type: ignore[arg-type]
    read_lineage_edges(engine, inventory_run_id="r1", process_name="rules", limit=1)  # type: ignore[arg-type]
    read_artefact_registry(engine, inventory_run_id="r1", artefact_type="metrics", limit=1)  # type: ignore[arg-type]
    read_process_inventory(engine, inventory_run_id="r1", process_name="rules", limit=1)  # type: ignore[arg-type]
    read_model_inventory(engine, inventory_run_id="r1", model_version="v1", limit=1)  # type: ignore[arg-type]
    read_validation_inventory(engine, inventory_run_id="r1", validation_type="monitoring", limit=1)  # type: ignore[arg-type]
    text = "\n".join(calls)
    assert "governance.inventory_runs" in text
    assert "governance.lineage_nodes" in text
    assert "governance.lineage_edges" in text
    assert "governance.artefact_registry" in text
    assert "governance.process_inventory" in text
    assert "governance.model_inventory" in text
    assert "governance.validation_inventory" in text
    assert ":limit" in text


def test_governance_inventory_summary_is_json_serialisable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_read(sql: object, *_args: object, **_kwargs: object) -> pd.DataFrame:
        text = str(sql)
        if "inventory_run_count" in text:
            return pd.DataFrame({"inventory_run_count": [0]})
        if "inventory_version" in text and "inventory_run_id" in text:
            return pd.DataFrame()
        return pd.DataFrame({"row_count": [0]})

    monkeypatch.setattr(
        pd,
        "read_sql_query",
        fake_read,
    )
    summary = read_governance_inventory_summary(FakeEngine())  # type: ignore[arg-type]
    assert "inventory_run_count" in summary


def test_governance_inventory_reader_failures_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> pd.DataFrame:
        raise RuntimeError("boom")

    monkeypatch.setattr(pd, "read_sql_query", fail)
    with pytest.raises(GovernanceInventoryPersistenceError):
        read_inventory_runs(FakeEngine())  # type: ignore[arg-type]


def test_governance_inventory_readers_validate_limits() -> None:
    with pytest.raises(GovernanceInventoryPersistenceError):
        read_inventory_runs(FakeEngine(), limit=-1)  # type: ignore[arg-type]
