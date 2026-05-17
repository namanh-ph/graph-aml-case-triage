"""Tests for governance inventory persistence SQL."""

import pytest

from graph_aml.governance import (
    GovernanceInventoryPersistenceConfig,
    GovernanceInventoryPersistenceError,
    build_artefact_registry_upsert_sql,
    build_inventory_run_insert_sql,
    build_lineage_edge_upsert_sql,
    build_lineage_node_upsert_sql,
    build_model_inventory_insert_sql,
    build_process_inventory_upsert_sql,
    build_validation_inventory_insert_sql,
    validate_governance_inventory_persistence_config,
)


def test_default_governance_inventory_persistence_config_is_valid() -> None:
    validate_governance_inventory_persistence_config(GovernanceInventoryPersistenceConfig())


def test_invalid_governance_inventory_persistence_config_raises() -> None:
    with pytest.raises(GovernanceInventoryPersistenceError):
        validate_governance_inventory_persistence_config(
            GovernanceInventoryPersistenceConfig(batch_size=0)
        )


@pytest.mark.parametrize(
    ("sql_builder", "table"),
    [
        (build_inventory_run_insert_sql, "governance.inventory_runs"),
        (build_lineage_node_upsert_sql, "governance.lineage_nodes"),
        (build_lineage_edge_upsert_sql, "governance.lineage_edges"),
        (build_artefact_registry_upsert_sql, "governance.artefact_registry"),
        (build_process_inventory_upsert_sql, "governance.process_inventory"),
        (build_model_inventory_insert_sql, "governance.model_inventory"),
        (build_validation_inventory_insert_sql, "governance.validation_inventory"),
    ],
)
def test_governance_inventory_sql_targets_expected_tables(
    sql_builder: object,
    table: str,
) -> None:
    sql = sql_builder()  # type: ignore[operator]
    assert table in sql
    assert ":" in sql


def test_upsert_sql_contains_on_conflict() -> None:
    assert "ON CONFLICT" in build_lineage_node_upsert_sql()
    assert "ON CONFLICT" in build_lineage_edge_upsert_sql()
    assert "ON CONFLICT" in build_artefact_registry_upsert_sql()
    assert "ON CONFLICT" in build_process_inventory_upsert_sql()
