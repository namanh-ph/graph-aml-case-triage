"""Static DDL tests for governance inventory tables."""

from pathlib import Path

SQL = Path("src/graph_aml/database/sql/003_create_core_tables.sql").read_text(encoding="utf-8")


def test_governance_inventory_tables_exist() -> None:
    for table in (
        "governance.inventory_runs",
        "governance.lineage_nodes",
        "governance.lineage_edges",
        "governance.artefact_registry",
        "governance.process_inventory",
        "governance.model_inventory",
        "governance.validation_inventory",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in SQL


def test_governance_inventory_tables_contain_key_fields() -> None:
    for token in (
        "inventory_run_id TEXT",
        "metadata JSONB",
        "node_id TEXT",
        "relationship_type TEXT",
        "artefact_id TEXT",
        "process_name TEXT",
        "model_version TEXT",
        "validation_type TEXT",
    ):
        assert token in SQL


def test_governance_inventory_ddl_has_primary_keys_and_indexes() -> None:
    for token in (
        "PRIMARY KEY (inventory_run_id, node_id)",
        "PRIMARY KEY (inventory_run_id, source_id, target_id, relationship_type)",
        "PRIMARY KEY (inventory_run_id, artefact_id)",
        "PRIMARY KEY (inventory_run_id, process_name)",
        "idx_inventory_runs_version",
        "idx_lineage_nodes_type",
        "idx_artefact_registry_type",
        "idx_validation_inventory_type",
    ):
        assert token in SQL


def test_governance_inventory_ddl_is_non_destructive() -> None:
    section = SQL[SQL.index("CREATE TABLE IF NOT EXISTS governance.inventory_runs") :]
    assert "DROP TABLE" not in section
    assert "TRUNCATE" not in section
