"""Tests for raw loader file handling and table mapping."""

from pathlib import Path

import pandas as pd
import pytest

from graph_aml.ingestion import IngestionSourceError
from graph_aml.ingestion.raw_loader import RAW_TABLE_MAPPING, read_table_file


def test_raw_table_mapping_includes_expected_tables() -> None:
    assert RAW_TABLE_MAPPING == {
        "countries": "raw.countries_raw",
        "customers": "raw.customers_raw",
        "accounts": "raw.accounts_raw",
        "counterparties": "raw.counterparties_raw",
        "devices": "raw.devices_raw",
        "transactions": "raw.transactions_raw",
    }


def test_read_table_file_reads_csv(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    pd.DataFrame({"value": [1, 2]}).to_csv(path, index=False)

    frame = read_table_file(path)

    assert list(frame["value"]) == [1, 2]


def test_read_table_file_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_table_file(tmp_path / "missing.csv")


def test_read_table_file_raises_for_unsupported_suffix(tmp_path: Path) -> None:
    path = tmp_path / "sample.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(IngestionSourceError):
        read_table_file(path)


def test_scenario_manifest_is_not_mapped_to_raw_tables() -> None:
    assert "scenario_manifest" not in RAW_TABLE_MAPPING
