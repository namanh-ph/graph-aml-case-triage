from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from graph_aml.labels import (
    LabelDatasetBuildResult,
    generate_label_artefacts,
    write_account_labels_csv,
    write_account_supervised_dataset_csv,
    write_case_labels_csv,
    write_case_supervised_dataset_csv,
    write_label_quality_summary_json,
)


def _result() -> LabelDatasetBuildResult:
    frame = pd.DataFrame({"id": [1]})
    return LabelDatasetBuildResult(frame, frame, frame, frame)


def test_case_labels_csv_writer_writes_file(tmp_path) -> None:
    assert write_case_labels_csv(pd.DataFrame(), tmp_path / "case.csv").exists()


def test_account_labels_csv_writer_writes_file(tmp_path) -> None:
    assert write_account_labels_csv(pd.DataFrame(), tmp_path / "account.csv").exists()


def test_case_dataset_csv_writer_writes_file(tmp_path) -> None:
    assert write_case_supervised_dataset_csv(pd.DataFrame(), tmp_path / "case_ds.csv").exists()


def test_account_dataset_csv_writer_writes_file(tmp_path) -> None:
    path = write_account_supervised_dataset_csv(pd.DataFrame(), tmp_path / "account_ds.csv")
    assert path.exists()


def test_label_quality_summary_writer_writes_parseable_json(tmp_path) -> None:
    path = write_label_quality_summary_json({"status": "ok"}, tmp_path / "summary.json")
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "ok"


def test_high_level_artefact_generator_writes_expected_artefacts(tmp_path) -> None:
    paths = generate_label_artefacts(_result(), tmp_path)
    assert {
        "case_labels_csv",
        "account_labels_csv",
        "case_supervised_dataset_csv",
        "account_supervised_dataset_csv",
        "label_quality_summary_json",
    } <= set(paths)


def test_parent_directories_are_created_automatically(tmp_path) -> None:
    assert write_case_labels_csv(pd.DataFrame(), tmp_path / "nested" / "case.csv").exists()


def test_artefact_paths_are_returned_as_path_objects(tmp_path) -> None:
    paths = generate_label_artefacts(_result(), tmp_path).values()
    assert all(isinstance(path, Path) for path in paths)


def test_empty_label_frames_still_write_valid_artefacts(tmp_path) -> None:
    paths = generate_label_artefacts(
        LabelDatasetBuildResult(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()),
        tmp_path,
    )
    assert all(path.exists() for path in paths.values())
