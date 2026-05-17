"""Tests for graph feature validation helpers."""

import json

import pandas as pd
import pytest

from graph_aml.graph import (
    GRAPH_ANALYTICS_FEATURE_COLUMNS,
    GraphFeatureValidationError,
    build_graph_feature_quality_summary,
    compare_graph_feature_row_counts,
    prepare_graph_features_for_persistence,
    validate_graph_feature_frame,
    validate_prepared_graph_feature_frame,
)


def _features() -> pd.DataFrame:
    row = {column: 0 for column in GRAPH_ANALYTICS_FEATURE_COLUMNS}
    row.update({"account_id": "A1", "pagerank_score": 0.2, "alert_count": 1})
    return pd.DataFrame([row], columns=GRAPH_ANALYTICS_FEATURE_COLUMNS)


def test_valid_graph_feature_frame_passes_validation() -> None:
    validate_graph_feature_frame(_features())


def test_missing_or_duplicate_account_ids_fail_validation() -> None:
    with pytest.raises(GraphFeatureValidationError):
        validate_graph_feature_frame(_features().assign(account_id=None))

    with pytest.raises(GraphFeatureValidationError):
        validate_graph_feature_frame(pd.concat([_features(), _features()]))


def test_missing_required_graph_feature_columns_fail_validation() -> None:
    with pytest.raises(GraphFeatureValidationError):
        validate_graph_feature_frame(_features().drop(columns=["degree"]))


def test_prepared_graph_feature_frame_validation() -> None:
    prepared = prepare_graph_features_for_persistence(_features())

    validate_prepared_graph_feature_frame(prepared)
    with pytest.raises(GraphFeatureValidationError):
        validate_prepared_graph_feature_frame(prepared.drop(columns=["metadata"]))


def test_row_count_comparison_statuses() -> None:
    ok = compare_graph_feature_row_counts(_features(), _features())
    warning = compare_graph_feature_row_counts(_features(), pd.DataFrame())

    assert ok["status"] == "ok"
    assert warning["status"] == "warning"
    assert warning["warnings"]


def test_quality_summary_contains_counts_and_is_json_serialisable() -> None:
    summary = build_graph_feature_quality_summary(_features())

    json.dumps(summary)
    assert summary["row_count"] == 1
    assert summary["nonzero_feature_counts"]["pagerank_score"] == 1
    assert summary["nonzero_feature_counts"]["alert_count"] == 1
