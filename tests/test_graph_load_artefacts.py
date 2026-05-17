"""Tests for graph load artefact writers."""

import json

from graph_aml.graph import (
    GraphLoadResult,
    generate_graph_load_artefacts,
    graph_load_result_to_dict,
    write_graph_load_summary_json,
    write_graph_reconciliation_json,
)


def test_graph_load_result_to_dict_is_json_serialisable() -> None:
    payload = graph_load_result_to_dict(GraphLoadResult(nodes_loaded={"Account": 1}))

    json.dumps(payload)
    assert payload["nodes_loaded"] == {"Account": 1}


def test_load_summary_writer_writes_parseable_json(tmp_path) -> None:
    path = write_graph_load_summary_json(
        GraphLoadResult(nodes_loaded={"Account": 1}),
        tmp_path / "summary.json",
    )

    assert json.loads(path.read_text(encoding="utf-8"))["nodes_loaded"] == {"Account": 1}


def test_reconciliation_writer_writes_parseable_json(tmp_path) -> None:
    path = write_graph_reconciliation_json({"status": "ok"}, tmp_path / "recon.json")

    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "ok"}


def test_high_level_artefact_generator_writes_expected_files(tmp_path) -> None:
    paths = generate_graph_load_artefacts(
        GraphLoadResult(nodes_loaded={"Account": 1}),
        {"status": "ok"},
        output_dir=tmp_path / "nested",
    )

    assert set(paths) == {"graph_load_summary", "graph_reconciliation"}
    assert all(path.exists() for path in paths.values())
    assert all(path.parent == tmp_path / "nested" for path in paths.values())


def test_high_level_artefact_generator_can_skip_reconciliation(tmp_path) -> None:
    paths = generate_graph_load_artefacts(GraphLoadResult(), output_dir=tmp_path)

    assert set(paths) == {"graph_load_summary"}
