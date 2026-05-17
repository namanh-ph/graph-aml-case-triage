from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from graph_aml.labels import (
    LabelDatasetBuildResult,
    LabelPersistenceConfig,
    LabelPersistenceError,
    build_account_label_upsert_sql,
    build_account_supervised_dataset_upsert_sql,
    build_case_label_upsert_sql,
    build_case_supervised_dataset_upsert_sql,
    prepare_label_frames_for_persistence,
    validate_label_persistence_config,
)


def _result() -> LabelDatasetBuildResult:
    return LabelDatasetBuildResult(
        case_labels=pd.DataFrame({"case_id": ["C1"], "label_version": ["v1"]}),
        account_labels=pd.DataFrame({"account_id": ["A1"], "label_version": ["v1"]}),
        case_dataset=pd.DataFrame({"case_id": ["C1"], "dataset_version": ["d1"]}),
        account_dataset=pd.DataFrame({"account_id": ["A1"], "dataset_version": ["d1"]}),
    )


def test_default_persistence_config_is_valid() -> None:
    validate_label_persistence_config(LabelPersistenceConfig())


def test_invalid_persistence_config_raises() -> None:
    with pytest.raises(LabelPersistenceError):
        validate_label_persistence_config(replace(LabelPersistenceConfig(), batch_size=0))


def test_prepared_frames_include_all_four_frames() -> None:
    frames = prepare_label_frames_for_persistence(_result())
    assert set(frames) == {"case_labels", "account_labels", "case_dataset", "account_dataset"}


def test_case_label_upsert_sql_inserts_into_table() -> None:
    assert "INSERT INTO aml.case_labels" in build_case_label_upsert_sql()


def test_account_label_upsert_sql_inserts_into_table() -> None:
    assert "INSERT INTO aml.account_labels" in build_account_label_upsert_sql()


def test_case_dataset_upsert_sql_inserts_into_table() -> None:
    assert "INSERT INTO mart.case_supervised_dataset" in build_case_supervised_dataset_upsert_sql()


def test_account_dataset_upsert_sql_inserts_into_table() -> None:
    sql = build_account_supervised_dataset_upsert_sql()
    assert "INSERT INTO mart.account_supervised_dataset" in sql


def test_upsert_sql_uses_named_parameters() -> None:
    assert ":case_id" in build_case_label_upsert_sql()


def test_upsert_sql_includes_on_conflict() -> None:
    assert "ON CONFLICT" in build_account_label_upsert_sql()


def test_persistence_functions_do_not_create_engines(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *args, **kwargs: pytest.fail("no engine"),
    )
    assert prepare_label_frames_for_persistence(_result())
