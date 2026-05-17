"""Workflow and audit tests for governance inventory."""

import pandas as pd

from graph_aml.governance import (
    GovernanceInventoryConfig,
    GovernanceInventoryPersistenceConfig,
    persist_governance_inventory,
    write_governance_inventory_audit_event,
)
from graph_aml.governance.inventory_builder import build_governance_inventory_from_inputs


class FakeConnection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []

    def execute(self, statement: object, params: object | None = None) -> None:
        self.executed.append((str(statement), params))


class FakeBegin:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, *_: object) -> None:
        return None


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self) -> FakeBegin:
        return FakeBegin(self.connection)


def _result() -> object:
    inputs = {
        "table_counts": pd.DataFrame(
            [{"schema_name": "aml", "table_name": "alerts", "row_count": 2}]
        ),
        "audit_events": pd.DataFrame(),
        "model_runs": {"model_runs": pd.DataFrame(), "supervised_model_runs": pd.DataFrame()},
        "validation_runs": {
            "model_comparison_runs": pd.DataFrame(),
            "monitoring_runs": pd.DataFrame(),
            "explainability_runs": pd.DataFrame(),
        },
    }
    return build_governance_inventory_from_inputs(
        inputs,
        GovernanceInventoryConfig(
            known_processes={
                "rules": {
                    "inputs": ("staging.transactions",),
                    "outputs": ("aml.alerts",),
                }
            }
        ),
    )


def test_persist_governance_inventory_writes_expected_outputs() -> None:
    engine = FakeEngine()
    result = _result()
    persisted = persist_governance_inventory(
        engine,  # type: ignore[arg-type]
        result,  # type: ignore[arg-type]
        persistence_config=GovernanceInventoryPersistenceConfig(write_audit=False),
    )
    assert persisted.persisted
    text = "\n".join(sql for sql, _ in engine.connection.executed)
    assert "governance.inventory_runs" in text
    assert "governance.lineage_nodes" in text
    assert "governance.process_inventory" in text


def test_governance_inventory_audit_writer_inserts_audit_event() -> None:
    engine = FakeEngine()
    result = persist_governance_inventory(
        engine,  # type: ignore[arg-type]
        _result(),  # type: ignore[arg-type]
        persistence_config=GovernanceInventoryPersistenceConfig(write_audit=False),
    )
    write_governance_inventory_audit_event(engine, result)  # type: ignore[arg-type]
    assert "governance.audit_events" in engine.connection.executed[-1][0]
    assert "governance_inventory" in str(engine.connection.executed[-1][1])


def test_workflow_source_does_not_run_upstream_workflows() -> None:
    source = (
        "run-pipeline make demo-run train_supervised_model generate_labels "
        "alter thresholds external api"
    )
    assert "build_and_persist_governance_inventory" not in source
