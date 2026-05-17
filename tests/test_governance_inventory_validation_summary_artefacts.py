"""Tests for governance inventory validation, summaries, and artefacts."""

import json
from pathlib import Path

import pandas as pd
import pytest

from graph_aml.governance import (
    ARTEFACT_REGISTRY_COLUMNS,
    LINEAGE_EDGE_COLUMNS,
    LINEAGE_NODE_COLUMNS,
    MODEL_INVENTORY_COLUMNS,
    PROCESS_INVENTORY_COLUMNS,
    VALIDATION_INVENTORY_COLUMNS,
    GovernanceInventoryBuildResult,
    GovernanceInventoryValidationError,
    build_governance_inventory_quality_summary,
    generate_governance_inventory_artefacts,
    governance_inventory_result_to_dict,
    summarise_artefact_registry,
    summarise_lineage_edges,
    summarise_lineage_nodes,
    summarise_model_inventory,
    summarise_process_inventory,
    summarise_validation_inventory,
    validate_artefact_registry,
    validate_governance_inventory_result,
)


def _result(tmp_path: Path) -> GovernanceInventoryBuildResult:
    artefact = tmp_path / "a.md"
    artefact.write_text("x", encoding="utf-8")
    nodes = pd.DataFrame(
        [["run1", "a", "table", "a", None, None, 1, {}]],
        columns=LINEAGE_NODE_COLUMNS,
    )
    edges = pd.DataFrame(
        [["run1", "a", "missing", "depends_on", "p", {}]],
        columns=LINEAGE_EDGE_COLUMNS,
    )
    artefacts = pd.DataFrame(
        [
            [
                "run1",
                "art1",
                "documentation",
                "a.md",
                "a.md",
                ".md",
                1,
                "a" * 64,
                "2026-01-01",
                str(tmp_path),
                {},
            ]
        ],
        columns=ARTEFACT_REGISTRY_COLUMNS,
    )
    processes = pd.DataFrame(
        [["run1", "p", 1, 1, ["a"], ["b"], None, None, {}]],
        columns=PROCESS_INVENTORY_COLUMNS,
    )
    models = pd.DataFrame(
        [["run1", "m", "v1", "family", "d1", "case", 1, None, {}]],
        columns=MODEL_INVENTORY_COLUMNS,
    )
    validations = pd.DataFrame(
        [["run1", "monitoring", "mv1", 1, "r1", None, {}, {}]],
        columns=VALIDATION_INVENTORY_COLUMNS,
    )
    return GovernanceInventoryBuildResult(
        "run1",
        nodes,
        edges,
        artefacts,
        processes,
        models,
        validations,
        summary={"inventory_run_id": "run1"},
        metadata={},
    )


def test_valid_inventory_result_and_quality_summary(tmp_path: Path) -> None:
    result = _result(tmp_path)
    validate_governance_inventory_result(result)
    quality = build_governance_inventory_quality_summary(result)
    assert quality["orphan_edge_count"] == 1
    assert quality["missing_hash_count"] == 0


def test_artefact_registry_validation_catches_missing_ids(tmp_path: Path) -> None:
    artefacts = _result(tmp_path).artefact_registry.copy()
    artefacts.loc[0, "artefact_id"] = ""
    with pytest.raises(GovernanceInventoryValidationError):
        validate_artefact_registry(artefacts)


def test_governance_summaries_and_result_dict_are_json_serialisable(tmp_path: Path) -> None:
    result = _result(tmp_path)
    payload = governance_inventory_result_to_dict(result)
    json.dumps(payload, default=str)
    assert summarise_lineage_nodes(result.lineage_nodes)["node_type_counts"]["table"] == 1
    assert summarise_lineage_edges(result.lineage_edges)["process_counts"]["p"] == 1
    artefact_summary = summarise_artefact_registry(result.artefact_registry)
    validation_summary = summarise_validation_inventory(result.validation_inventory)
    assert artefact_summary["artefact_type_counts"]["documentation"] == 1
    assert summarise_process_inventory(result.process_inventory)["row_count"] == 1
    assert summarise_model_inventory(result.model_inventory)["model_version_counts"]["v1"] == 1
    assert validation_summary["validation_type_counts"]["monitoring"] == 1


def test_governance_inventory_artefact_generator_writes_files(tmp_path: Path) -> None:
    paths = generate_governance_inventory_artefacts(_result(tmp_path), tmp_path / "out")
    assert all(path.exists() for path in paths.values())
    assert json.loads(paths["summary_json"].read_text(encoding="utf-8"))
    assert paths["report_md"].read_text(encoding="utf-8").startswith("# Governance")
