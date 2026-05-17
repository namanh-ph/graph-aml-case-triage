"""Tests for governance lineage models and builders."""

import pandas as pd
import pytest

from graph_aml.governance import (
    LINEAGE_EDGE_COLUMNS,
    LINEAGE_NODE_COLUMNS,
    PROCESS_INVENTORY_COLUMNS,
    GovernanceInventoryConfig,
    LineageBuildError,
    LineageEdge,
    LineageNode,
    build_governance_lineage,
    build_inventory_run_id,
    build_process_lineage,
    build_run_dependency_edges,
    build_table_lineage_nodes,
    lineage_edge_to_record,
    lineage_node_to_record,
)


def _config() -> GovernanceInventoryConfig:
    return GovernanceInventoryConfig(
        known_processes={"rules": {"inputs": ("staging.transactions",), "outputs": ("aml.alerts",)}}
    )


def test_lineage_node_and_edge_convert_to_records() -> None:
    node = lineage_node_to_record(LineageNode("table:a.b", "table", "a.b"), "run1")
    edge = lineage_edge_to_record(LineageEdge("a", "b", "depends_on"), "run1")
    assert node["inventory_run_id"] == "run1"
    assert edge["relationship_type"] == "depends_on"


def test_inventory_run_id_is_deterministic_for_fixed_timestamp() -> None:
    timestamp = pd.Timestamp("2026-01-01T00:00:00Z")
    first = build_inventory_run_id(_config(), timestamp)
    second = build_inventory_run_id(_config(), timestamp)
    assert first == second


def test_table_and_process_lineage_preserve_columns() -> None:
    counts = pd.DataFrame(
        [{"schema_name": "aml", "table_name": "alerts", "row_count": 3}]
    )
    nodes = build_table_lineage_nodes(counts, "run1")
    process_nodes, process_edges, processes = build_process_lineage(_config(), "run1")
    assert tuple(nodes.columns) == LINEAGE_NODE_COLUMNS
    assert tuple(process_nodes.columns) == LINEAGE_NODE_COLUMNS
    assert tuple(process_edges.columns) == LINEAGE_EDGE_COLUMNS
    assert tuple(processes.columns) == PROCESS_INVENTORY_COLUMNS
    assert "process:rules" in set(process_nodes["node_id"])


def test_run_dependency_edges_are_built_from_audit_events() -> None:
    edges = build_run_dependency_edges(
        {
            "audit_events": pd.DataFrame(
                [{"component": "rules", "run_id": "run-123", "event_type": "rules"}]
            )
        },
        pd.DataFrame(),
        "inventory",
    )
    assert not edges.empty
    assert "run:run-123" in set(edges["target_id"])


def test_high_level_lineage_does_not_mutate_inputs() -> None:
    counts = pd.DataFrame(
        [{"schema_name": "aml", "table_name": "alerts", "row_count": 3}]
    )
    original = counts.copy(deep=True)
    nodes, edges, processes = build_governance_lineage(
        {"table_counts": counts, "audit_events": pd.DataFrame()},
        _config(),
        "run1",
    )
    pd.testing.assert_frame_equal(counts, original)
    assert not nodes.empty
    assert not edges.empty
    assert not processes.empty


def test_malformed_table_counts_raise_lineage_error() -> None:
    with pytest.raises(LineageBuildError):
        build_table_lineage_nodes(pd.DataFrame({"bad": [1]}), "run1")
