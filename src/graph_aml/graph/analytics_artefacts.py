"""Artefact writers for graph analytics features."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.graph.analytics import (
    GraphAnalyticsResult,
    graph_features_to_records,
)
from graph_aml.graph.exceptions import GraphAnalyticsError, GraphFeaturePersistenceError
from graph_aml.graph.feature_persistence import GraphFeaturePersistenceResult


def write_graph_features_csv(
    features: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/graph_features.csv",
) -> Path:
    """Write graph analytics features as CSV."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        features.to_csv(path, index=False)
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to write graph features CSV: {exc}") from exc
    return path


def _write_json(payload: object, output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        raise GraphAnalyticsError(f"Failed to write graph analytics JSON: {exc}") from exc
    return path


def write_graph_features_json(
    features: pd.DataFrame,
    output_path: Path | str = "reports/model_validation/graph_features.json",
) -> Path:
    """Write graph analytics features as JSON."""

    return _write_json(graph_features_to_records(features), output_path)


def write_graph_analytics_summary_json(
    summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/graph_analytics_summary.json",
) -> Path:
    """Write graph analytics summary JSON."""

    if not isinstance(summary, dict):
        raise GraphAnalyticsError("summary must be a dictionary")
    return _write_json(summary, output_path)


def generate_graph_analytics_artefacts(
    result: GraphAnalyticsResult,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write graph analytics feature and summary artefacts."""

    if not isinstance(result, GraphAnalyticsResult):
        raise GraphAnalyticsError("result must be GraphAnalyticsResult")
    directory = Path(output_dir)
    return {
        "features_csv": write_graph_features_csv(
            result.features,
            directory / "graph_features.csv",
        ),
        "features_json": write_graph_features_json(
            result.features,
            directory / "graph_features.json",
        ),
        "summary_json": write_graph_analytics_summary_json(
            result.summary,
            directory / "graph_analytics_summary.json",
        ),
    }


def _graph_feature_persistence_result_to_dict(
    result: GraphFeaturePersistenceResult,
) -> dict[str, object]:
    return {
        "rows_prepared": result.rows_prepared,
        "rows_persisted": result.rows_persisted,
        "unique_account_count": result.unique_account_count,
        "feature_date": result.feature_date,
        "feature_version": result.feature_version,
        "graph_build_id": result.graph_build_id,
        "graph_database": result.graph_database,
        "persisted": result.persisted,
        "metadata": result.metadata,
        "summary": result.summary,
    }


def write_graph_feature_persistence_summary_json(
    result: GraphFeaturePersistenceResult,
    output_path: Path | str = "reports/model_validation/graph_feature_persistence_summary.json",
) -> Path:
    """Write graph feature persistence summary JSON."""

    if not isinstance(result, GraphFeaturePersistenceResult):
        raise GraphFeaturePersistenceError("result must be GraphFeaturePersistenceResult")
    try:
        return _write_json(_graph_feature_persistence_result_to_dict(result), output_path)
    except GraphAnalyticsError as exc:
        raise GraphFeaturePersistenceError(str(exc)) from exc


def write_graph_feature_quality_summary_json(
    quality_summary: dict[str, object],
    output_path: Path | str = "reports/model_validation/graph_feature_quality_summary.json",
) -> Path:
    """Write graph feature quality summary JSON."""

    if not isinstance(quality_summary, dict):
        raise GraphFeaturePersistenceError("quality_summary must be a dictionary")
    try:
        return _write_json(quality_summary, output_path)
    except GraphAnalyticsError as exc:
        raise GraphFeaturePersistenceError(str(exc)) from exc


def generate_graph_feature_persistence_artefacts(
    result: GraphFeaturePersistenceResult,
    quality_summary: dict[str, object] | None = None,
    output_dir: Path | str = "reports/model_validation",
) -> dict[str, Path]:
    """Write graph feature persistence and quality artefacts."""

    directory = Path(output_dir)
    paths = {
        "persistence_summary_json": write_graph_feature_persistence_summary_json(
            result,
            directory / "graph_feature_persistence_summary.json",
        )
    }
    if quality_summary is not None:
        paths["quality_summary_json"] = write_graph_feature_quality_summary_json(
            quality_summary,
            directory / "graph_feature_quality_summary.json",
        )
    return paths
