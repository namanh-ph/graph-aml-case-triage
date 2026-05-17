"""Graph load artefact writers."""

from __future__ import annotations

import json
from pathlib import Path

from graph_aml.graph.exceptions import GraphLoadError
from graph_aml.graph.loader import GraphLoadResult


def graph_load_result_to_dict(result: GraphLoadResult) -> dict[str, object]:
    """Convert a graph load result into a JSON-serialisable dictionary."""

    if not isinstance(result, GraphLoadResult):
        raise GraphLoadError("result must be a GraphLoadResult")
    return {
        "nodes_loaded": dict(result.nodes_loaded),
        "relationships_loaded": dict(result.relationships_loaded),
        "constraints_attempted": result.constraints_attempted,
        "database": result.database,
        "summary": dict(result.summary),
    }


def _write_json(payload: object, output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        raise GraphLoadError(f"Failed to write graph artefact {path}: {exc}") from exc
    return path


def write_graph_load_summary_json(
    result: GraphLoadResult,
    output_path: Path | str = "reports/model_validation/graph_load_summary.json",
) -> Path:
    """Write a graph load summary JSON artefact."""

    return _write_json(graph_load_result_to_dict(result), output_path)


def write_graph_reconciliation_json(
    reconciliation: dict[str, object],
    output_path: Path | str = "reports/model_validation/graph_reconciliation.json",
) -> Path:
    """Write a graph reconciliation JSON artefact."""

    if not isinstance(reconciliation, dict):
        raise GraphLoadError("reconciliation must be a dictionary")
    return _write_json(reconciliation, output_path)


def generate_graph_load_artefacts(
    result: GraphLoadResult,
    reconciliation: dict[str, object] | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write graph load and optional reconciliation artefacts."""

    directory = Path(output_dir)
    paths = {
        "graph_load_summary": write_graph_load_summary_json(
            result, directory / "graph_load_summary.json"
        )
    }
    if reconciliation is not None:
        paths["graph_reconciliation"] = write_graph_reconciliation_json(
            reconciliation,
            directory / "graph_reconciliation.json",
        )
    return paths
