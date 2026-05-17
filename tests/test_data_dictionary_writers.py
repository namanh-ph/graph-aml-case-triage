"""Tests for data dictionary artefact writers."""

import json
from pathlib import Path

import pandas as pd

from graph_aml.documentation import (
    build_data_dictionary,
    generate_data_dictionary_artefacts,
    write_data_dictionary_csv,
    write_data_dictionary_json,
    write_data_dictionary_markdown,
)


def test_markdown_writer_writes_file(tmp_path: Path) -> None:
    path = write_data_dictionary_markdown(build_data_dictionary(), tmp_path / "nested" / "dd.md")

    assert path.is_file()


def test_json_writer_writes_parseable_json(tmp_path: Path) -> None:
    path = write_data_dictionary_json(build_data_dictionary(), tmp_path / "dd.json")

    assert json.loads(path.read_text(encoding="utf-8"))["tables"]


def test_csv_writer_writes_csv_file(tmp_path: Path) -> None:
    path = write_data_dictionary_csv(build_data_dictionary(), tmp_path / "dd.csv")

    assert path.is_file()


def test_high_level_generator_writes_markdown_json_and_csv(tmp_path: Path) -> None:
    paths = generate_data_dictionary_artefacts(tmp_path)

    assert set(paths) == {"markdown", "json", "csv"}
    assert all(path.is_file() for path in paths.values())


def test_written_markdown_contains_heading(tmp_path: Path) -> None:
    path = write_data_dictionary_markdown(build_data_dictionary(), tmp_path / "dd.md")

    assert "# Data Dictionary" in path.read_text(encoding="utf-8")


def test_written_json_includes_tables(tmp_path: Path) -> None:
    path = write_data_dictionary_json(build_data_dictionary(), tmp_path / "dd.json")

    assert json.loads(path.read_text(encoding="utf-8"))["tables"]


def test_written_csv_has_one_row_per_column(tmp_path: Path) -> None:
    dictionary = build_data_dictionary()
    path = write_data_dictionary_csv(dictionary, tmp_path / "dd.csv")

    assert len(pd.read_csv(path)) == sum(len(table.columns) for table in dictionary.tables)


def test_parent_directories_are_created_automatically(tmp_path: Path) -> None:
    path = write_data_dictionary_json(build_data_dictionary(), tmp_path / "a" / "b" / "dd.json")

    assert path.is_file()
