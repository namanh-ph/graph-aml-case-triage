"""Tests for graph analytics artefact writers."""

import json

import pandas as pd

from graph_aml.graph import (
    GRAPH_ANALYTICS_FEATURE_COLUMNS,
    GraphAnalyticsResult,
    generate_graph_analytics_artefacts,
    write_graph_analytics_summary_json,
    write_graph_features_csv,
    write_graph_features_json,
)


def _features() -> pd.DataFrame:
    row = {column: 0 for column in GRAPH_ANALYTICS_FEATURE_COLUMNS}
    row["account_id"] = "A1"
    row["shortest_path_to_flagged"] = None
    return pd.DataFrame([row], columns=GRAPH_ANALYTICS_FEATURE_COLUMNS)


def test_graph_features_csv_writer_writes_file(tmp_path) -> None:
    path = write_graph_features_csv(_features(), tmp_path / "features.csv")

    assert path.exists()
    assert "account_id" in path.read_text(encoding="utf-8")


def test_graph_features_json_writer_writes_parseable_json(tmp_path) -> None:
    path = write_graph_features_json(_features(), tmp_path / "features.json")

    assert json.loads(path.read_text(encoding="utf-8"))[0]["account_id"] == "A1"


def test_graph_analytics_summary_writer_writes_parseable_json(tmp_path) -> None:
    path = write_graph_analytics_summary_json({"account_count": 1}, tmp_path / "summary.json")

    assert json.loads(path.read_text(encoding="utf-8")) == {"account_count": 1}


def test_high_level_artefact_generator_writes_expected_files(tmp_path) -> None:
    paths = generate_graph_analytics_artefacts(
        GraphAnalyticsResult(features=_features(), summary={"account_count": 1}),
        output_dir=tmp_path / "nested",
    )

    assert set(paths) == {"features_csv", "features_json", "summary_json"}
    assert all(path.exists() for path in paths.values())
    assert all(path.parent == tmp_path / "nested" for path in paths.values())


def test_empty_feature_frames_still_write_valid_artefacts(tmp_path) -> None:
    paths = generate_graph_analytics_artefacts(
        GraphAnalyticsResult(features=pd.DataFrame(columns=GRAPH_ANALYTICS_FEATURE_COLUMNS)),
        output_dir=tmp_path,
    )

    assert json.loads(paths["features_json"].read_text(encoding="utf-8")) == []
