from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from graph_aml.demo import (
    DemoRunResult,
    build_demo_artefact_index,
    generate_demo_readiness_artefacts,
    write_demo_artefact_index_json,
    write_demo_readiness_report_json,
    write_demo_run_summary_json,
    write_demo_validation_summary_json,
)


def _run_result() -> DemoRunResult:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return DemoRunResult(run_id="DEMO_1", started_at=now, completed_at=now, status="success")


def _assert_parseable_json(path: Path) -> None:
    assert json.loads(path.read_text(encoding="utf-8")) is not None


def test_demo_run_summary_writer_writes_parseable_json(tmp_path) -> None:
    path = write_demo_run_summary_json(_run_result(), tmp_path / "run.json")
    _assert_parseable_json(path)


def test_readiness_report_writer_writes_parseable_json(tmp_path) -> None:
    path = write_demo_readiness_report_json({"status": "ok"}, tmp_path / "ready.json")
    _assert_parseable_json(path)


def test_validation_summary_writer_writes_parseable_json(tmp_path) -> None:
    path = write_demo_validation_summary_json({"status": "ok"}, tmp_path / "validation.json")
    _assert_parseable_json(path)


def test_artefact_index_includes_files_under_report_directory(tmp_path) -> None:
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    index = build_demo_artefact_index(tmp_path)
    assert index["file_count"] == 1


def test_artefact_index_writer_writes_parseable_json(tmp_path) -> None:
    path = write_demo_artefact_index_json({"files": []}, tmp_path / "index.json")
    _assert_parseable_json(path)


def test_high_level_artefact_generator_writes_expected_artefacts(tmp_path) -> None:
    paths = generate_demo_readiness_artefacts(
        run_result=_run_result(),
        readiness={"status": "ok"},
        validation_summary={"status": "ok"},
        output_dir=tmp_path,
    )
    assert {
        "demo_run_summary_json",
        "demo_readiness_report_json",
        "demo_validation_summary_json",
        "demo_artefact_index_json",
    } <= set(paths)


def test_parent_directories_are_created_automatically(tmp_path) -> None:
    path = write_demo_readiness_report_json({"status": "ok"}, tmp_path / "nested" / "ready.json")
    assert path.exists()


def test_artefact_paths_are_returned_as_path_objects(tmp_path) -> None:
    paths = generate_demo_readiness_artefacts(readiness={"status": "ok"}, output_dir=tmp_path)
    assert all(isinstance(path, Path) for path in paths.values())


def test_missing_report_directory_is_handled_gracefully(tmp_path) -> None:
    index = build_demo_artefact_index(tmp_path / "missing")
    assert index["file_count"] == 0
