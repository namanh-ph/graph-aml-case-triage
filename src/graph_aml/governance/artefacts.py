"""Artefact writers for governance inventory outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.governance.exceptions import GovernanceInventoryPersistenceError
from graph_aml.governance.lineage_models import GovernanceInventoryBuildResult
from graph_aml.governance.summary import governance_inventory_result_to_dict


def _ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(frame: pd.DataFrame, output_path: Path | str, label: str) -> Path:
    try:
        path = _ensure_parent(Path(output_path))
        frame.to_csv(path, index=False)
        return path
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(f"failed to write {label}: {exc}") from exc


def write_lineage_nodes_csv(
    nodes: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/governance_lineage_nodes.csv",
) -> Path:
    return _write_csv(nodes, output_path, "lineage nodes")


def write_lineage_edges_csv(
    edges: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/governance_lineage_edges.csv",
) -> Path:
    return _write_csv(edges, output_path, "lineage edges")


def write_artefact_registry_csv(
    artefacts: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/governance_artefact_registry.csv",
) -> Path:
    return _write_csv(artefacts, output_path, "artefact registry")


def write_process_inventory_csv(
    processes: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/governance_process_inventory.csv",
) -> Path:
    return _write_csv(processes, output_path, "process inventory")


def write_model_inventory_csv(
    models: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/governance_model_inventory.csv",
) -> Path:
    return _write_csv(models, output_path, "model inventory")


def write_validation_inventory_csv(
    validations: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/governance_validation_inventory.csv",
) -> Path:
    return _write_csv(validations, output_path, "validation inventory")


def write_governance_inventory_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/governance_inventory_summary.json",
) -> Path:
    try:
        path = _ensure_parent(Path(output_path))
        path.write_text(
            json.dumps(summary, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(
            f"failed to write governance inventory summary: {exc}"
        ) from exc


def write_governance_inventory_report_md(
    result: GovernanceInventoryBuildResult,
    output_path: Path | str = "reports/model_validation/governance_inventory_report.md",
) -> Path:
    try:
        path = _ensure_parent(Path(output_path))
        lines = [
            "# Governance Inventory Report",
            "",
            f"- Inventory run: `{result.inventory_run_id}`",
            f"- Lineage nodes: {len(result.lineage_nodes)}",
            f"- Lineage edges: {len(result.lineage_edges)}",
            f"- Artefacts: {len(result.artefact_registry)}",
            f"- Processes: {len(result.process_inventory)}",
            f"- Model inventory rows: {len(result.model_inventory)}",
            f"- Validation inventory rows: {len(result.validation_inventory)}",
            "",
            "## Lineage Scope",
            "",
            (
                "Lineage combines persisted table metadata, configured process dependencies, "
                "and run metadata where available."
            ),
            "",
            "## Process Dependencies",
            "",
        ]
        if result.process_inventory.empty:
            lines.append("No configured process dependencies were available.")
        else:
            for row in result.process_inventory.sort_values("process_name").to_dict("records"):
                process_name = row["process_name"]
                input_count = row["input_count"]
                output_count = row["output_count"]
                lines.append(f"- `{process_name}`: {input_count} inputs, {output_count} outputs")
        lines.extend(
            [
                "",
                "## Model Inventory",
                "",
                f"Model inventory rows: {len(result.model_inventory)}.",
                "",
                "## Validation Inventory",
                "",
                f"Validation inventory rows: {len(result.validation_inventory)}.",
                "",
                "## Artefact Registry",
                "",
                (
                    "The artefact registry scans only configured local roots, filters by "
                    "extension and size, and records deterministic file hashes."
                ),
                "",
                "## Reproducibility Notes",
                "",
                (
                    "Inventory outputs are versioned, timestamped, and derived from "
                    "persisted state plus local documentation/report files."
                ),
                "",
                "## Limitations",
                "",
                (
                    "Configured process lineage documents expected dependencies and does "
                    "not prove every runtime dependency unless corroborated by audit events."
                ),
            ]
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
    except Exception as exc:
        raise GovernanceInventoryPersistenceError(
            f"failed to write governance inventory report: {exc}"
        ) from exc


def generate_governance_inventory_artefacts(
    result: GovernanceInventoryBuildResult,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    output = Path(output_dir)
    return {
        "lineage_nodes_csv": write_lineage_nodes_csv(
            result.lineage_nodes,
            output / "governance_lineage_nodes.csv",
        ),
        "lineage_edges_csv": write_lineage_edges_csv(
            result.lineage_edges,
            output / "governance_lineage_edges.csv",
        ),
        "artefact_registry_csv": write_artefact_registry_csv(
            result.artefact_registry,
            output / "governance_artefact_registry.csv",
        ),
        "process_inventory_csv": write_process_inventory_csv(
            result.process_inventory,
            output / "governance_process_inventory.csv",
        ),
        "model_inventory_csv": write_model_inventory_csv(
            result.model_inventory,
            output / "governance_model_inventory.csv",
        ),
        "validation_inventory_csv": write_validation_inventory_csv(
            result.validation_inventory,
            output / "governance_validation_inventory.csv",
        ),
        "summary_json": write_governance_inventory_summary_json(
            governance_inventory_result_to_dict(result),
            output / "governance_inventory_summary.json",
        ),
        "report_md": write_governance_inventory_report_md(
            result,
            output / "governance_inventory_report.md",
        ),
    }
