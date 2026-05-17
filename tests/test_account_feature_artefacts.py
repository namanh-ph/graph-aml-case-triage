"""Tests for account feature artefact writers."""

import json
from pathlib import Path

import pandas as pd
import pytest

from graph_aml.features import (
    ACCOUNT_FEATURE_COLUMNS,
    FeatureArtefactError,
    calculate_account_features,
    generate_account_feature_artefacts,
    write_account_feature_summary_json,
    write_account_features_csv,
)
from graph_aml.features.summary import summarise_account_features


def _accounts() -> pd.DataFrame:
    return pd.DataFrame([{"account_id": "ACC_A"}, {"account_id": "ACC_B"}])


def _transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "transaction_id": "TXN_001",
                "sender_account_id": "ACC_A",
                "receiver_account_id": "ACC_B",
                "counterparty_id": None,
                "transaction_timestamp": "2025-01-01T10:00:00Z",
                "amount": 10.0,
            }
        ]
    )


def _features() -> pd.DataFrame:
    return calculate_account_features(_accounts(), _transactions())


def test_write_account_features_csv_writes_csv_file(tmp_path: Path) -> None:
    path = write_account_features_csv(_features(), tmp_path / "features.csv")

    assert path.is_file()


def test_written_feature_csv_has_expected_columns(tmp_path: Path) -> None:
    path = write_account_features_csv(_features(), tmp_path / "features.csv")

    assert tuple(pd.read_csv(path).columns) == ACCOUNT_FEATURE_COLUMNS


def test_write_account_feature_summary_json_writes_parseable_json(tmp_path: Path) -> None:
    path = write_account_feature_summary_json(
        summarise_account_features(_features()),
        tmp_path / "summary.json",
    )

    assert json.loads(path.read_text(encoding="utf-8"))["feature_row_count"] == 2


def test_generate_account_feature_artefacts_writes_feature_csv_and_summary_json(
    tmp_path: Path,
) -> None:
    paths = generate_account_feature_artefacts(
        _accounts(),
        _transactions(),
        output_dir=tmp_path,
    )

    assert set(paths) == {"features_csv", "summary_json"}
    assert all(path.is_file() for path in paths.values())


def test_artefact_writer_validates_features_before_writing(tmp_path: Path) -> None:
    invalid = _features().drop(columns=["account_id"])

    with pytest.raises(FeatureArtefactError):
        write_account_features_csv(invalid, tmp_path / "features.csv")


def test_parent_directories_are_created_automatically(tmp_path: Path) -> None:
    path = write_account_features_csv(_features(), tmp_path / "a" / "b" / "features.csv")

    assert path.is_file()


def test_write_failures_raise_feature_artefact_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_to_csv(self, path, index=False):
        raise OSError("cannot write")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_to_csv)

    with pytest.raises(FeatureArtefactError):
        write_account_features_csv(_features(), tmp_path / "features.csv")
