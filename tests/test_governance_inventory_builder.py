"""Tests for high-level governance inventory builders."""

import pandas as pd

from graph_aml.governance import (
    GovernanceInventoryBuildResult,
    GovernanceInventoryConfig,
    build_governance_inventory_from_inputs,
    build_model_inventory,
    build_validation_inventory,
)


def _inputs() -> dict[str, object]:
    return {
        "table_counts": pd.DataFrame(
            [{"schema_name": "aml", "table_name": "alerts", "row_count": 2}]
        ),
        "audit_events": pd.DataFrame(),
        "model_runs": {
            "model_runs": pd.DataFrame(
                [
                    {
                        "model_run_id": "m1",
                        "model_name": "iforest",
                        "model_version": "v1",
                        "model_type": "isolation_forest",
                        "feature_version": "features_v1",
                        "created_at": "2026-01-01",
                    }
                ]
            ),
            "supervised_model_runs": pd.DataFrame(
                [
                    {
                        "run_id": "s1",
                        "model_name": "supervised",
                        "model_version": "sv1",
                        "model_family": "logistic_regression",
                        "dataset_version": "d1",
                        "entity_level": "case",
                        "trained_at": "2026-01-02",
                    }
                ]
            ),
        },
        "validation_runs": {
            "model_comparison_runs": pd.DataFrame(
                [
                    {
                        "comparison_run_id": "c1",
                        "comparison_version": "cv1",
                        "created_at": "2026-01-03",
                    }
                ]
            ),
            "monitoring_runs": pd.DataFrame(),
            "explainability_runs": pd.DataFrame(),
        },
    }


def test_model_and_validation_inventory_summarise_inputs() -> None:
    model_inventory = build_model_inventory(_inputs(), "run1")
    validation_inventory = build_validation_inventory(_inputs(), "run1")
    assert len(model_inventory) == 2
    assert len(validation_inventory) == 1
    assert "sv1" in set(model_inventory["model_version"])
    assert "model_comparison" in set(validation_inventory["validation_type"])


def test_high_level_inventory_builder_returns_result_and_counts() -> None:
    config = GovernanceInventoryConfig(
        known_processes={"rules": {"inputs": ("staging.transactions",), "outputs": ("aml.alerts",)}}
    )
    result = build_governance_inventory_from_inputs(_inputs(), config)
    assert isinstance(result, GovernanceInventoryBuildResult)
    assert result.summary["lineage_node_count"] == len(result.lineage_nodes)
    assert result.metadata["inventory_version"] == config.inventory_version
    assert not result.lineage_nodes.empty
    assert not result.lineage_edges.empty
    assert not result.process_inventory.empty


def test_inventory_builder_does_not_mutate_inputs() -> None:
    inputs = _inputs()
    original = inputs["table_counts"].copy(deep=True)  # type: ignore[index, union-attr]
    build_governance_inventory_from_inputs(inputs, GovernanceInventoryConfig())
    pd.testing.assert_frame_equal(inputs["table_counts"], original)  # type: ignore[arg-type]
