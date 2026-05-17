"""Tests for graph feature persistence artefact writers."""

import json

from graph_aml.graph import (
    GraphFeaturePersistenceResult,
    generate_graph_feature_persistence_artefacts,
    write_graph_feature_persistence_summary_json,
    write_graph_feature_quality_summary_json,
)


def test_persistence_summary_writer_writes_parseable_json(tmp_path) -> None:
    path = write_graph_feature_persistence_summary_json(
        GraphFeaturePersistenceResult(rows_prepared=1),
        tmp_path / "summary.json",
    )

    assert json.loads(path.read_text(encoding="utf-8"))["rows_prepared"] == 1


def test_quality_summary_writer_writes_parseable_json(tmp_path) -> None:
    path = write_graph_feature_quality_summary_json(
        {"status": "ok"},
        tmp_path / "quality.json",
    )

    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "ok"}


def test_high_level_persistence_artefact_generator_writes_expected_files(tmp_path) -> None:
    paths = generate_graph_feature_persistence_artefacts(
        GraphFeaturePersistenceResult(rows_prepared=1),
        {"status": "ok"},
        output_dir=tmp_path / "nested",
    )

    assert set(paths) == {"persistence_summary_json", "quality_summary_json"}
    assert all(path.exists() for path in paths.values())
    assert all(path.parent == tmp_path / "nested" for path in paths.values())


def test_empty_persistence_result_still_writes_valid_artefact(tmp_path) -> None:
    paths = generate_graph_feature_persistence_artefacts(
        GraphFeaturePersistenceResult(),
        output_dir=tmp_path,
    )

    assert set(paths) == {"persistence_summary_json"}
    assert (
        json.loads(paths["persistence_summary_json"].read_text(encoding="utf-8"))["rows_prepared"]
        == 0
    )
