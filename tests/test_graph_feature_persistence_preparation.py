"""Tests for preparing graph analytics features for PostgreSQL persistence."""

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from graph_aml.graph import (
    GRAPH_ANALYTICS_FEATURE_COLUMNS,
    GRAPH_FEATURE_METADATA_COLUMNS,
    GraphFeaturePersistenceConfig,
    GraphFeatureValidationError,
    prepare_graph_features_for_persistence,
)


def _features() -> pd.DataFrame:
    row = {column: 0 for column in GRAPH_ANALYTICS_FEATURE_COLUMNS}
    row.update(
        {
            "account_id": "A1",
            "degree": None,
            "pagerank_score": 0.4,
            "community_id": 2,
            "shortest_path_to_flagged": None,
        }
    )
    return pd.DataFrame([row], columns=GRAPH_ANALYTICS_FEATURE_COLUMNS)


def test_prepared_features_include_feature_and_metadata_columns() -> None:
    prepared = prepare_graph_features_for_persistence(
        _features(),
        GraphFeaturePersistenceConfig(
            feature_date=date(2025, 1, 25),
            graph_database="neo4j",
        ),
        computed_at=datetime(2025, 1, 25, 1, 2, 3, tzinfo=UTC),
    )

    for column in GRAPH_ANALYTICS_FEATURE_COLUMNS:
        assert column in prepared.columns
    for column in GRAPH_FEATURE_METADATA_COLUMNS:
        assert column in prepared.columns
    assert prepared.loc[0, "feature_date"] == date(2025, 1, 25)
    assert prepared.loc[0, "feature_version"] == "graph_features_v1"
    assert prepared.loc[0, "graph_build_id"] == "graph_features_v1_2025_01_25_neo4j"
    assert prepared.loc[0, "computed_at"].tzinfo is not None


def test_preparation_fills_missing_numeric_values_and_preserves_nullable_path() -> None:
    prepared = prepare_graph_features_for_persistence(_features())

    assert prepared.loc[0, "degree"] == 0
    assert pd.isna(prepared.loc[0, "shortest_path_to_flagged"])


def test_preparation_deduplicates_account_rows_deterministically() -> None:
    features = pd.concat(
        [
            _features(),
            _features().assign(account_id="A1", pagerank_score=0.9),
        ],
        ignore_index=True,
    )

    prepared = prepare_graph_features_for_persistence(features)

    assert len(prepared) == 1
    assert prepared.loc[0, "pagerank_score"] == 0.9


def test_missing_required_columns_raise_validation_error() -> None:
    with pytest.raises(GraphFeatureValidationError):
        prepare_graph_features_for_persistence(_features().drop(columns=["account_id"]))


def test_preparation_does_not_mutate_input_dataframe() -> None:
    features = _features()
    original = features.copy(deep=True)

    prepare_graph_features_for_persistence(features)

    pd.testing.assert_frame_equal(features, original)
