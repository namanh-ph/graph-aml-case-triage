"""Tests for graph analytics feature merging and serialisation."""

import json

import pandas as pd
import pytest

from graph_aml.graph import (
    GRAPH_ANALYTICS_FEATURE_COLUMNS,
    GraphAnalyticsError,
    graph_features_from_records,
    graph_features_to_records,
    merge_graph_feature_frames,
)


def test_feature_frames_merge_on_account_id_and_fill_missing_values() -> None:
    left = pd.DataFrame([{"account_id": "A1", "degree": 2}])
    right = pd.DataFrame(
        [{"account_id": "A1", "shortest_path_to_flagged": None, "pagerank_score": 0.25}]
    )
    left_copy = left.copy(deep=True)

    frame = merge_graph_feature_frames([left, right], ["A1", "A2"])

    assert tuple(frame.columns) == GRAPH_ANALYTICS_FEATURE_COLUMNS
    assert frame.set_index("account_id").loc["A1", "degree"] == 2
    assert frame.set_index("account_id").loc["A2", "degree"] == 0
    assert frame.set_index("account_id").loc["A1", "shortest_path_to_flagged"] is None
    pd.testing.assert_frame_equal(left, left_copy)


def test_feature_records_are_json_serialisable_and_round_trip() -> None:
    frame = merge_graph_feature_frames(
        [pd.DataFrame([{"account_id": "A1", "degree": 1, "pagerank_score": 0.5}])],
        ["A1"],
    )

    records = graph_features_to_records(frame)
    round_trip = graph_features_from_records(records)

    json.dumps(records)
    assert list(round_trip.columns) == list(GRAPH_ANALYTICS_FEATURE_COLUMNS)
    assert round_trip.loc[0, "account_id"] == "A1"


def test_invalid_feature_records_raise_graph_analytics_error() -> None:
    with pytest.raises(GraphAnalyticsError):
        graph_features_from_records([{"degree": 1}])

    with pytest.raises(GraphAnalyticsError):
        merge_graph_feature_frames([pd.DataFrame([{"degree": 1}])], ["A1"])
